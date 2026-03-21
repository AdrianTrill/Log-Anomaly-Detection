"""
Centralized inference configuration for benchmark dataset models.

Thresholds are deployment/inference settings, not part of model weights.
Each dataset uses its own checkpoint, vocabulary, and decision threshold.
"""

from pathlib import Path
from typing import Dict, Any

from app.core.config import _PROJECT_ROOT

INFERENCE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "HDFS_v1": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "checkpoints" / "fourth_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "metadata.json",
        "traces": _PROJECT_ROOT / "datasets" / "raw" / "HDFS_v1" / "preprocessed" / "Event_traces.csv",
        "threshold": 0.5,
        "model_name": "transformer_encoder_hdfs",
        "scope": "hdfs_block_session",
    },
    "BGL": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "checkpoints" / "fourth_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "metadata.json",
        "threshold": 0.8,
        "model_name": "transformer_encoder_bgl",
        "scope": "bgl_sliding_window",
    },
}


def get_config(dataset_name: str) -> Dict[str, Any]:
    """Get inference config for a dataset. Raises KeyError if not configured."""
    return INFERENCE_CONFIGS[dataset_name]
