"""
Abstract base class for dataset-specific log parsers.

Every research dataset (HDFS, BGL, etc.) has a unique line format. Concrete
parsers implement parse_file() to handle that format while producing the same
LogEntry schema the rest of the pipeline (normalizer, summarizer, frontend)
already expects.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.models.schemas import LogEntry, DatasetInfo


class BaseDatasetParser(ABC):
    dataset_name: str = ""
    file_pattern: str = ""

    @abstractmethod
    def parse_file(
        self, filepath: Path, max_lines: Optional[int] = None, start_line: int = 1,
    ) -> list[LogEntry]:
        """Parse a dataset log file into a list of LogEntry objects.
        start_line is 1-based; max_lines caps how many lines are read from that offset."""
        ...

    @abstractmethod
    def dataset_info(self) -> DatasetInfo:
        """Return metadata about this dataset for the /api/datasets listing."""
        ...

    def _read_lines(
        self, filepath: Path, max_lines: Optional[int] = None, start_line: int = 1,
    ) -> list[str]:
        """Read lines from a file with optional offset and cap."""
        lines: list[str] = []
        skip = max(0, start_line - 1)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < skip:
                    continue
                if max_lines is not None and len(lines) >= max_lines:
                    break
                lines.append(line)
        return lines
