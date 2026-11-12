from datetime import UTC, datetime

from repo_health.models import Repository


def test_repository_stores_metadata() -> None:
    updated_at = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
    repository = Repository(
        name="example",
        url="https://github.com/octocat/example",
        archived=False,
        description="An example project",
        license="MIT",
        topics=("python", "cli"),
        updated_at=updated_at,
        language="Python",
    )

    assert repository.name == "example"
    assert repository.url == "https://github.com/octocat/example"
    assert repository.description == "An example project"
    assert repository.license == "MIT"
    assert repository.topics == ("python", "cli")
    assert repository.updated_at == updated_at
    assert repository.language == "Python"
    assert repository.archived is False


def test_repository_uses_empty_values_for_missing_metadata() -> None:
    repository = Repository(
        name="example",
        url="https://github.com/octocat/example",
        archived=True,
    )

    assert repository.description is None
    assert repository.license is None
    assert repository.topics == ()
    assert repository.updated_at is None
    assert repository.language is None
    assert repository.archived is True
