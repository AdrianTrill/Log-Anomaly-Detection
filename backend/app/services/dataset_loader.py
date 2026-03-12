"""
Dataset loader: discovers available datasets on disk and dispatches parsing
to the correct dataset-specific parser.

Reuses the existing normalizer and summarizer so that dataset-previewed data
arrives at the frontend in the exact same UploadResponse shape as uploaded files.
"""

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models.schemas import DatasetInfo, DatasetsListResponse, UploadResponse
from app.services.normalizer import normalize_entries
from app.services.summarizer import generate_summary
from app.services.dataset_parsers.base_dataset_parser import BaseDatasetParser
from app.services.dataset_parsers.hdfs_parser import HDFSParser
from app.services.dataset_parsers.bgl_parser import BGLParser

# Maps dataset directory names (under datasets/raw/) to parser instances.
# To add a new dataset, create a parser class and register it here.
DATASET_REGISTRY: dict[str, BaseDatasetParser] = {
    "HDFS_v1": HDFSParser(),
    "BGL": BGLParser(),
}


def list_datasets() -> DatasetsListResponse:
    """Scan the datasets/raw/ directory and return info for each registered dataset found on disk."""
    datasets_dir = settings.resolved_datasets_dir
    raw_dir = datasets_dir / "raw"
    found: list[DatasetInfo] = []

    for name, parser in DATASET_REGISTRY.items():
        dataset_dir = raw_dir / name
        log_file = dataset_dir / parser.file_pattern
        if dataset_dir.is_dir() and log_file.is_file():
            info = parser.dataset_info()
            info.path = str(log_file.relative_to(datasets_dir))
            found.append(info)

    return DatasetsListResponse(
        datasets_dir=str(datasets_dir),
        datasets=found,
    )


def load_and_parse(
    dataset_name: str,
    max_lines: Optional[int] = None,
) -> UploadResponse:
    """Load a dataset file, parse it, normalize, and summarize into UploadResponse."""
    parser = DATASET_REGISTRY.get(dataset_name)
    if parser is None:
        available = list(DATASET_REGISTRY.keys())
        raise ValueError(f"Unknown dataset '{dataset_name}'. Available: {available}")

    datasets_dir = settings.resolved_datasets_dir
    filepath = datasets_dir / "raw" / dataset_name / parser.file_pattern

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Dataset file not found: {filepath}. "
            f"Place {parser.file_pattern} in datasets/raw/{dataset_name}/"
        )

    entries = parser.parse_file(filepath, max_lines=max_lines)
    total_lines = len(entries)
    entries, normalization_info = normalize_entries(entries)

    file_label = f"{dataset_name}/{parser.file_pattern}"
    if max_lines is not None:
        file_label += f" (first {max_lines} lines)"

    return generate_summary(entries, file_label, total_lines, normalization_info)
