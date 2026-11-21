from datetime import UTC, datetime

import pytest

from repo_health.checks import Finding, Severity
from repo_health.models import Repository
from repo_health.report import render_markdown


def test_renders_date_summary_findings_and_suggestions() -> None:
    repo = Repository("demo", "https://github.com/octocat/demo", False)
    finding = Finding("missing-description", Severity.MEDIUM, "Falta descripción", "Añade una.")

    report = render_markdown([(repo, [finding])], generated_at=datetime(2026, 11, 20, tzinfo=UTC))

    assert "Generado: 2026-11-20T00:00:00+00:00" in report
    assert "Repositorios revisados: 1" in report
    assert "Hallazgos de severidad media: 1" in report
    assert "Falta descripción" in report
    assert "Sugerencia: Añade una\\." in report


def test_escapes_external_text_and_flattens_line_breaks() -> None:
    repo = Repository("demo](/evil)\n# injected", "https://github.com/x/y", False)
    finding = Finding("x", Severity.LOW, "*malicioso*\n## inyectado", "[enlace](evil)")

    report = render_markdown([(repo, [finding])])

    assert "demo\\]\\(/evil\\) \\# injected" in report
    assert "\\*malicioso\\* \\#\\# inyectado" in report
    assert "\\[enlace\\]\\(evil\\)" in report
    assert "\n## inyectado" not in report


def test_renders_empty_report_and_rejects_naive_generation_date() -> None:
    assert "Repositorios revisados: 0" in render_markdown([], generated_at=datetime.now(UTC))
    with pytest.raises(ValueError, match="zona horaria"):
        render_markdown([], generated_at=datetime(2026, 1, 1))
