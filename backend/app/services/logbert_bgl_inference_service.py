"""
BGL LogBERT inference service.

Loads the trained BGL LogBERT checkpoint and template vocabulary, then provides
sliding-window anomaly inference for BGL log entries.

Uses the same BGL sliding-window prediction granularity as the Transformer
Encoder service: all log lines within the same window share one anomaly score
and prediction.  The only model-level difference is that LogBERT uses
forward_cls() (CLS-based pooling) instead of the Transformer Encoder's
mean-pool forward().
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.models.schemas import LogEntry
from app.services.bgl_inference_service import _normalize_bgl_message, WindowResult

logger = logging.getLogger(__name__)


class LogbertBglInferenceService:
    """
    Lazy-loading inference service for BGL LogBERT anomaly detection.

    Loads the LogBERT fine-tuned checkpoint and BGL template vocabulary
    on first use, then caches everything for subsequent requests.
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
            logger.info("BGL LogBERT inference service loaded successfully")
        except Exception as e:
            self._load_error = str(e)
            logger.error("Failed to load BGL LogBERT inference service: %s", e)

    def _load_all(self) -> None:
        import torch

        ml_root = str(self._project_root)
        if ml_root not in sys.path:
            sys.path.insert(0, ml_root)

        from ml.models.logbert import LogBERT

        with open(self._vocab_path) as f:
            vocab_data = json.load(f)

        self._pad_id = vocab_data.get("pad_id", 0)
        self._unk_id = vocab_data.get("unk_id", 0)

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

        model = LogBERT(
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
            "BGL LogBERT loaded: epoch=%d, val_f1=%.4f, params=%d, threshold=%.2f, window=%d, step=%d",
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
        """Build sliding windows from template IDs."""
        windows: List[List[int]] = []
        starts: List[int] = []
        n = len(template_ids)
        for start in range(0, n - self._window_size + 1, self._step_size):
            windows.append(template_ids[start:start + self._window_size])
            starts.append(start)
        return windows, starts

    def _infer_windows(self, windows: List[List[int]]) -> List[WindowResult]:
        """Run LogBERT classification inference on encoded windows."""
        import torch

        encoded = np.array(windows, dtype=np.int64)
        tensor = torch.from_numpy(encoded).long().to(self._device)

        with torch.no_grad():
            logits = self._model.forward_cls(tensor)
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


def _create_service() -> LogbertBglInferenceService:
    from app.core.config import _PROJECT_ROOT
    from app.core.inference_config import get_config

    cfg = get_config("logbert_bgl")
    return LogbertBglInferenceService(
        checkpoint_path=cfg["checkpoint"],
        vocab_path=cfg["vocab"],
        metadata_path=cfg["metadata"],
        threshold=cfg["threshold"],
        model_name=cfg["model_name"],
        project_root=_PROJECT_ROOT,
    )


logbert_bgl_service = _create_service()
