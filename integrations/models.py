
from django.conf import settings
from django.db import models


class GithubConnection(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="github_connection",
    )

    github_user_id = models.BigIntegerField(
        db_index=True
    )

    github_username = models.CharField(
        max_length=255
    )

    # These fields will contain encrypted values,
    # never plaintext GitHub tokens.
    access_token_encrypted = models.TextField()

    refresh_token_encrypted = models.TextField(
        blank=True
    )

    access_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    refresh_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.user_id} - "
            f"{self.github_username}"
        )


class GithubOAuthState(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    state_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    code_verifier = models.CharField(
        max_length=128,
    )

    datasource_id = models.UUIDField()

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )