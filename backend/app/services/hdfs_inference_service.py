"""
HDFS Transformer Encoder inference service.

Loads the trained checkpoint, template vocabulary, and benchmark event traces,
then provides block-level anomaly inference for HDFS log entries.

The model predicts per block/session (e.g. blk_-1608999687919862906). All log
lines belonging to the same block receive the same anomaly score and prediction.
"""

import json
import re
import sys
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.models.schemas import LogEntry

logger = logging.getLogger(__name__)

BLOCK_ID_PATTERN = re.compile(r"(blk_-?\d+)")

MODEL_NAME = "transformer_encoder"


class BlockResult:
    __slots__ = ("score", "prediction")

    def __init__(self, score: float, prediction: str):
        self.score = score
        self.prediction = prediction


class HdfsInferenceService:
    """
    Lazy-loading inference service for HDFS log anomaly detection.

    Loads the Transformer Encoder checkpoint, template vocabulary, and
    Event_traces.csv lookup table on first use, then caches everything
    for subsequent requests.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        vocab_path: Path,
        traces_path: Path,
        metadata_path: Path,
        project_root: Path,
    ):
        self._checkpoint_path = checkpoint_path
        self._vocab_path = vocab_path
        self._traces_path = traces_path
        self._metadata_path = metadata_path
        self._project_root = project_root

        self._model = None
        self._token_to_id: Dict[str, int] = {}
        self._traces: Dict[str, List[str]] = {}
        self._max_seq_len: int = 50
        self._pad_id: int = 0
        self._unk_id: int = 30
        self._loaded = False
        self._load_error: Optional[str] = None

    def is_available(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        for p in [self._checkpoint_path, self._vocab_path, self._traces_path]:
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
            logger.info("HDFS inference service loaded successfully")
        except Exception as e:
            self._load_error = str(e)
            logger.error("Failed to load HDFS inference service: %s", e)

    def _load_all(self) -> None:
        import torch

        ml_root = str(self._project_root)
        if ml_root not in sys.path:
            sys.path.insert(0, ml_root)

        from ml.models.transformer_encoder import LogAnomalyTransformer

        with open(self._vocab_path) as f:
            vocab_data = json.load(f)
        self._token_to_id = vocab_data["token_to_id"]
        self._pad_id = vocab_data.get("pad_id", 0)
        self._unk_id = vocab_data.get("unk_id", 30)

        with open(self._metadata_path) as f:
            metadata = json.load(f)
        self._max_seq_len = metadata["config"]["max_seq_len"]

        self._traces = self._load_traces()
        logger.info("Loaded %d block event traces", len(self._traces))

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
            "Model loaded: epoch=%d, val_f1=%.4f, params=%d",
            ckpt["epoch"],
            ckpt["best_f1"],
            sum(p.numel() for p in model.parameters()),
        )

    def _load_traces(self) -> Dict[str, List[str]]:
        traces: Dict[str, List[str]] = {}
        with open(self._traces_path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            features_idx = header.index("Features")
            block_idx = header.index("BlockId")
            for row in reader:
                block_id = row[block_idx]
                raw_features = row[features_idx].strip("[] ")
                if raw_features:
                    events = [t.strip() for t in raw_features.split(",") if t.strip()]
                else:
                    events = []
                traces[block_id] = events
        return traces

    def _encode_sequences(self, sessions: List[List[str]]) -> np.ndarray:
        encoded = np.full((len(sessions), self._max_seq_len), self._pad_id, dtype=np.int64)
        for i, events in enumerate(sessions):
            for j, event in enumerate(events[: self._max_seq_len]):
                encoded[i, j] = int(self._token_to_id.get(event, self._unk_id))
        return encoded

    def infer_blocks(self, block_ids: List[str]) -> Dict[str, BlockResult]:
        """Run inference on a list of block IDs. Returns {block_id: BlockResult}."""
        import torch

        self._ensure_loaded()
        if not self._loaded:
            return {}

        unique_ids = list(dict.fromkeys(block_ids))
        valid_ids = [bid for bid in unique_ids if bid in self._traces]

        if not valid_ids:
            return {}

        sessions = [self._traces[bid] for bid in valid_ids]
        encoded = self._encode_sequences(sessions)
        tensor = torch.from_numpy(encoded).long().to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.sigmoid(logits).cpu().numpy()

        results: Dict[str, BlockResult] = {}
        for bid, prob in zip(valid_ids, probs):
            score = float(prob)
            prediction = "anomaly" if score >= 0.5 else "normal"
            results[bid] = BlockResult(score=score, prediction=prediction)

        return results

    def annotate_entries(self, entries: List[LogEntry]) -> Tuple[List[LogEntry], int, int]:
        """
        Annotate log entries with anomaly predictions based on their block ID.

        Returns:
            (annotated_entries, entries_analyzed, anomalies_detected)
        """
        self._ensure_loaded()
        if not self._loaded:
            return entries, 0, 0

        entry_blocks: List[Optional[str]] = []
        block_set: List[str] = []
        for entry in entries:
            bid = self._extract_block_id(entry)
            entry_blocks.append(bid)
            if bid and bid not in block_set:
                block_set.append(bid)

        if not block_set:
            return entries, 0, 0

        results = self.infer_blocks(block_set)

        analyzed = 0
        anomalies = 0
        for entry, bid in zip(entries, entry_blocks):
            if bid and bid in results:
                r = results[bid]
                entry.anomaly_score = round(r.score, 6)
                entry.prediction = r.prediction
                entry.model_name = MODEL_NAME
                entry.inference_status = "completed"
                analyzed += 1
                if r.prediction == "anomaly":
                    anomalies += 1
            elif bid:
                entry.model_name = MODEL_NAME
                entry.inference_status = "not_available"
            # entries with no block ID keep default "not_run"

        return entries, analyzed, anomalies

    @staticmethod
    def _extract_block_id(entry: LogEntry) -> Optional[str]:
        text = entry.message or entry.raw_line
        match = BLOCK_ID_PATTERN.search(text)
        return match.group(1) if match else None


def _create_service() -> HdfsInferenceService:
    from app.core.config import _PROJECT_ROOT

    artifacts_dir = _PROJECT_ROOT / "ml" / "artifacts" / "hdfs"
    traces_path = (
        _PROJECT_ROOT / "datasets" / "raw" / "HDFS_v1" / "preprocessed" / "Event_traces.csv"
    )

    return HdfsInferenceService(
        checkpoint_path=artifacts_dir / "checkpoints" / "fourth_run" / "best_model.pt",
        vocab_path=artifacts_dir / "template_vocab.json",
        traces_path=traces_path,
        metadata_path=artifacts_dir / "metadata.json",
        project_root=_PROJECT_ROOT,
    )


hdfs_service = _create_service()
