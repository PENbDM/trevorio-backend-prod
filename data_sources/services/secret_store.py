import base64
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class SecretStoreError(Exception):
    pass


class LocalSecretStore:
    """Small local encrypted secret store using the existing secret_ref DB column.

    New values are self-contained: `local:<fernet-token>`.
    The reader also accepts legacy unprefixed Fernet tokens and a few common
    file-reference forms to make recovery less fragile.
    """

    def __init__(self, secret_key=None):
        raw = secret_key if secret_key is not None else settings.LOCAL_SECRET_KEY
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        raw = str(raw)
        if not raw:
            raise SecretStoreError("LOCAL_SECRET_KEY is empty.")
        key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
        self.fernet = Fernet(key)

    def put(self, payload: dict) -> str:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        token = self.fernet.encrypt(encoded).decode("utf-8")
        ref = f"local:{token}"
        if len(ref) > 500:
            raise SecretStoreError("Encrypted datasource secret is too large for secret_ref.")
        return ref

    def get(self, secret_ref: str) -> dict:
        if not secret_ref:
            raise SecretStoreError("Datasource has no secret_ref.")

        ref = str(secret_ref).strip()

        # Development/legacy plain JSON support.
        if ref.startswith("{"):
            try:
                value = json.loads(ref)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass

        # Current direct encrypted reference.
        token = ref
        for prefix in ("local:", "fernet:", "encrypted:"):
            if token.startswith(prefix):
                token = token[len(prefix):]
                break

        # Legacy file references: file:C:/..., local-file:path, or a direct path.
        possible_path = None
        for prefix in ("file:", "local-file:"):
            if ref.startswith(prefix):
                possible_path = ref[len(prefix):]
                break
        if possible_path is None and not ref.startswith("gAAAA"):
            candidate = Path(ref)
            if candidate.is_absolute() or "/" in ref or "\\" in ref:
                possible_path = ref

        if possible_path:
            path = Path(possible_path)
            if not path.is_absolute():
                path = settings.BASE_DIR / path
            if path.exists() and path.is_file():
                return self.get(path.read_text(encoding="utf-8").strip())

        # A few conventional legacy local-secret locations keyed by ref.
        if not ref.startswith("gAAAA") and all(ch not in ref for ch in "/\\:"):
            for path in (
                settings.BASE_DIR / ".secrets" / ref,
                settings.BASE_DIR / ".secrets" / f"{ref}.json",
                settings.BASE_DIR / "secrets" / ref,
                settings.BASE_DIR / "secrets" / f"{ref}.json",
            ):
                if path.exists() and path.is_file():
                    return self.get(path.read_text(encoding="utf-8").strip())

        try:
            decoded = self.fernet.decrypt(token.encode("utf-8"))
            value = json.loads(decoded.decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise SecretStoreError(
                "Unable to decrypt datasource credentials. Re-enter the connection credentials."
            ) from exc

        if not isinstance(value, dict):
            raise SecretStoreError("Datasource secret payload is invalid.")
        return value

    def delete(self, secret_ref: str) -> None:
        # New refs are self-contained in the DB, so deletion of the DataSource row
        # removes the reference. We deliberately do not delete arbitrary legacy paths.
        return None


def get_secret_store() -> LocalSecretStore:
    return LocalSecretStore()
