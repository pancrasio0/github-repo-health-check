from datetime import UTC, datetime

import httpx
import pytest

from repo_health.api import (
    GitHubAPIError,
    GitHubClient,
    GitHubInvalidResponseError,
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


def test_lists_public_user_repositories_and_maps_metadata() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/users/octocat/repos"
        assert request.url.params["type"] == "owner"
        assert request.url.params["per_page"] == "100"
        assert request.headers["Accept"] == "application/vnd.github+json"
        assert request.extensions["timeout"]["read"] == 10.0
        return httpx.Response(
            200,
            json=[
                {
                    "name": "hello-world",
                    "html_url": "https://github.com/octocat/hello-world",
                    "archived": False,
                    "description": "An example project",
                    "license": {"name": "MIT License", "spdx_id": "MIT"},
                    "topics": ["python", "cli"],
                    "updated_at": "2026-11-12T10:30:00Z",
                    "language": "Python",
                }
            ],
        )

    transport = httpx.MockTransport(respond)
    with GitHubClient(transport=transport) as client:
        repositories = client.list_user_repositories("octocat")

    assert len(repositories) == 1
    repository = repositories[0]
    assert repository.name == "hello-world"
    assert repository.url == "https://github.com/octocat/hello-world"
    assert repository.description == "An example project"
    assert repository.license == "MIT License"
    assert repository.topics == ("python", "cli")
    assert repository.updated_at == datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
    assert repository.language == "Python"
    assert repository.archived is False


def test_lists_public_organization_repositories() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/orgs/github/repos"
        assert request.url.params["type"] == "public"
        return httpx.Response(
            200,
            json=[{"name": "docs", "html_url": "https://github.com/github/docs", "archived": True}],
        )

    with GitHubClient(transport=httpx.MockTransport(respond)) as client:
        repositories = client.list_organization_repositories("github")

    assert len(repositories) == 1
    assert repositories[0].name == "docs"
    assert repositories[0].archived is True
    assert repositories[0].description is None
    assert repositories[0].license is None
    assert repositories[0].topics == ()
    assert repositories[0].updated_at is None
    assert repositories[0].language is None


def test_follows_next_links_and_preserves_repository_order() -> None:
    requested_pages: list[str | None] = []

    def respond(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        requested_pages.append(page)
        if page is None:
            return httpx.Response(
                200,
                json=[
                    {
                        "name": "first",
                        "html_url": "https://github.com/octocat/first",
                        "archived": False,
                    }
                ],
                headers={
                    "Link": (
                        "<https://api.github.com/users/octocat/repos?type=owner&"
                        'per_page=100&page=2>; rel="next"'
                    )
                },
            )

        assert page == "2"
        return httpx.Response(
            200,
            json=[
                {
                    "name": "second",
                    "html_url": "https://github.com/octocat/second",
                    "archived": False,
                }
            ],
        )

    with GitHubClient(transport=httpx.MockTransport(respond)) as client:
        repositories = client.list_user_repositories("octocat")

    assert requested_pages == [None, "2"]
    assert [repository.name for repository in repositories] == ["first", "second"]


def test_rejects_pagination_links_outside_github() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=[],
            headers={"Link": '<https://example.com/page/2>; rel="next"'},
        )
    )

    with GitHubClient(transport=transport) as client:
        with pytest.raises(GitHubInvalidResponseError, match="fuera de api.github.com"):
            client.list_user_repositories("octocat")


def test_translates_not_found_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, json={"message": "Not Found"})
    )

    with GitHubClient(transport=transport) as client:
        with pytest.raises(GitHubNotFoundError) as error:
            client.list_user_repositories("missing-user")

    assert error.value.status_code == 404
    assert "No se encontró" in str(error.value)


def test_translates_primary_rate_limit_and_exposes_reset_time_without_retry() -> None:
    requests = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1790000000"},
        )

    with GitHubClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(GitHubRateLimitError) as error:
            client.list_user_repositories("octocat")

    assert requests == 1
    assert error.value.status_code == 403
    assert error.value.rate_limit_reset == "1790000000"
    assert error.value.retry_after is None
    assert "1790000000" in str(error.value)


def test_translates_secondary_rate_limit_and_exposes_retry_after() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429,
            json={"message": "You have exceeded a secondary rate limit."},
            headers={"Retry-After": "60"},
        )
    )

    with GitHubClient(transport=transport) as client:
        with pytest.raises(GitHubRateLimitError) as error:
            client.list_user_repositories("octocat")

    assert error.value.retry_after == "60"
    assert "Retry-After: 60" in str(error.value)


def test_translates_server_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"message": "error"}))

    with GitHubClient(transport=transport) as client:
        with pytest.raises(GitHubAPIError, match="HTTP 500") as error:
            client.list_user_repositories("octocat")

    assert error.value.status_code == 500


def test_translates_timeout_and_connection_errors() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with GitHubClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(GitHubNetworkError, match="tiempo límite"):
            client.list_user_repositories("octocat")

    def connection_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with GitHubClient(transport=httpx.MockTransport(connection_error)) as client:
        with pytest.raises(GitHubNetworkError, match="No se pudo conectar"):
            client.list_user_repositories("octocat")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json", headers={"Content-Type": "application/json"}),
        httpx.Response(200, json={"unexpected": "object"}),
        httpx.Response(200, json=[{"unexpected": "repository shape"}]),
        httpx.Response(
            200,
            json=[{"name": None, "html_url": "https://github.com/octocat/repo", "archived": False}],
        ),
        httpx.Response(
            200,
            json=[
                {
                    "name": "repo",
                    "html_url": "https://github.com/octocat/repo",
                    "archived": False,
                    "topics": "python",
                }
            ],
        ),
    ],
    ids=[
        "malformed-json",
        "unexpected-top-level-shape",
        "missing-repository-fields",
        "wrong-required-field-type",
        "wrong-topics-type",
    ],
)
def test_translates_invalid_responses(response: httpx.Response) -> None:
    transport = httpx.MockTransport(lambda request: response)

    with GitHubClient(transport=transport) as client:
        with pytest.raises(GitHubInvalidResponseError):
            client.list_user_repositories("octocat")
