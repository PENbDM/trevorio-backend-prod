import hashlib
import logging

from datetime import timedelta

import requests

from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import (
    Serializer,
    UUIDField,
    IntegerField,
    CharField,
    ValidationError,
)

from data_sources.models import DataSource

from .models import (
    GithubConnection,
    GithubOAuthState,
)

from .services.github_auth import (
    create_github_authorization_url,
    exchange_code_for_token,
    get_github_user,
)

from .services.github_tokens import (
    encrypt_token,
    GithubReconnectRequired,
)

from .services.github_repositories import (
    get_github_repositories,
)

from .services.github_files import (
    list_repository_files,
    get_sql_file_content,
    GithubFileError,
)


logger = logging.getLogger(__name__)

# ==========================================
# 1. GITHUB CONNECTION STATUS
# ==========================================

class GithubConnectionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        connection = GithubConnection.objects.filter(
            user=request.user
        ).first()

        if connection is None:
            return Response({
                "connected": False,
                "github_username": None,
            })

        return Response({
            "connected": True,
            "github_username": connection.github_username,
        })


# ==========================================
# 2. CONNECT GITHUB
# ==========================================

class GithubConnectSerializer(Serializer):
    datasource_id = UUIDField()


class GithubConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GithubConnectSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        datasource_id = serializer.validated_data[
            "datasource_id"
        ]

        # Verify that the Trevor user has
        # access to this datasource.
        has_access = DataSource.objects.filter(
            id=datasource_id,
            memberships__user=request.user,
        ).exists()

        if not has_access:
            return Response(
                {
                    "detail": "Datasource not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        authorization_url = (
            create_github_authorization_url(
                user=request.user,
                datasource_id=datasource_id,
            )
        )

        return Response({
            "authorization_url": authorization_url,
        })


# ==========================================
# 3. GITHUB OAUTH CALLBACK
# ==========================================

class GithubCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        raw_state = request.query_params.get("state")
        code = request.query_params.get("code")

        # ----------------------------------
        # Validate state parameter
        # ----------------------------------

        if not raw_state:
            logger.warning(
                "GitHub callback failed: missing state"
            )

            return self._error_redirect()

        state_hash = hashlib.sha256(
            raw_state.encode("utf-8")
        ).hexdigest()

        # ----------------------------------
        # Retrieve and consume OAuth state
        # ----------------------------------

        with transaction.atomic():
            oauth_state = (
                GithubOAuthState.objects
                .select_for_update()
                .filter(state_hash=state_hash)
                .first()
            )

            if oauth_state is None:
                logger.warning(
                    "GitHub callback failed: "
                    "state not found or already consumed"
                )

                return self._error_redirect()

            if oauth_state.expires_at <= timezone.now():
                oauth_state.delete()

                logger.warning(
                    "GitHub callback failed: state expired"
                )

                return self._error_redirect()

            # Save values before deleting the state.
            user_id = oauth_state.user_id
            datasource_id = oauth_state.datasource_id
            code_verifier = oauth_state.code_verifier

            # The same OAuth state cannot be reused.
            oauth_state.delete()

        # ----------------------------------
        # Check GitHub authorization result
        # ----------------------------------

        github_error = request.query_params.get("error")

        if github_error or not code:
            logger.warning(
                "GitHub authorization failed: error=%s",
                github_error or "missing_code",
            )

            return self._error_redirect(datasource_id)

        # ----------------------------------
        # Exchange code and save connection
        # ----------------------------------

        stage = "token_exchange"

        try:
            # STEP 1:
            # Exchange the temporary authorization
            # code for a GitHub user access token.

            logger.info(
                "GitHub OAuth: starting token exchange"
            )

            token_data = exchange_code_for_token(
                code=code,
                code_verifier=code_verifier,
            )

            access_token = token_data["access_token"]

            logger.info(
                "GitHub OAuth: token exchange successful"
            )

            # STEP 2:
            # Retrieve GitHub user information.

            stage = "github_user"

            github_user = get_github_user(
                access_token
            )

            logger.info(
                "GitHub OAuth: user retrieved successfully"
            )

            # STEP 3:
            # Calculate token expiration times.

            stage = "token_expiration"

            now = timezone.now()

            access_expires_in = token_data.get(
                "expires_in"
            )

            refresh_expires_in = token_data.get(
                "refresh_token_expires_in"
            )

            access_expires_at = (
                now + timedelta(
                    seconds=int(access_expires_in)
                )
                if access_expires_in is not None
                else None
            )

            refresh_expires_at = (
                now + timedelta(
                    seconds=int(refresh_expires_in)
                )
                if refresh_expires_in is not None
                else None
            )

            refresh_token = token_data.get(
                "refresh_token",
                "",
            )

            # STEP 4:
            # Encrypt tokens before saving.

            stage = "encrypt_tokens"

            encrypted_access_token = encrypt_token(
                access_token
            )

            encrypted_refresh_token = (
                encrypt_token(refresh_token)
                if refresh_token
                else ""
            )

            logger.info(
                "GitHub OAuth: token encryption successful"
            )

            # STEP 5:
            # Save the GitHub connection in PostgreSQL.

            stage = "save_connection"

            GithubConnection.objects.update_or_create(
                user_id=user_id,
                defaults={
                    "github_user_id": github_user["id"],

                    "github_username": github_user["login"],

                    "access_token_encrypted": (
                        encrypted_access_token
                    ),

                    "refresh_token_encrypted": (
                        encrypted_refresh_token
                    ),

                    "access_token_expires_at": (
                        access_expires_at
                    ),

                    "refresh_token_expires_at": (
                        refresh_expires_at
                    ),
                },
            )

            logger.info(
                "GitHub OAuth: connection saved successfully"
            )

        except (
            requests.RequestException,
            ValueError,
            KeyError,
        ) as exc:

            logger.error(
                "GitHub OAuth failed: stage=%s, exception=%s",
                stage,
                type(exc).__name__,
            )

            return self._error_redirect(datasource_id)

        # ----------------------------------
        # Success: redirect back to Trevor
        # ----------------------------------

        logger.info(
            "GitHub OAuth: authorization completed"
        )

        return redirect(
            f"{settings.FRONTEND_URL.rstrip('/')}"
            f"/datasources/{datasource_id}/import-github"
            f"?github=connected"
        )

    # ======================================
    # ERROR REDIRECT
    # ======================================

    @staticmethod
    def _error_redirect(datasource_id=None):
        base_url = settings.FRONTEND_URL.rstrip("/")

        if datasource_id:
            return redirect(
                f"{base_url}/datasources/{datasource_id}"
                f"/import-github?github=error"
            )

        return redirect(
            f"{base_url}/datasources?github=error"
        )



# ==========================================
# 4. GITHUB REPOSITORIES
# ==========================================


# ==========================================
# 4. GITHUB REPOSITORIES
# ==========================================

class GithubRepositoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        connection = GithubConnection.objects.filter(
            user=request.user
        ).first()

        if connection is None:
            return Response(
                {
                    "detail": "GitHub is not connected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            repositories = get_github_repositories(
                connection
            )

        # ==================================
        # TOKEN EXPIRED / REVOKED
        # ==================================

        except GithubReconnectRequired:

            return Response(
                {
                    "detail": "Reconnect your GitHub account.",
                    "code": "github_reconnect_required",
                },
                status=status.HTTP_409_CONFLICT,
            )

        # ==================================
        # GITHUB HTTP ERROR
        # ==================================

        except requests.HTTPError as exc:

            github_status = (
                exc.response.status_code
                if exc.response is not None
                else None
            )

            if github_status == 401:
                return Response(
                    {
                        "detail": "Reconnect your GitHub account.",
                        "code": "github_reconnect_required",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            logger.warning(
                "GitHub repositories request failed: status=%s",
                github_status,
            )

            return Response(
                {
                    "detail": "Unable to fetch repositories."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ==================================
        # NETWORK ERROR
        # ==================================

        except requests.RequestException:

            logger.warning(
                "GitHub repositories request failed: "
                "network error"
            )

            return Response(
                {
                    "detail": "GitHub is temporarily unavailable."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "repositories": repositories,
            "count": len(repositories),
        })



# ==========================================
# 5. VALIDATE GITHUB FILE REQUESTS
# ==========================================

class GithubFilesSerializer(Serializer):
    repo_id = IntegerField(min_value=1)

    path = CharField(
        required=False,
        allow_blank=True,
        max_length=1024,
        default="",
    )

    def validate_path(self, value):
        if (
            value.startswith("/")
            or "\\" in value
            or any(
                part in (".", "..")
                for part in value.split("/")
            )
            or any(ord(char) < 32 for char in value)
        ):
            raise ValidationError(
                "Invalid repository path."
            )

        return value


class GithubContentSerializer(GithubFilesSerializer):
    path = CharField(
        required=True,
        allow_blank=False,
        max_length=1024,
    )


# ==========================================
# 6. VERIFY REPOSITORY ACCESS
# ==========================================

def get_user_repository(connection, repo_id):
    """
    Find a repository that the connected
    GitHub user can access through our App.
    """

    repositories = get_github_repositories(
        connection
    )

    for repository in repositories:
        if repository["id"] == repo_id:
            return repository

    return None


# ==========================================
# 7. GITHUB FILES VIEW
# ==========================================

class GithubFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # 1. Validate query parameters.
        serializer = GithubFilesSerializer(
            data=request.query_params
        )

        serializer.is_valid(
            raise_exception=True
        )

        repo_id = serializer.validated_data[
            "repo_id"
        ]

        path = serializer.validated_data[
            "path"
        ]

        # 2. Find the current user's GitHub connection.
        connection = GithubConnection.objects.filter(
            user=request.user
        ).first()

        if connection is None:
            return Response(
                {
                    "detail": "GitHub is not connected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 3. Check repository permissions.
            repository = get_user_repository(
                connection,
                repo_id,
            )

            if repository is None:
                return Response(
                    {
                        "detail": "Repository not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 4. Fetch directory contents from GitHub.
            files = list_repository_files(
                connection,
                repository,
                path,
            )

        except GithubReconnectRequired:
            return Response(
                {
                    "detail": "Reconnect your GitHub account."
                },
                status=status.HTTP_409_CONFLICT,
            )

        except GithubFileError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except requests.HTTPError as exc:
            github_status = (
                exc.response.status_code
                if exc.response is not None
                else None
            )

            if github_status == 401:
                return Response(
                    {
                        "detail": "Reconnect your GitHub account."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if github_status == 404:
                return Response(
                    {
                        "detail": "Repository path not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            logger.warning(
                "GitHub files request failed: status=%s",
                github_status,
            )

            return Response(
                {
                    "detail": "Unable to fetch GitHub files."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except requests.RequestException:
            return Response(
                {
                    "detail": "GitHub is temporarily unavailable."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 5. Return the files to Next.js.
        return Response({
            "repository": repository["full_name"],
            "path": path,
            "files": files,
        })


# ==========================================
# 8. GITHUB CONTENT VIEW
# ==========================================

class GithubContentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # 1. Validate query parameters.
        serializer = GithubContentSerializer(
            data=request.query_params
        )

        serializer.is_valid(
            raise_exception=True
        )

        repo_id = serializer.validated_data[
            "repo_id"
        ]

        path = serializer.validated_data[
            "path"
        ]

        # 2. Find the user's GitHub connection.
        connection = GithubConnection.objects.filter(
            user=request.user
        ).first()

        if connection is None:
            return Response(
                {
                    "detail": "GitHub is not connected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 3. Verify access to the repository.
            repository = get_user_repository(
                connection,
                repo_id,
            )

            if repository is None:
                return Response(
                    {
                        "detail": "Repository not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 4. Fetch the selected SQL file.
            file_data = get_sql_file_content(
                connection,
                repository,
                path,
            )

        except GithubReconnectRequired:
            return Response(
                {
                    "detail": "Reconnect your GitHub account."
                },
                status=status.HTTP_409_CONFLICT,
            )

        except GithubFileError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except requests.HTTPError as exc:
            github_status = (
                exc.response.status_code
                if exc.response is not None
                else None
            )

            if github_status == 401:
                return Response(
                    {
                        "detail": "Reconnect your GitHub account."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if github_status == 404:
                return Response(
                    {
                        "detail": "SQL file not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            logger.warning(
                "GitHub content request failed: status=%s",
                github_status,
            )

            return Response(
                {
                    "detail": "Unable to fetch SQL file."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except requests.RequestException:
            return Response(
                {
                    "detail": "GitHub is temporarily unavailable."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 5. Return the SQL file contents to Next.js.
        return Response(file_data)