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
    def parse_file(self, filepath: Path, max_lines: Optional[int] = None) -> list[LogEntry]:
        """Parse a dataset log file into a list of LogEntry objects.
        max_lines caps how many lines are read (critical for multi-million-line files)."""
        ...

    @abstractmethod
    def dataset_info(self) -> DatasetInfo:
        """Return metadata about this dataset for the /api/datasets listing."""
        ...

    def _read_lines(self, filepath: Path, max_lines: Optional[int] = None) -> list[str]:
        """Read lines from a file with optional cap. Uses errors='replace' for robustness."""
        lines: list[str] = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if max_lines is not None and i >= max_lines:
                    break
                lines.append(line)
        return lines
