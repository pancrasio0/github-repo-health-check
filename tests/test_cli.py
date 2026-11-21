from pathlib import Path

import pytest

from repo_health import cli
from repo_health.api import GitHubAPIError
from repo_health.models import Repository


def repository() -> Repository:
    return Repository("demo", "https://github.com/octocat/demo", False)


class FakeClient:
    def __init__(self) -> None:
        self.called: tuple[str, str] | None = None

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def list_user_repositories(self, account: str) -> list[Repository]:
        self.called = ("user", account)
        return [repository()]

    def list_organization_repositories(self, account: str) -> list[Repository]:
        self.called = ("organization", account)
        return [repository()]


def test_cli_prints_summary_and_uses_user_endpoint(monkeypatch, capsys) -> None:
    client = FakeClient()
    monkeypatch.setattr(cli, "GitHubClient", lambda: client)

    assert cli.main(["octocat"]) == 0

    assert client.called == ("user", "octocat")
    assert "Repositorios revisados: 1" in capsys.readouterr().out


def test_cli_supports_organization_and_markdown_output(monkeypatch, tmp_path: Path, capsys) -> None:
    client = FakeClient()
    monkeypatch.setattr(cli, "GitHubClient", lambda: client)
    output = tmp_path / "report.md"

    assert cli.main(["octo-org", "--organization", "--output", str(output)]) == 0

    assert client.called == ("organization", "octo-org")
    assert "# Informe de GitHub Repo Health Check" in output.read_text(encoding="utf-8")
    assert "Informe guardado" in capsys.readouterr().out


@pytest.mark.parametrize("args", [[], ["   "]])
def test_cli_rejects_missing_or_empty_account(args: list[str], capsys) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(args)

    assert error.value.code == 2
    error_text = capsys.readouterr().err.lower()
    assert "account" in error_text or "cuenta" in error_text


def test_cli_handles_api_errors_without_traceback(monkeypatch, capsys) -> None:
    class FailingClient(FakeClient):
        def list_user_repositories(self, account: str) -> list[Repository]:
            raise GitHubAPIError("falló", status_code=500)

    monkeypatch.setattr(cli, "GitHubClient", FailingClient)

    assert cli.main(["octocat"]) == 1
    captured = capsys.readouterr()
    assert "falló" in captured.err
    assert "Traceback" not in captured.err


def test_cli_reports_output_write_errors(monkeypatch, tmp_path: Path, capsys) -> None:
    client = FakeClient()
    monkeypatch.setattr(cli, "GitHubClient", lambda: client)
    directory = tmp_path / "missing-parent" / "report.md"

    assert cli.main(["octocat", "--output", str(directory)]) == 1
    assert "No se pudo escribir" in capsys.readouterr().err


def test_help_explains_account_and_options(capsys) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["--help"])

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "usuario u organización" in output
    assert "--output" in output
