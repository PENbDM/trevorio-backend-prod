
import base64
import hashlib
import secrets

from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

from integrations.models import GithubOAuthState


GITHUB_AUTHORIZE_URL = (
    "https://github.com/login/oauth/authorize"
)


def create_github_authorization_url(
    user,
    datasource_id,
):
    # Generate unpredictable random values.
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    # Store only a hash of the OAuth state.
    state_hash = hashlib.sha256(
        state.encode("utf-8")
    ).hexdigest()

    # Generate the PKCE code challenge.
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode("ascii")
        ).digest()
    ).decode("ascii").rstrip("=")

    # Store the authorisation attempt in PostgreSQL.
    GithubOAuthState.objects.create(
        user=user,
        state_hash=state_hash,
        code_verifier=code_verifier,
        datasource_id=datasource_id,
        expires_at=(
            timezone.now() + timedelta(minutes=10)
        ),
    )

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_CALLBACK_URL,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return (
        f"{GITHUB_AUTHORIZE_URL}?"
        f"{urlencode(params)}"
    )



GITHUB_TOKEN_URL = (
    "https://github.com/login/oauth/access_token"
)

GITHUB_USER_URL = (
    "https://api.github.com/user"
)



def exchange_code_for_token(
    code: str,
    code_verifier: str,
) -> dict:

    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={
            "Accept": "application/json",
        },
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_CALLBACK_URL,
            "code_verifier": code_verifier,
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    # GitHub can return HTTP 200
    # even when token exchange fails.
    if "access_token" not in data:

        logger.error(
            "GitHub token exchange rejected: error=%s",
            data.get("error", "unknown_error"),
        )

        raise ValueError(
            "GitHub did not return an access token."
        )

    return data


def get_github_user(access_token: str) -> dict:
    """
    Fetch the authenticated user's
    GitHub account information.
    """

    response = requests.get(
        GITHUB_USER_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("id") or not data.get("login"):
        raise ValueError(
            "GitHub returned invalid user information."
        )

    return data