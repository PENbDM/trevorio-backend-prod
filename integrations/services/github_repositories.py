
import requests

from .github_tokens import get_valid_github_token


GITHUB_API_URL = "https://api.github.com"


def get_github_repositories(connection):
    """
    Fetch repositories accessible to the
    connected GitHub user through our App.
    """

    # ==================================
    # GET VALID ACCESS TOKEN
    # ==================================

    access_token = get_valid_github_token(
        connection
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    # ==================================
    # GET USER INSTALLATIONS
    # ==================================

    response = requests.get(
        f"{GITHUB_API_URL}/user/installations",
        headers=headers,
        params={
            "per_page": 100,
        },
        timeout=10,
    )

    response.raise_for_status()

    installations = response.json().get(
        "installations",
        []
    )

    repositories = []

    # ==================================
    # GET INSTALLATION REPOSITORIES
    # ==================================

    for installation in installations:

        installation_id = installation["id"]

        response = requests.get(
            (
                f"{GITHUB_API_URL}/user/installations/"
                f"{installation_id}/repositories"
            ),
            headers=headers,
            params={
                "per_page": 100,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        for repo in data.get("repositories", []):

            repositories.append({
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "owner": repo["owner"]["login"],
                "private": repo["private"],
                "description": repo.get("description"),
                "default_branch": repo["default_branch"],
            })

    return repositories