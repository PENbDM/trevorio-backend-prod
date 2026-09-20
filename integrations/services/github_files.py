
import base64
import binascii
from urllib.parse import quote

import requests

from .github_tokens import get_valid_github_token


GITHUB_API_URL = "https://api.github.com"

# Maximum SQL file size for our initial import feature.
MAX_SQL_FILE_SIZE = 512 * 1024


class GithubFileError(Exception):
    pass


def get_repository_content(
    connection,
    repository,
    path="",
):
    """
    Retrieve a file or directory from GitHub.
    """

    access_token = get_valid_github_token(connection)

    owner = repository["owner"]
    repo_name = repository["name"]
    branch = repository["default_branch"]

    # Encode path segments safely.
    encoded_path = quote(path, safe="/")

    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{quote(owner, safe='')}/"
        f"{quote(repo_name, safe='')}/contents"
    )

    if encoded_path:
        url = f"{url}/{encoded_path}"

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        params={
            "ref": branch,
        },
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def list_repository_files(
    connection,
    repository,
    path="",
):
    """
    Return directories and SQL files.
    """

    data = get_repository_content(
        connection,
        repository,
        path,
    )

    if not isinstance(data, list):
        raise GithubFileError(
            "The requested path is not a directory."
        )

    items = []

    for item in data:
        item_type = item["type"]
        name = item["name"]

        # Only include directories and .sql files.
        if item_type == "dir":
            items.append({
                "name": name,
                "path": item["path"],
                "type": "dir",
            })

        elif (
            item_type == "file"
            and name.lower().endswith(".sql")
        ):
            items.append({
                "name": name,
                "path": item["path"],
                "type": "file",
                "size": item.get("size", 0),
            })

    # Folders first, then files.
    items.sort(
        key=lambda item: (
            item["type"] != "dir",
            item["name"].lower(),
        )
    )

    return items


def get_sql_file_content(
    connection,
    repository,
    path,
):
    """
    Retrieve and decode a selected SQL file.
    """

    if not path.lower().endswith(".sql"):
        raise GithubFileError(
            "Only .sql files are supported."
        )

    data = get_repository_content(
        connection,
        repository,
        path,
    )

    if not isinstance(data, dict):
        raise GithubFileError(
            "Expected a SQL file."
        )

    if data.get("type") != "file":
        raise GithubFileError(
            "The selected item is not a file."
        )

    file_size = data.get("size", 0)

    if file_size > MAX_SQL_FILE_SIZE:
        raise GithubFileError(
            "SQL file is too large. Maximum size is 512 KB."
        )

    if data.get("encoding") != "base64":
        raise GithubFileError(
            "Unsupported GitHub file encoding."
        )

    encoded_content = data.get("content")

    if not encoded_content:
        raise GithubFileError(
            "GitHub did not return the file content."
        )

    try:
        decoded_content = base64.b64decode(
            "".join(encoded_content.split()),
            validate=True,
        )

        if len(decoded_content) > MAX_SQL_FILE_SIZE:
            raise GithubFileError(
                "SQL file exceeds the maximum size."
            )

        sql = decoded_content.decode("utf-8-sig")

    except (
        binascii.Error,
        UnicodeDecodeError,
    ) as exc:
        raise GithubFileError(
            "Unable to decode SQL file."
        ) from exc

    return {
        "name": data["name"],
        "path": data["path"],
        "sha": data["sha"],
        "content": sql,
        "size": file_size,
    }