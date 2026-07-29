from __future__ import annotations

import re

from .models import (
    ChunkResult,
    Finding,
    InclusionStatus,
    ReviewChunk,
    ReviewResult,
    SkippedItem,
)


def aggregate_results(
    chunks: list[ReviewChunk],
    chunk_results: list[ChunkResult],
    skipped: list[SkippedItem],
    file_statuses: dict[str, InclusionStatus],
    redaction_count: int,
) -> ReviewResult:
    findings: dict[tuple[object, ...], Finding] = {}
    processed: list[str] = []
    failed: dict[str, str] = {}
    for chunk_result in chunk_results:
        if chunk_result.error_category:
            failed[chunk_result.chunk_id] = chunk_result.error_category
            continue
        result = chunk_result.result
        if result is None or not result.valid:
            failed[chunk_result.chunk_id] = result.error_category if result else "empty_response"
            continue
        processed.append(chunk_result.chunk_id)
        for finding in result.findings:
            findings.setdefault(_dedupe_key(finding), finding)

    ordered = sorted(
        findings.values(),
        key=lambda finding: (
            finding.file.casefold(), finding.line is None, finding.line or 0,
            finding.category.casefold(), finding.title.casefold(),
            _normalize(finding.explanation),
        ),
    )
    return ReviewResult(
        findings=ordered,
        skipped=sorted(skipped, key=lambda item: (item.path, item.reason, item.hunk_header or "")),
        processed_chunks=sorted(processed),
        failed_chunks=dict(sorted(failed.items())),
        generated_chunks=[chunk.chunk_id for chunk in chunks],
        file_statuses=dict(sorted(file_statuses.items())),
        redaction_count=redaction_count,
        estimated_tokens=sum(chunk.estimated_tokens for chunk in chunks),
    )


def _dedupe_key(finding: Finding) -> tuple[object, ...]:
    return (
        finding.file.casefold(),
        finding.line,
        _normalize(finding.hunk or ""),
        finding.category.casefold().strip(),
        _normalize(finding.title),
        _normalize(finding.explanation),
    )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
