"""
Centralized inference configuration for benchmark dataset models.

Configs are keyed by model identifier (e.g. "transformer_encoder_hdfs",
"logbert_hdfs") rather than dataset name, so multiple models can serve
the same dataset.

Thresholds are deployment/inference settings, not part of model weights.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import _PROJECT_ROOT

INFERENCE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "transformer_encoder_hdfs": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "checkpoints" / "fourth_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "metadata.json",
        "traces": _PROJECT_ROOT / "datasets" / "raw" / "HDFS_v1" / "preprocessed" / "Event_traces.csv",
        "threshold": 0.5,
        "model_name": "transformer_encoder_hdfs",
        "scope": "hdfs_block_session",
        "dataset": "HDFS_v1",
        "model_class": "transformer_encoder",
    },
    "transformer_encoder_bgl": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "checkpoints" / "fourth_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "metadata.json",
        "threshold": 0.8,
        "model_name": "transformer_encoder_bgl",
        "scope": "bgl_sliding_window",
        "dataset": "BGL",
        "model_class": "transformer_encoder",
    },
    "logbert_hdfs": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs_logbert" / "checkpoints" / "third_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "hdfs" / "metadata.json",
        "traces": _PROJECT_ROOT / "datasets" / "raw" / "HDFS_v1" / "preprocessed" / "Event_traces.csv",
        "threshold": 0.5,
        "model_name": "logbert_hdfs",
        "scope": "hdfs_block_session",
        "dataset": "HDFS_v1",
        "model_class": "logbert",
    },
    "logbert_bgl": {
        "checkpoint": _PROJECT_ROOT / "ml" / "artifacts" / "bgl_logbert" / "checkpoints" / "second_run-BEST" / "best_model.pt",
        "vocab": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "template_vocab.json",
        "metadata": _PROJECT_ROOT / "ml" / "artifacts" / "bgl" / "metadata.json",
        "threshold": 0.8,
        "model_name": "logbert_bgl",
        "scope": "bgl_sliding_window",
        "dataset": "BGL",
        "model_class": "logbert",
    },
}

DATASET_MODELS: Dict[str, List[str]] = {
    "HDFS_v1": ["transformer_encoder_hdfs", "logbert_hdfs"],
    "BGL": ["transformer_encoder_bgl", "logbert_bgl"],
}

DEFAULT_MODEL: Dict[str, str] = {
    "HDFS_v1": "transformer_encoder_hdfs",
    "BGL": "transformer_encoder_bgl",
}


def get_config(model_name: str) -> Dict[str, Any]:
    """Get inference config by model identifier. Raises KeyError if not configured."""
    return INFERENCE_CONFIGS[model_name]


def get_models_for_dataset(dataset_name: str) -> List[str]:
    """Return the list of model identifiers available for a dataset."""
    return DATASET_MODELS.get(dataset_name, [])


def get_default_model(dataset_name: str) -> str:
    """Return the default model identifier for a dataset. Raises KeyError if unknown."""
    return DEFAULT_MODEL[dataset_name]


def resolve_model(dataset_name: str, model_name: Optional[str] = None) -> str:
    """Resolve an explicit or default model for a dataset.

    If model_name is provided and valid for the dataset, returns it.
    Otherwise returns the dataset's default model.
    """
    if model_name and model_name in get_models_for_dataset(dataset_name):
        return model_name
    return get_default_model(dataset_name)
