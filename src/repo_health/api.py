"""Read public repository metadata from the GitHub REST API."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx

from repo_health.models import Repository


class GitHubError(Exception):
    """Base class for user-facing GitHub client errors."""


class GitHubAPIError(GitHubError):
    """An HTTP error response from GitHub."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubNotFoundError(GitHubAPIError):
    """The requested user or organization does not exist."""


class GitHubRateLimitError(GitHubAPIError):
    """GitHub rate-limited the request and provided optional retry information."""

    def __init__(
        self,
        *,
        status_code: int,
        retry_after: str | None,
        rate_limit_reset: str | None,
    ) -> None:
        message = "GitHub limitó las solicitudes. No se reintentó automáticamente."
        if retry_after:
            message += f" Retry-After: {retry_after}."
        elif rate_limit_reset:
            message += f" El límite se restablece en UTC (epoch): {rate_limit_reset}."
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after
        self.rate_limit_reset = rate_limit_reset


class GitHubNetworkError(GitHubError):
    """A timeout or connection error prevented reaching GitHub."""


class GitHubInvalidResponseError(GitHubError):
    """GitHub returned a response that does not match the expected format."""


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
        """Return all public repositories owned by a user."""
        path = f"/users/{quote(username, safe='')}/repos"
        return self._list_repositories(path, {"type": "owner", "per_page": 100})

    def list_organization_repositories(self, organization: str) -> list[Repository]:
        """Return all public repositories owned by an organization."""
        path = f"/orgs/{quote(organization, safe='')}/repos"
        return self._list_repositories(path, {"type": "public", "per_page": 100})

    def _list_repositories(self, path: str, params: dict[str, str | int]) -> list[Repository]:
        response = self._get(path, params=params)
        repositories: list[Repository] = []
        visited_urls = {str(response.url)}

        while True:
            items = self._repository_items(response)
            repositories.extend(self._to_repository(item) for item in items)

            next_link = response.links.get("next")
            if next_link is None:
                return repositories

            try:
                next_url = httpx.URL(next_link["url"])
            except (KeyError, ValueError, httpx.InvalidURL) as error:
                raise GitHubInvalidResponseError(
                    "GitHub devolvió un enlace de paginación inválido."
                ) from error
            if (
                next_url.scheme != "https"
                or next_url.host != "api.github.com"
                or next_url.port not in (None, 443)
            ):
                raise GitHubInvalidResponseError(
                    "GitHub devolvió un enlace de paginación fuera de api.github.com."
                )
            if str(next_url) in visited_urls:
                raise GitHubInvalidResponseError(
                    "GitHub devolvió un enlace de paginación repetido."
                )

            visited_urls.add(str(next_url))
            response = self._get(next_url)

    def _get(
        self,
        url: str | httpx.URL,
        *,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as error:
            raise GitHubNetworkError(
                "La solicitud a GitHub superó el tiempo límite; inténtalo nuevamente más tarde."
            ) from error
        except httpx.RequestError as error:
            raise GitHubNetworkError(
                "No se pudo conectar con GitHub; revisa la conexión e inténtalo nuevamente."
            ) from error

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            self._raise_api_error(response, error)

        return response

    @staticmethod
    def _raise_api_error(response: httpx.Response, cause: httpx.HTTPStatusError) -> None:
        status = response.status_code
        if status == 404:
            raise GitHubNotFoundError(
                "No se encontró el usuario u organización solicitados.", status_code=status
            ) from cause

        if status in (403, 429) and GitHubClient._is_rate_limited(response):
            raise GitHubRateLimitError(
                status_code=status,
                retry_after=response.headers.get("Retry-After"),
                rate_limit_reset=response.headers.get("X-RateLimit-Reset"),
            ) from cause

        raise GitHubAPIError(
            f"GitHub devolvió un error HTTP {status}.", status_code=status
        ) from cause

    @staticmethod
    def _is_rate_limited(response: httpx.Response) -> bool:
        return (
            response.status_code == 429
            or response.headers.get("X-RateLimit-Remaining") == "0"
            or "rate limit" in response.text.lower()
        )

    @staticmethod
    def _repository_items(response: httpx.Response) -> list[dict[str, object]]:
        try:
            data = response.json()
        except ValueError as error:
            raise GitHubInvalidResponseError("GitHub devolvió JSON inválido.") from error

        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise GitHubInvalidResponseError(
                "GitHub devolvió una respuesta con formato inesperado."
            )
        return data

    @staticmethod
    def _to_repository(data: dict[str, object]) -> Repository:
        name = data.get("name")
        url = data.get("html_url")
        archived = data.get("archived")
        if not isinstance(name, str) or not isinstance(url, str) or not isinstance(archived, bool):
            raise GitHubInvalidResponseError("GitHub devolvió metadatos de repositorio inválidos.")

        description = data.get("description")
        language = data.get("language")
        if (description is not None and not isinstance(description, str)) or (
            language is not None and not isinstance(language, str)
        ):
            raise GitHubInvalidResponseError("GitHub devolvió metadatos de repositorio inválidos.")

        license_data = data.get("license")
        if license_data is None:
            license_name = None
        elif isinstance(license_data, dict):
            license_name = license_data.get("name")
            if license_name is not None and not isinstance(license_name, str):
                raise GitHubInvalidResponseError(
                    "GitHub devolvió metadatos de repositorio inválidos."
                )
        else:
            raise GitHubInvalidResponseError("GitHub devolvió metadatos de licencia inválidos.")

        topics_data = data.get("topics")
        if topics_data is None:
            topics: tuple[str, ...] = ()
        elif isinstance(topics_data, list) and all(isinstance(topic, str) for topic in topics_data):
            topics = tuple(topics_data)
        else:
            raise GitHubInvalidResponseError("GitHub devolvió topics con formato inválido.")

        updated_at = data.get("updated_at")
        if updated_at is not None and not isinstance(updated_at, str):
            raise GitHubInvalidResponseError(
                "GitHub devolvió la fecha de actualización con formato inválido."
            )

        try:
            return Repository(
                name=name,
                url=url,
                archived=archived,
                description=description,
                license=license_name,
                topics=topics,
                updated_at=(
                    datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if isinstance(updated_at, str)
                    else None
                ),
                language=language,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubInvalidResponseError(
                "GitHub devolvió metadatos de repositorio inválidos."
            ) from error

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
