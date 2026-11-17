"""Transparent, informational checks for repository metadata."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from repo_health.models import Repository

INACTIVITY_DAYS = 365


class Severity(StrEnum):
    """Severity describes a suggested metadata improvement, not repository quality."""

    INFORMATIVE = "informativa"
    LOW = "baja"
    MEDIUM = "media"


@dataclass(frozen=True, slots=True)
class Finding:
    """A transparent observation and a concrete next step."""

    code: str
    severity: Severity
    summary: str
    suggestion: str


def analyze_repository(
    repository: Repository,
    *,
    as_of: datetime | None = None,
) -> list[Finding]:
    """Return metadata findings without assigning an overall score."""
    current_time = as_of or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("as_of debe incluir una zona horaria.")
    current_time = current_time.astimezone(UTC)

    findings: list[Finding] = []
    if not (repository.description or "").strip():
        findings.append(
            Finding(
                code="missing-description",
                severity=Severity.MEDIUM,
                summary="El repositorio no tiene descripción.",
                suggestion="Añade una frase que explique su propósito y uso.",
            )
        )
    if not (repository.license or "").strip():
        findings.append(
            Finding(
                code="missing-license",
                severity=Severity.MEDIUM,
                summary="El repositorio no declara una licencia.",
                suggestion="Añade una licencia para aclarar la reutilización.",
            )
        )
    if not repository.topics:
        findings.append(
            Finding(
                code="missing-topics",
                severity=Severity.LOW,
                summary="El repositorio no tiene topics.",
                suggestion="Añade topics que describan sus tecnologías y propósito.",
            )
        )
    if repository.archived:
        findings.append(
            Finding(
                code="archived",
                severity=Severity.INFORMATIVE,
                summary="El repositorio está archivado.",
                suggestion="Si el archivo es intencional, no requiere cambios.",
            )
        )

    updated_at = repository.updated_at
    if (
        updated_at is not None
        and updated_at.tzinfo is not None
        and updated_at.utcoffset() is not None
        and updated_at.astimezone(UTC) < current_time - timedelta(days=INACTIVITY_DAYS)
    ):
        findings.append(
            Finding(
                code="inactive",
                severity=Severity.INFORMATIVE,
                summary=f"El repositorio no se actualiza hace más de {INACTIVITY_DAYS} días.",
                suggestion="La inactividad no implica mala calidad; confirma si sigue vigente.",
            )
        )

    return findings
