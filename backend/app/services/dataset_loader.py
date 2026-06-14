"""
Dataset loader: discovers available datasets on disk and dispatches parsing
to the correct dataset-specific parser and inference service.

Reuses the existing normalizer and summarizer so that dataset-previewed data
arrives at the frontend in the exact same UploadResponse shape as uploaded files.
"""

from pathlib import Path
from typing import Optional

import csv
import logging
import re

from app.core.config import settings
from app.models.schemas import DatasetInfo, DatasetsListResponse, InferenceSummary, LogEntry, UploadResponse
from app.services.normalizer import normalize_entries
from app.services.summarizer import generate_summary
from app.services.dataset_parsers.base_dataset_parser import BaseDatasetParser
from app.services.dataset_parsers.hdfs_parser import HDFSParser
from app.services.dataset_parsers.bgl_parser import BGLParser

logger = logging.getLogger(__name__)

_HDFS_BLOCK_ID_PATTERN = re.compile(r"(blk_-?\d+)")
_HDFS_BLOCK_LABELS: Optional[dict[str, str]] = None

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
    start_line: int = 1,
    model_name: Optional[str] = None,
) -> UploadResponse:
    """Load a dataset file, parse it, normalize, summarize, and run inference.

    Args:
        model_name: Explicit model identifier (e.g. "logbert_hdfs").
                    If None, the dataset's default model is used.
    """
    from app.core.inference_config import resolve_model

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

    entries = parser.parse_file(filepath, max_lines=max_lines, start_line=start_line)
    total_lines = len(entries)
    entries, normalization_info = normalize_entries(entries)

    if dataset_name == "HDFS_v1":
        _apply_hdfs_ground_truth(entries)

    file_label = f"{dataset_name}/{parser.file_pattern}"
    if max_lines is not None:
        range_desc = f"lines {start_line:,}\u2013{start_line + max_lines - 1:,}" if start_line > 1 else f"first {max_lines:,} lines"
        file_label += f" ({range_desc})"

    response = generate_summary(entries, file_label, total_lines, normalization_info)

    resolved = resolve_model(dataset_name, model_name)

    if resolved == "logbert_hdfs":
        response = _run_logbert_hdfs_inference(response)
    elif resolved == "logbert_bgl":
        response = _run_logbert_bgl_inference(response)
    elif dataset_name == "HDFS_v1":
        response = _run_hdfs_inference(response)
    elif dataset_name == "BGL":
        response = _run_bgl_inference(response)

    return response


def _run_hdfs_inference(response: UploadResponse) -> UploadResponse:
    """Run HDFS Transformer Encoder inference on parsed entries."""
    from app.core.inference_config import get_config

    try:
        from app.services.hdfs_inference_service import hdfs_service

        if not hdfs_service.is_available():
            logger.info("HDFS TE inference service not available, skipping")
            return response

        cfg = get_config("transformer_encoder_hdfs")
        entries, analyzed, anomalies = hdfs_service.annotate_entries(response.entries)
        response.entries = entries

        if analyzed > 0:
            response.inference_summary = InferenceSummary(
                model_name=cfg["model_name"],
                entries_analyzed=analyzed,
                anomalies_detected=anomalies,
                status="completed",
                scope=cfg["scope"],
                threshold=cfg["threshold"],
                dataset=cfg["dataset"],
            )
            logger.info(
                "HDFS TE inference: %d entries analyzed, %d anomalies detected",
                analyzed, anomalies,
            )
    except Exception as e:
        logger.error("HDFS TE inference failed: %s", e)

    return response


def _run_logbert_hdfs_inference(response: UploadResponse) -> UploadResponse:
    """Run HDFS LogBERT inference on parsed entries."""
    from app.core.inference_config import get_config

    try:
        from app.services.logbert_inference_service import logbert_hdfs_service

        if not logbert_hdfs_service.is_available():
            logger.info("LogBERT HDFS inference service not available, skipping")
            return response

        cfg = get_config("logbert_hdfs")
        entries, analyzed, anomalies = logbert_hdfs_service.annotate_entries(response.entries)
        response.entries = entries

        if analyzed > 0:
            response.inference_summary = InferenceSummary(
                model_name=cfg["model_name"],
                entries_analyzed=analyzed,
                anomalies_detected=anomalies,
                status="completed",
                scope=cfg["scope"],
                threshold=cfg["threshold"],
                dataset=cfg["dataset"],
            )
            logger.info(
                "LogBERT HDFS inference: %d entries analyzed, %d anomalies detected",
                analyzed, anomalies,
            )
    except Exception as e:
        logger.error("LogBERT HDFS inference failed: %s", e)

    return response


def _run_logbert_bgl_inference(response: UploadResponse) -> UploadResponse:
    """Run BGL LogBERT inference on parsed entries."""
    from app.core.inference_config import get_config

    try:
        from app.services.logbert_bgl_inference_service import logbert_bgl_service

        if not logbert_bgl_service.is_available():
            logger.info("LogBERT BGL inference service not available, skipping")
            return response

        cfg = get_config("logbert_bgl")
        entries, analyzed, anomalies = logbert_bgl_service.annotate_entries(response.entries)
        response.entries = entries

        if analyzed > 0:
            response.inference_summary = InferenceSummary(
                model_name=cfg["model_name"],
                entries_analyzed=analyzed,
                anomalies_detected=anomalies,
                status="completed",
                scope=cfg["scope"],
                threshold=cfg["threshold"],
                dataset=cfg["dataset"],
            )
            logger.info(
                "LogBERT BGL inference: %d entries analyzed, %d anomalies detected",
                analyzed, anomalies,
            )
    except Exception as e:
        logger.error("LogBERT BGL inference failed: %s", e)

    return response


def _run_bgl_inference(response: UploadResponse) -> UploadResponse:
    """Run BGL Transformer Encoder inference on parsed entries."""
    from app.core.inference_config import get_config

    try:
        from app.services.bgl_inference_service import bgl_service

        if not bgl_service.is_available():
            logger.info("BGL inference service not available, skipping")
            return response

        cfg = get_config("transformer_encoder_bgl")
        entries, analyzed, anomalies = bgl_service.annotate_entries(response.entries)
        response.entries = entries

        if analyzed > 0:
            response.inference_summary = InferenceSummary(
                model_name=cfg["model_name"],
                entries_analyzed=analyzed,
                anomalies_detected=anomalies,
                status="completed",
                scope=cfg["scope"],
                threshold=cfg["threshold"],
                dataset=cfg["dataset"],
            )
            logger.info(
                "BGL inference: %d entries analyzed, %d anomalies detected",
                analyzed, anomalies,
            )
    except Exception as e:
        logger.error("BGL inference failed: %s", e)

    return response


def _load_hdfs_block_labels() -> dict[str, str]:
    """Load HDFS block-id -> "anomaly"/"normal" labels from anomaly_label.csv.

    Cached after first read. Returns empty dict if the file is missing.
    """
    global _HDFS_BLOCK_LABELS
    if _HDFS_BLOCK_LABELS is not None:
        return _HDFS_BLOCK_LABELS

    label_path = settings.resolved_datasets_dir / "raw" / "HDFS_v1" / "preprocessed" / "anomaly_label.csv"
    labels: dict[str, str] = {}
    if not label_path.is_file():
        logger.info("HDFS anomaly_label.csv not found at %s; ground truth disabled", label_path)
        _HDFS_BLOCK_LABELS = labels
        return labels

    try:
        with open(label_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                block_id = (row.get("BlockId") or "").strip()
                raw = (row.get("Label") or "").strip().lower()
                if not block_id or not raw:
                    continue
                labels[block_id] = "anomaly" if raw == "anomaly" else "normal"
        logger.info("Loaded %d HDFS block labels for ground truth", len(labels))
    except Exception as e:
        logger.error("Failed to load HDFS block labels: %s", e)

    _HDFS_BLOCK_LABELS = labels
    return labels


def _apply_hdfs_ground_truth(entries: list[LogEntry]) -> None:
    """Tag each HDFS entry with its block-level ground truth label, if known."""
    labels = _load_hdfs_block_labels()
    if not labels:
        return

    for entry in entries:
        text = entry.message or entry.raw_line or ""
        match = _HDFS_BLOCK_ID_PATTERN.search(text)
        if match:
            entry.ground_truth = labels.get(match.group(1))
