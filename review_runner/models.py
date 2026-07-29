from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    BINARY = "binary"


class InclusionStatus(str, Enum):
    FULL = "fully_reviewed"
    PARTIAL = "partially_included"
    SKIPPED = "skipped"


@dataclass
class DiffLine:
    kind: str
    text: str
    old_line: int | None = None
    new_line: int | None = None


@dataclass
class DiffHunk:
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine] = field(default_factory=list)

    def render(self) -> str:
        return "\n".join([self.header, *(line.text for line in self.lines)])


@dataclass
class DiffFile:
    path: str
    previous_path: str | None
    change_type: ChangeType
    headers: list[str]
    hunks: list[DiffHunk]
    binary: bool = False
    added_lines: int = 0
    removed_lines: int = 0
    status: InclusionStatus = InclusionStatus.FULL

    def render_headers(self) -> str:
        return "\n".join(self.headers)

    def render(self) -> str:
        sections = [self.render_headers(), *(hunk.render() for hunk in self.hunks)]
        return "\n".join(section for section in sections if section)


@dataclass(frozen=True)
class SkippedItem:
    path: str
    reason: str
    detail: str = ""
    hunk_header: str | None = None


@dataclass
class ReviewChunk:
    chunk_id: str
    content: str
    files: list[str]
    estimated_tokens: int
    hunk_headers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    file: str
    title: str
    explanation: str
    severity: str
    category: str
    line: int | None = None
    hunk: str | None = None


@dataclass
class ProviderResult:
    findings: list[Finding] = field(default_factory=list)
    valid: bool = True
    error_category: str | None = None


@dataclass
class ChunkResult:
    chunk_id: str
    result: ProviderResult | None = None
    error_category: str | None = None


@dataclass
class ReviewResult:
    findings: list[Finding]
    skipped: list[SkippedItem]
    processed_chunks: list[str]
    failed_chunks: dict[str, str]
    generated_chunks: list[str]
    file_statuses: dict[str, InclusionStatus]
    redaction_count: int
    estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
