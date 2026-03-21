"""
BGL Transformer Encoder inference service.

Loads the trained BGL checkpoint and template vocabulary, then provides
sliding-window anomaly inference for BGL log entries.

The model predicts per sliding window of consecutive log lines. All log
lines within the same window share one anomaly score and prediction.
Lines that don't fill a complete window get inference_status = "not_run".

BGL normalization uses the same regex patterns as the preprocessing
pipeline (ml/preprocessing/preprocess_bgl.py) to ensure template
vocabulary alignment.
"""

import json
import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.models.schemas import LogEntry

logger = logging.getLogger(__name__)

# Same normalization patterns as ml/preprocessing/preprocess_bgl.py
HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b")
PATH_PATTERN = re.compile(r"(?<!\w)/[a-zA-Z0-9_./-]{3,}")
NUM_PATTERN = re.compile(r"\b\d+\b")


def _normalize_bgl_message(msg: str) -> str:
    """Mask variable tokens — same order as preprocessing pipeline."""
    out = msg.strip()
    out = HEX_PATTERN.sub("<HEX>", out)
    out = IP_PATTERN.sub("<IP>", out)
    out = PATH_PATTERN.sub("<PATH>", out)
    out = NUM_PATTERN.sub("<NUM>", out)
    return out


class WindowResult:
    __slots__ = ("score", "prediction")

    def __init__(self, score: float, prediction: str):
        self.score = score
        self.prediction = prediction


class BglInferenceService:
    """
    Lazy-loading inference service for BGL log anomaly detection.

    Loads the Transformer Encoder checkpoint and template vocabulary on
    first use.  Inference normalizes entry messages on the fly, maps them
    to template IDs, groups into sliding windows, and runs the model.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        vocab_path: Path,
        metadata_path: Path,
        threshold: float,
        model_name: str,
        project_root: Path,
    ):
        self._checkpoint_path = checkpoint_path
        self._vocab_path = vocab_path
        self._metadata_path = metadata_path
        self._threshold = threshold
        self._model_name = model_name
        self._project_root = project_root

        self._model = None
        self._msg_to_id: Dict[str, int] = {}
        self._unk_id: int = 0
        self._pad_id: int = 0
        self._window_size: int = 50
        self._step_size: int = 50
        self._loaded = False
        self._load_error: Optional[str] = None

    def is_available(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        for p in [self._checkpoint_path, self._vocab_path, self._metadata_path]:
            if not p.exists():
                return False
        return True

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._load_error:
            return
        try:
            self._load_all()
            self._loaded = True
            logger.info("BGL inference service loaded successfully")
        except Exception as e:
            self._load_error = str(e)
            logger.error("Failed to load BGL inference service: %s", e)

    def _load_all(self) -> None:
        import torch

        ml_root = str(self._project_root)
        if ml_root not in sys.path:
            sys.path.insert(0, ml_root)

        from ml.models.transformer_encoder import LogAnomalyTransformer

        with open(self._vocab_path) as f:
            vocab_data = json.load(f)

        self._pad_id = vocab_data.get("pad_id", 0)
        self._unk_id = vocab_data.get("unk_id", 0)

        # Build reverse lookup: normalized message string -> integer ID
        templates = vocab_data.get("templates", {})
        token_to_id = vocab_data["token_to_id"]
        self._msg_to_id = {
            msg: token_to_id[tid] for tid, msg in templates.items()
        }

        with open(self._metadata_path) as f:
            metadata = json.load(f)
        cfg_meta = metadata["config"]
        self._window_size = cfg_meta.get("window_size", cfg_meta["max_seq_len"])
        self._step_size = cfg_meta.get("step_size", self._window_size)

        device = torch.device("cpu")
        ckpt = torch.load(self._checkpoint_path, map_location=device, weights_only=False)
        cfg = ckpt["config"]
        meta = ckpt["metadata"]

        model = LogAnomalyTransformer(
            vocab_size=meta["vocab_size"],
            d_model=cfg["d_model"],
            nhead=cfg["nhead"],
            num_layers=cfg["num_layers"],
            dim_feedforward=cfg["dim_feedforward"],
            max_seq_len=meta["max_seq_len"],
            dropout=0.0,
            pad_id=meta["pad_id"],
        )
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        self._model = model
        self._device = device

        logger.info(
            "BGL model loaded: epoch=%d, val_f1=%.4f, params=%d, threshold=%.2f, window=%d, step=%d",
            ckpt["epoch"],
            ckpt["best_f1"],
            sum(p.numel() for p in model.parameters()),
            self._threshold,
            self._window_size,
            self._step_size,
        )

    def _normalize_and_map(self, entries: List[LogEntry]) -> List[int]:
        """Normalize each entry's message and look up its template ID."""
        ids: List[int] = []
        for entry in entries:
            msg = entry.message or entry.raw_line
            normalized = _normalize_bgl_message(msg)
            tid = self._msg_to_id.get(normalized, self._unk_id)
            ids.append(tid)
        return ids

    def _build_windows(self, template_ids: List[int]) -> Tuple[List[List[int]], List[int]]:
        """Build sliding windows using window_size and step_size from metadata.

        Returns (windows, start_indices) so the caller knows each window's
        position in the original entry list.
        """
        windows: List[List[int]] = []
        starts: List[int] = []
        n = len(template_ids)
        for start in range(0, n - self._window_size + 1, self._step_size):
            windows.append(template_ids[start:start + self._window_size])
            starts.append(start)
        return windows, starts

    def _infer_windows(self, windows: List[List[int]]) -> List[WindowResult]:
        """Run model inference on encoded windows."""
        import torch

        encoded = np.array(windows, dtype=np.int64)
        tensor = torch.from_numpy(encoded).long().to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.sigmoid(logits).cpu().numpy()

        results: List[WindowResult] = []
        for prob in probs:
            score = float(prob)
            prediction = "anomaly" if score >= self._threshold else "normal"
            results.append(WindowResult(score=score, prediction=prediction))
        return results

    def annotate_entries(self, entries: List[LogEntry]) -> Tuple[List[LogEntry], int, int]:
        """
        Annotate log entries with anomaly predictions using sliding windows.

        Window boundaries are derived from window_size and step_size in
        the BGL metadata, so inference stays aligned with preprocessing.
        When windows overlap (step_size < window_size), entries covered by
        multiple windows receive the highest (most anomalous) score.

        Returns:
            (annotated_entries, entries_analyzed, anomalies_detected)
        """
        self._ensure_loaded()
        if not self._loaded:
            return entries, 0, 0

        template_ids = self._normalize_and_map(entries)
        windows, starts = self._build_windows(template_ids)

        if not windows:
            return entries, 0, 0

        results = self._infer_windows(windows)

        # Map window results back to entries.
        # For overlapping windows, keep the highest score per entry.
        entry_scores: List[Optional[float]] = [None] * len(entries)
        entry_preds: List[Optional[str]] = [None] * len(entries)

        for win_start, result in zip(starts, results):
            for idx in range(win_start, win_start + self._window_size):
                prev = entry_scores[idx]
                if prev is None or result.score > prev:
                    entry_scores[idx] = result.score
                    entry_preds[idx] = result.prediction

        analyzed = 0
        anomalies = 0
        for i, entry in enumerate(entries):
            if entry_scores[i] is not None:
                entry.anomaly_score = round(entry_scores[i], 6)
                entry.prediction = entry_preds[i]
                entry.model_name = self._model_name
                entry.inference_status = "completed"
                analyzed += 1
                if entry_preds[i] == "anomaly":
                    anomalies += 1
            else:
                entry.model_name = self._model_name
                entry.inference_status = "not_run"

        return entries, analyzed, anomalies


def _create_service() -> BglInferenceService:
    from app.core.config import _PROJECT_ROOT
    from app.core.inference_config import get_config

    cfg = get_config("BGL")
    return BglInferenceService(
        checkpoint_path=cfg["checkpoint"],
        vocab_path=cfg["vocab"],
        metadata_path=cfg["metadata"],
        threshold=cfg["threshold"],
        model_name=cfg["model_name"],
        project_root=_PROJECT_ROOT,
    )


bgl_service = _create_service()
