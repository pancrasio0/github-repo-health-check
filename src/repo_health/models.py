"""Domain models for public GitHub repository metadata."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Repository:
    """Metadata used to review how a public repository is presented."""

    name: str
    url: str
    archived: bool
    description: str | None = None
    license: str | None = None
    topics: tuple[str, ...] = ()
    updated_at: datetime | None = None
    language: str | None = None
