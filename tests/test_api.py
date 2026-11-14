from datetime import UTC, datetime

import httpx
import pytest

from repo_health.api import GitHubClient


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
        with pytest.raises(ValueError, match="outside api.github.com"):
            client.list_user_repositories("octocat")


def test_raises_for_http_error_status() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, json={"message": "Not Found"})
    )

    with GitHubClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError) as error:
            client.list_user_repositories("missing-user")

    assert error.value.response.status_code == 404
