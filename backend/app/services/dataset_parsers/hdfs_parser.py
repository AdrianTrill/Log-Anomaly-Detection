"""
HDFS dataset parser.

Line format from the Loghub HDFS_v1 dataset:
  081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 ...

Fields: YYMMDD HHMMSS pid LEVEL java.component: message
"""

import re
import uuid
from pathlib import Path
from typing import Optional
from app.models.schemas import LogEntry, DatasetInfo
from app.services.dataset_parsers.base_dataset_parser import BaseDatasetParser

# YYMMDD HHMMSS pid LEVEL component: message
HDFS_PATTERN = re.compile(
    r"^(\d{6})\s+(\d{6})\s+(\d+)\s+"
    r"(INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|DEBUG|TRACE)\s+"
    r"(\S+?):\s+"
    r"(.+)$",
    re.IGNORECASE,
)


def _format_hdfs_timestamp(date_part: str, time_part: str) -> str:
    """Convert YYMMDD HHMMSS to YYYY-MM-DD HH:MM:SS."""
    yy, mm, dd = date_part[:2], date_part[2:4], date_part[4:6]
    year = f"20{yy}" if int(yy) < 70 else f"19{yy}"
    hh, mi, ss = time_part[:2], time_part[2:4], time_part[4:6]
    return f"{year}-{mm}-{dd} {hh}:{mi}:{ss}"


class HDFSParser(BaseDatasetParser):
    dataset_name = "HDFS_v1"
    file_pattern = "HDFS.log"

    def parse_file(self, filepath: Path, max_lines: Optional[int] = None, start_line: int = 1) -> list[LogEntry]:
        raw_lines = self._read_lines(filepath, max_lines, start_line)
        entries: list[LogEntry] = []
        line_offset = max(0, start_line - 1)

        for idx, raw_line in enumerate(raw_lines):
            stripped = raw_line.strip()
            if not stripped:
                continue

            real_line = line_offset + idx + 1
            entry_id = f"hdfs-{real_line}-{uuid.uuid4().hex[:8]}"
            m = HDFS_PATTERN.match(stripped)

            if m:
                timestamp = _format_hdfs_timestamp(m.group(1), m.group(2))
                entries.append(LogEntry(
                    id=entry_id,
                    line_number=real_line,
                    raw_line=stripped,
                    timestamp=timestamp,
                    level=m.group(4).upper(),
                    source=m.group(5),
                    message=m.group(6),
                    parse_status="parsed",
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
            description="Hadoop Distributed File System logs from Loghub. "
                        "Block-level traces with anomaly labels for detection research.",
            path=f"raw/{self.dataset_name}/{self.file_pattern}",
            format="hdfs",
        )
