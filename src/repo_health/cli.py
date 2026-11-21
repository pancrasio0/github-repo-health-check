"""Command-line interface for Repo Health Check."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from repo_health.api import GitHubClient, GitHubError
from repo_health.checks import Finding, Severity, analyze_repository
from repo_health.models import Repository
from repo_health.report import render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-health",
        description="Revisa metadatos públicos de repositorios de una cuenta de GitHub.",
        epilog="Ejemplo: repo-health octocat --output informe.md",
    )
    parser.add_argument("account", help="nombre público de usuario u organización en GitHub")
    parser.add_argument(
        "--organization",
        action="store_true",
        help="interpreta la cuenta como organización (por defecto, usuario)",
    )
    parser.add_argument("--output", type=Path, metavar="ARCHIVO", help="guarda un informe Markdown")
    return parser


def _print_summary(reviews: list[tuple[Repository, list[Finding]]]) -> None:
    counts = Counter(finding.severity for _, findings in reviews for finding in findings)
    print(f"Repositorios revisados: {len(reviews)}")
    print("Hallazgos por severidad:")
    for severity in (Severity.MEDIUM, Severity.LOW, Severity.INFORMATIVE):
        print(f"  {severity.value.capitalize()}: {counts[severity]}")
    for repository, findings in reviews:
        if findings:
            print(f"\n{repository.name}:")
            for finding in findings:
                print(f"  [{finding.severity.value}] {finding.summary}")
                print(f"    Sugerencia: {finding.suggestion}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.account.strip():
        parser.error("la cuenta no puede estar vacía")

    try:
        with GitHubClient() as client:
            repositories = (
                client.list_organization_repositories(args.account)
                if args.organization
                else client.list_user_repositories(args.account)
            )
        reviews = [(repo, analyze_repository(repo)) for repo in repositories]
        _print_summary(reviews)
        if args.output is not None:
            args.output.write_text(render_markdown(reviews), encoding="utf-8")
            print(f"Informe guardado en: {args.output}")
    except GitHubError as error:
        print(str(error), file=sys.stderr)
        return 1
    except OSError as error:
        print(f"No se pudo escribir el informe: {error}", file=sys.stderr)
        return 1
    return 0
