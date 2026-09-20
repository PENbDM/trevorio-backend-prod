
from datetime import timedelta

import requests

from cryptography.fernet import Fernet, InvalidToken

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from integrations.models import GithubConnection


GITHUB_TOKEN_URL = (
    "https://github.com/login/oauth/access_token"
)


# ==========================================
# EXCEPTIONS
# ==========================================

class GithubReconnectRequired(Exception):
    """
    The user must reconnect their GitHub account.
    """
    pass


# ==========================================
# ENCRYPTION
# ==========================================

def get_cipher() -> Fernet:
    return Fernet(
        settings.GITHUB_TOKEN_ENCRYPTION_KEY.encode(
            "utf-8"
        )
    )


def encrypt_token(token: str) -> str:
    """
    Encrypt a GitHub token before storing it.
    """

    return get_cipher().encrypt(
        token.encode("utf-8")
    ).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a saved GitHub token.
    """

    try:
        return get_cipher().decrypt(
            encrypted_token.encode("utf-8")
        ).decode("utf-8")

    except InvalidToken as exc:
        raise GithubReconnectRequired(
            "Unable to decrypt GitHub credentials."
        ) from exc


# ==========================================
# GET VALID ACCESS TOKEN
# ==========================================

def get_valid_github_token(
    connection: GithubConnection,
) -> str:
    """
    Return a valid GitHub access token.

    If it is about to expire:
      1. Refresh it using GitHub.
      2. Encrypt the new access token.
      3. Encrypt the new refresh token.
      4. Replace the old values in PostgreSQL.
      5. Return the new access token.
    """

    with transaction.atomic():

        # Lock this connection so multiple Django
        # workers cannot refresh it simultaneously.
        connection = (
            GithubConnection.objects
            .select_for_update()
            .get(pk=connection.pk)
        )

        now = timezone.now()

        expires_at = connection.access_token_expires_at

        # ==================================
        # 1. CHECK EXISTING TOKEN
        # ==================================

        # None means the token has no configured
        # expiration (GitHub App setting).
        if expires_at is None:
            return decrypt_token(
                connection.access_token_encrypted
            )

        # Token still has more than 60 seconds.
        if expires_at > now + timedelta(seconds=60):
            return decrypt_token(
                connection.access_token_encrypted
            )

        # ==================================
        # 2. CHECK REFRESH TOKEN
        # ==================================

        if not connection.refresh_token_encrypted:
            raise GithubReconnectRequired(
                "GitHub refresh token is missing."
            )

        if (
            connection.refresh_token_expires_at
            and connection.refresh_token_expires_at <= now
        ):
            raise GithubReconnectRequired(
                "GitHub refresh token has expired."
            )

        refresh_token = decrypt_token(
            connection.refresh_token_encrypted
        )

        # ==================================
        # 3. REQUEST NEW TOKEN PAIR
        # ==================================

        response = requests.post(
            GITHUB_TOKEN_URL,
            headers={
                "Accept": "application/json",
            },
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )

        # Temporary GitHub errors should remain
        # HTTP errors, not force a reconnect.
        if response.status_code >= 500:
            response.raise_for_status()

        if response.status_code in (400, 401, 403):
            raise GithubReconnectRequired(
                "GitHub rejected the refresh token."
            )

        response.raise_for_status()

        data = response.json()

        new_access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token")

        if not new_access_token or not new_refresh_token:
            raise GithubReconnectRequired(
                "GitHub did not return new credentials."
            )

        # ==================================
        # 4. REPLACE ENCRYPTED TOKENS
        # ==================================

        connection.access_token_encrypted = (
            encrypt_token(new_access_token)
        )

        connection.refresh_token_encrypted = (
            encrypt_token(new_refresh_token)
        )

        # ==================================
        # 5. UPDATE EXPIRATION TIMES
        # ==================================

        connection.access_token_expires_at = (
            timezone.now()
            + timedelta(seconds=int(data["expires_in"]))
        )

        connection.refresh_token_expires_at = (
            timezone.now()
            + timedelta(
                seconds=int(
                    data["refresh_token_expires_in"]
                )
            )
        )

        # ==================================
        # 6. SAVE NEW TOKEN PAIR
        # ==================================

        connection.save(
            update_fields=[
                "access_token_encrypted",
                "refresh_token_encrypted",
                "access_token_expires_at",
                "refresh_token_expires_at",
                "updated_at",
            ]
        )

        # ==================================
        # 7. RETURN NEW ACCESS TOKEN
        # ==================================

        return new_access_token