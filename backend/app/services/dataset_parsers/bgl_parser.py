"""
BGL (BlueGene/L) dataset parser.

Line format from the Loghub BGL dataset:
  - 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.363779 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected

Fields (space-delimited, 9 fixed tokens + message):
  [0] label        — "-" for normal, alert category string for anomalous
  [1] unix_ts      — unix epoch seconds
  [2] date         — YYYY.MM.DD
  [3] node         — hardware location identifier
  [4] precise_ts   — YYYY-MM-DD-HH.MM.SS.microseconds
  [5] node         — repeated
  [6] category     — e.g. RAS
  [7] component    — e.g. KERNEL, APP
  [8] level        — INFO, WARN, ERROR, FATAL, etc.
  [9+] message     — free-form text

The ground-truth label (token 0) is not stored in LogEntry AI fields;
those remain null/not_run per the schema contract. The label is preserved
only for future evaluation pipelines.
"""

import re
import uuid
from pathlib import Path
from typing import Optional
from app.models.schemas import LogEntry, DatasetInfo
from app.services.dataset_parsers.base_dataset_parser import BaseDatasetParser

KNOWN_LEVELS = {"INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL", "DEBUG", "TRACE", "SEVERE", "FAILURE"}


def _format_bgl_timestamp(precise_ts: str) -> str:
    """Convert 2005-06-03-15.42.50.363779 to 2005-06-03 15:42:50."""
    # Format: YYYY-MM-DD-HH.MM.SS.micros
    m = re.match(r"(\d{4}-\d{2}-\d{2})-(\d{2})\.(\d{2})\.(\d{2})", precise_ts)
    if m:
        return f"{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}"
    return precise_ts


class BGLParser(BaseDatasetParser):
    dataset_name = "BGL"
    file_pattern = "BGL.log"

    def parse_file(self, filepath: Path, max_lines: Optional[int] = None, start_line: int = 1) -> list[LogEntry]:
        raw_lines = self._read_lines(filepath, max_lines, start_line)
        entries: list[LogEntry] = []
        line_offset = max(0, start_line - 1)

        for idx, raw_line in enumerate(raw_lines):
            stripped = raw_line.strip()
            if not stripped:
                continue

            real_line = line_offset + idx + 1
            entry_id = f"bgl-{real_line}-{uuid.uuid4().hex[:8]}"
            tokens = stripped.split(None, 9)

            if len(tokens) >= 10 and tokens[8].upper() in KNOWN_LEVELS:
                timestamp = _format_bgl_timestamp(tokens[4])
                source = tokens[3]
                component = tokens[7]
                level = tokens[8].upper()
                message = tokens[9]
                ground_truth = "normal" if tokens[0] == "-" else "anomaly"

                entries.append(LogEntry(
                    id=entry_id,
                    line_number=real_line,
                    raw_line=stripped,
                    timestamp=timestamp,
                    level=level,
                    source=f"{source} {component}",
                    message=message,
                    parse_status="parsed",
                    ground_truth=ground_truth,
                ))
            else:
                entries.append(LogEntry(
                    id=entry_id,
                    line_number=real_line,
                    raw_line=stripped,
                    message=stripped,
                    parse_status="fallback",
                ))

        return entries

    def dataset_info(self) -> DatasetInfo:
        return DatasetInfo(
            name=self.dataset_name,
            description="BlueGene/L supercomputer logs from LLNL (Loghub). "
                        "4.7M lines with alert/non-alert labels for anomaly detection.",
            path=f"raw/{self.dataset_name}/{self.file_pattern}",
            format="bgl",
        )
