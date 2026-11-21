"""Markdown report rendering for repository reviews."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

from repo_health.checks import Finding, Severity
from repo_health.models import Repository


def _escape_markdown(value: str) -> str:
    """Escape untrusted text and flatten line breaks to keep report structure intact."""
    flattened = " ".join(value.splitlines())
    special = "\\`*_{}[]()#+-.!|>"
    return "".join(
        f"\\{character}" if character in special else character for character in flattened
    )


def render_markdown(
    reviews: Sequence[tuple[Repository, Sequence[Finding]]],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render repository findings with a stable, injectable generation timestamp."""
    created = generated_at or datetime.now(UTC)
    if created.tzinfo is None or created.utcoffset() is None:
        raise ValueError("generated_at debe incluir una zona horaria.")
    created = created.astimezone(UTC)
    counts = Counter(finding.severity for _, findings in reviews for finding in findings)

    lines = [
        "# Informe de GitHub Repo Health Check",
        "",
        f"Generado: {created.isoformat()}",
        "",
        "## Resumen",
        "",
        f"- Repositorios revisados: {len(reviews)}",
        f"- Hallazgos de severidad media: {counts[Severity.MEDIUM]}",
        f"- Hallazgos de severidad baja: {counts[Severity.LOW]}",
        f"- Hallazgos informativos: {counts[Severity.INFORMATIVE]}",
        "",
        "## Repositorios",
        "",
    ]
    for repository, findings in reviews:
        lines.extend(
            [
                f"### {_escape_markdown(repository.name)}",
                "",
                f"URL: {_escape_markdown(repository.url)}",
                "",
            ]
        )
        if not findings:
            lines.extend(["Sin hallazgos.", ""])
            continue
        for finding in findings:
            lines.extend(
                [
                    f"- **{finding.severity.value.capitalize()}** — "
                    f"{_escape_markdown(finding.summary)}",
                    f"  - Sugerencia: {_escape_markdown(finding.suggestion)}",
                ]
            )
        lines.append("")
    return "\n".join(lines)
