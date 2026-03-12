"""
Summarizer service: aggregates parsed log entries into dashboard-ready statistics.

Computes level distribution, source distribution, time range, and line counts.
These aggregations are returned alongside the full entry list in UploadResponse
so the frontend can render charts and summary cards without re-processing.
"""

from collections import Counter
from app.models.schemas import LogEntry, UploadResponse, NormalizationInfo, TimeRange


def generate_summary(
    entries: list[LogEntry],
    file_name: str,
    total_lines: int,
    normalization_info: NormalizationInfo,
) -> UploadResponse:
    parsed = sum(1 for e in entries if e.parse_status == "parsed")
    failed = sum(1 for e in entries if e.parse_status == "fallback")

    level_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    timestamps: list[str] = []

    for entry in entries:
        if entry.level:
            level_counts[entry.level] += 1
        if entry.source:
            source_counts[entry.source] += 1
        if entry.timestamp:
            timestamps.append(entry.timestamp)

    time_range = None
    if timestamps:
        sorted_ts = sorted(timestamps)
        time_range = TimeRange(earliest=sorted_ts[0], latest=sorted_ts[-1])

    return UploadResponse(
        file_name=file_name,
        total_lines=total_lines,
        parsed_lines=parsed,
        failed_lines=failed,
        level_distribution=dict(level_counts),
        source_distribution=dict(source_counts),
        time_range=time_range,
        entries=entries,
        normalization_info=normalization_info,
        ai_ready=True,
    )
