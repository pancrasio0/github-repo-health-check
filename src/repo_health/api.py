"""Read public repository metadata from the GitHub REST API."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx

from repo_health.models import Repository


class GitHubClient:
    """Small HTTP client for listing public repositories."""

    def __init__(
        self,
        timeout: float = 10.0,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout,
            transport=transport,
        )

    def list_user_repositories(self, username: str) -> list[Repository]:
        """Return the first page of public repositories owned by a user."""
        path = f"/users/{quote(username, safe='')}/repos"
        return self._list_repositories(path, {"type": "owner", "per_page": 100})

    def list_organization_repositories(self, organization: str) -> list[Repository]:
        """Return the first page of public repositories owned by an organization."""
        path = f"/orgs/{quote(organization, safe='')}/repos"
        return self._list_repositories(path, {"type": "public", "per_page": 100})

    def _list_repositories(self, path: str, params: dict[str, str | int]) -> list[Repository]:
        response = self._client.get(path, params=params)
        response.raise_for_status()

        return [self._to_repository(item) for item in response.json()]

    @staticmethod
    def _to_repository(data: dict[str, object]) -> Repository:
        license_data = data.get("license")
        license_name = license_data.get("name") if isinstance(license_data, dict) else None
        updated_at = data.get("updated_at")

        return Repository(
            name=data["name"],
            url=data["html_url"],
            archived=data["archived"],
            description=data.get("description"),
            license=license_name,
            topics=tuple(data.get("topics") or ()),
            updated_at=(
                datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if isinstance(updated_at, str)
                else None
            ),
            language=data.get("language"),
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
