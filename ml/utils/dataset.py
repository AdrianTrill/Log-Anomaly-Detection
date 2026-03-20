"""
PyTorch dataset utilities for loading preprocessed log-sequence artifacts.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union

import numpy as np
import torch
from torch.utils.data import Dataset


class LogSequenceDataset(Dataset):
    """Wraps numpy sequence/label arrays as a PyTorch Dataset."""

    def __init__(self, sequences: np.ndarray, labels: np.ndarray):
        assert len(sequences) == len(labels), (
            f"Sequence/label length mismatch: {len(sequences)} vs {len(labels)}"
        )
        self.sequences = torch.from_numpy(sequences).long()
        self.labels = torch.from_numpy(labels).float()

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        return self.sequences[idx], self.labels[idx]


def load_split(artifacts_dir: Union[str, Path], split: str) -> LogSequenceDataset:
    """
    Load a train/val/test split from .npy files.

    Args:
        artifacts_dir: path to the artifacts folder (e.g. ml/artifacts/hdfs)
        split: one of "train", "val", "test"
    """
    d = Path(artifacts_dir)
    sequences = np.load(d / f"{split}_sequences.npy")
    labels = np.load(d / f"{split}_labels.npy")
    return LogSequenceDataset(sequences, labels)


def load_metadata(artifacts_dir: Union[str, Path]) -> Dict[str, Any]:
    """Load metadata.json from the artifacts directory."""
    with open(Path(artifacts_dir) / "metadata.json") as f:
        return json.load(f)
