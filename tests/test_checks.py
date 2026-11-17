from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from repo_health.checks import INACTIVITY_DAYS, Severity, analyze_repository
from repo_health.models import Repository

AS_OF = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def repository(**changes: object) -> Repository:
    base = Repository(
        name="example",
        url="https://github.com/octocat/example",
        archived=False,
        description="Example project",
        license="MIT",
        topics=("python",),
        updated_at=AS_OF,
        language="Python",
    )
    return replace(base, **changes)


def test_reports_missing_description_license_and_topics() -> None:
    findings = analyze_repository(
        repository(description="  ", license=None, topics=()),
        as_of=AS_OF,
    )

    assert [finding.code for finding in findings] == [
        "missing-description",
        "missing-license",
        "missing-topics",
    ]
    assert [finding.severity for finding in findings] == [
        Severity.MEDIUM,
        Severity.MEDIUM,
        Severity.LOW,
    ]
    assert all(finding.suggestion for finding in findings)


def test_reports_archived_repository_as_informative() -> None:
    findings = analyze_repository(repository(archived=True), as_of=AS_OF)

    assert [finding.code for finding in findings] == ["archived"]
    assert findings[0].severity is Severity.INFORMATIVE
    assert "no requiere cambios" in findings[0].suggestion


def test_reports_inactivity_only_after_365_days_as_informative() -> None:
    old_update = AS_OF - timedelta(days=INACTIVITY_DAYS, seconds=1)

    findings = analyze_repository(repository(updated_at=old_update), as_of=AS_OF)

    assert [finding.code for finding in findings] == ["inactive"]
    assert findings[0].severity is Severity.INFORMATIVE
    assert "no implica mala calidad" in findings[0].suggestion


def test_does_not_report_activity_at_exact_365_day_boundary() -> None:
    updated_at = AS_OF - timedelta(days=INACTIVITY_DAYS)

    findings = analyze_repository(repository(updated_at=updated_at), as_of=AS_OF)

    assert "inactive" not in [finding.code for finding in findings]


@pytest.mark.parametrize("updated_at", [None, datetime(2025, 1, 1)])
def test_skips_activity_check_when_date_is_missing_or_timezone_naive(
    updated_at: datetime | None,
) -> None:
    findings = analyze_repository(repository(updated_at=updated_at), as_of=AS_OF)

    assert "inactive" not in [finding.code for finding in findings]


def test_rejects_naive_analysis_time() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        analyze_repository(repository(), as_of=datetime(2026, 11, 16, 12, 0))


def test_clean_repository_has_no_findings() -> None:
    assert analyze_repository(repository(), as_of=AS_OF) == []
