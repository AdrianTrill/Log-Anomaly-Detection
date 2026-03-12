"""
Parser service: converts raw log lines into structured LogEntry objects.

Supports multiple common log formats via a chain of regex matchers:
  1. Structured — YYYY-MM-DD HH:MM:SS LEVEL source message
  2. Bracketed  — [YYYY-MM-DD HH:MM:SS] [LEVEL] [source] message
  3. Syslog     — Mon DD HH:MM:SS hostname service[pid]: message
  4. ISO 8601   — YYYY-MM-DDTHH:MM:SS(Z|+offset) LEVEL source message

Lines that don't match any pattern are handled by a fallback parser that
still attempts to extract a log level keyword and any leading timestamp.
"""

import re
import uuid
from typing import Optional, Dict
from app.models.schemas import LogEntry

# --- Pattern 1: Structured ---
# Matches: 2026-03-09 10:22:00 ERROR auth-service Failed login for user 123
STRUCTURED_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\s+"
    r"(\S+)\s+"
    r"(.+)$",
    re.IGNORECASE,
)

# --- Pattern 2: Bracketed ---
# Matches: [2026-03-09 10:22:00] [WARN] [db] Connection slow
BRACKETED_PATTERN = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+"
    r"\[(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\]\s+"
    r"\[([^\]]+)\]\s+"
    r"(.+)$",
    re.IGNORECASE,
)

# --- Pattern 3: Syslog ---
# Matches: Mar  9 10:22:00 myhost auth-service[1234]: Failed login
SYSLOG_PATTERN = re.compile(
    r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"                           # hostname
    r"(\S+?)(?:\[\d+\])?:\s+"             # service (with optional [pid])
    r"(.+)$",
    re.IGNORECASE,
)

# --- Pattern 4: ISO 8601 timestamp ---
# Matches: 2026-03-09T10:22:00Z ERROR auth-service Failed login
ISO_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\s+"
    r"(\S+)\s+"
    r"(.+)$",
    re.IGNORECASE,
)

# Used by fallback to detect a level keyword anywhere in the line
LEVEL_KEYWORD_PATTERN = re.compile(
    r"\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\b", re.IGNORECASE
)

# Used by fallback to detect a leading date-like pattern
FALLBACK_TIMESTAMP_PATTERN = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}\S*)"
)


def _try_structured(line: str) -> Optional[Dict[str, str]]:
    m = STRUCTURED_PATTERN.match(line)
    if m:
        return {
            "timestamp": m.group(1),
            "level": m.group(2).upper(),
            "source": m.group(3),
            "message": m.group(4),
        }
    return None


def _try_bracketed(line: str) -> Optional[Dict[str, str]]:
    m = BRACKETED_PATTERN.match(line)
    if m:
        return {
            "timestamp": m.group(1),
            "level": m.group(2).upper(),
            "source": m.group(3),
            "message": m.group(4),
        }
    return None


def _try_syslog(line: str) -> Optional[Dict[str, str]]:
    m = SYSLOG_PATTERN.match(line)
    if m:
        return {
            "timestamp": m.group(1),
            "level": None,  # syslog doesn't embed a level keyword
            "source": m.group(3),
            "message": m.group(4),
        }
    return None


def _try_iso(line: str) -> Optional[Dict[str, str]]:
    m = ISO_PATTERN.match(line)
    if m:
        return {
            "timestamp": m.group(1),
            "level": m.group(2).upper(),
            "source": m.group(3),
            "message": m.group(4),
        }
    return None


def _fallback_parse(line: str) -> dict:
    """Best-effort extraction when no structured pattern matches."""
    level_match = LEVEL_KEYWORD_PATTERN.search(line)
    ts_match = FALLBACK_TIMESTAMP_PATTERN.match(line)
    return {
        "timestamp": ts_match.group(1) if ts_match else None,
        "level": level_match.group(1).upper() if level_match else None,
        "source": None,
        "message": line,
    }


# Parser chain: try each format in order, fall back to best-effort extraction
_PARSERS = [_try_structured, _try_bracketed, _try_syslog, _try_iso]


def parse_log_lines(lines: list[str]) -> list[LogEntry]:
    """Parse a list of raw log lines into structured LogEntry objects."""
    entries: list[LogEntry] = []

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped:
            continue

        entry_id = f"entry-{idx + 1}-{uuid.uuid4().hex[:8]}"

        parsed = None
        for parser in _PARSERS:
            parsed = parser(stripped)
            if parsed:
                break

        if parsed:
            entries.append(
                LogEntry(
                    id=entry_id,
                    line_number=idx + 1,
                    raw_line=stripped,
                    timestamp=parsed["timestamp"],
                    level=parsed["level"],
                    source=parsed["source"],
                    message=parsed["message"],
                    parse_status="parsed",
                )
            )
        else:
            fallback = _fallback_parse(stripped)
            entries.append(
                LogEntry(
                    id=entry_id,
                    line_number=idx + 1,
                    raw_line=stripped,
                    timestamp=fallback["timestamp"],
                    level=fallback["level"],
                    source=fallback["source"],
                    message=fallback["message"],
                    parse_status="fallback",
                )
            )

    return entries
