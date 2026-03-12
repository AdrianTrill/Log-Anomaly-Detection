"""
Normalizer service: transforms parsed log entries into a standardized form.

Applies masking to sensitive/variable tokens (IPs, UUIDs, long numbers, file paths)
so that normalized messages can later be used for template extraction and ML input.
Masking order matters: IPs are replaced before long numbers to avoid partial matches
on IP octets, and UUIDs before numbers so hex-heavy UUIDs aren't partially masked.
"""

import re
from typing import Optional, Tuple
from app.models.schemas import LogEntry, NormalizationInfo

# Matches IPv4 addresses like 192.168.1.100
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

# Matches standard UUID format: 8-4-4-4-12 hex digits
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# Matches standalone numbers with 5+ digits (likely IDs, ports, durations)
LONG_NUM_PATTERN = re.compile(r"\b\d{5,}\b")

# Matches Unix-style absolute file paths like /var/log/app.log
PATH_PATTERN = re.compile(r"(?<!\w)/[a-zA-Z0-9_./-]{3,}")

# Maps non-standard level names to canonical forms
LEVEL_MAP = {
    "WARNING": "WARN",
}


def _normalize_message(message: str, info: NormalizationInfo) -> str:
    """Replace variable tokens with canonical placeholders for downstream ML use."""
    if not message:
        return message

    normalized = message.strip()

    # Order: IPs -> UUIDs -> numbers -> paths
    # IPs before numbers so octets like 192 aren't masked as <NUM>
    # UUIDs before numbers so hex segments aren't partially masked
    ip_count = len(IP_PATTERN.findall(normalized))
    if ip_count:
        info.ip_masked += ip_count
        normalized = IP_PATTERN.sub("<IP>", normalized)

    uuid_count = len(UUID_PATTERN.findall(normalized))
    if uuid_count:
        info.uuid_masked += uuid_count
        normalized = UUID_PATTERN.sub("<UUID>", normalized)

    num_count = len(LONG_NUM_PATTERN.findall(normalized))
    if num_count:
        info.num_masked += num_count
        normalized = LONG_NUM_PATTERN.sub("<NUM>", normalized)

    return normalized


def _standardize_level(level: Optional[str], info: NormalizationInfo) -> Optional[str]:
    """Uppercase and canonicalize log level names (e.g. WARNING -> WARN)."""
    if not level:
        return level
    upper = level.upper().strip()
    if upper != level:
        info.levels_standardized += 1
    if upper in LEVEL_MAP:
        info.levels_standardized += 1
        return LEVEL_MAP[upper]
    return upper


def normalize_entries(entries: list[LogEntry]) -> Tuple[list[LogEntry], NormalizationInfo]:
    """Normalize all entries in place: standardize levels and mask variable tokens."""
    info = NormalizationInfo()
    normalized: list[LogEntry] = []

    for entry in entries:
        entry.level = _standardize_level(entry.level, info)
        entry.normalized_message = _normalize_message(entry.message or entry.raw_line, info)
        normalized.append(entry)

    return normalized, info
