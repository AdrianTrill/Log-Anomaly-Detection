"""
Sequence builder for the HDFS preprocessing pipeline.

Loads pre-extracted event traces and anomaly labels from the Loghub HDFS
benchmark files, aligns them by BlockId, encodes event sequences as
padded integer arrays, and produces stratified train/val/test splits.

The Event_traces.csv Features column contains session-level event sequences
already extracted by the Drain log parser (e.g. "[E5,E22,E5,E11,...]").
Using these benchmark-aligned traces ensures reproducibility and consistency
with published results on HDFS anomaly detection.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.model_selection import train_test_split


def load_traces(event_traces_path: Path) -> Dict[str, List[str]]:
    """
    Parse Event_traces.csv and extract per-session event sequences.

    Returns:
        dict mapping BlockId -> list of event IDs, e.g.
        {"blk_123": ["E5", "E22", "E5", ...], ...}
    """
    traces: Dict[str, List[str]] = {}
    with open(event_traces_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        features_idx = header.index("Features")
        block_idx = header.index("BlockId")

        for row in reader:
            block_id = row[block_idx]
            raw_features = row[features_idx]
            events = _parse_features_string(raw_features)
            traces[block_id] = events

    return traces


def _parse_features_string(raw: str) -> List[str]:
    """Parse '[E5,E22,E5,E11,E9]' into ['E5', 'E22', 'E5', 'E11', 'E9']."""
    inner = raw.strip("[] ")
    if not inner:
        return []
    return [tok.strip() for tok in inner.split(",") if tok.strip()]


def load_labels(anomaly_label_path: Path) -> Dict[str, int]:
    """
    Parse anomaly_label.csv into a BlockId -> binary label mapping.

    Returns:
        {"blk_123": 0, "blk_456": 1, ...}   (0 = Normal, 1 = Anomaly)
    """
    labels: Dict[str, int] = {}
    with open(anomaly_label_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            block_id = row["BlockId"]
            label_str = row["Label"]
            labels[block_id] = 1 if label_str == "Anomaly" else 0
    return labels


def align_and_verify(
    traces: Dict[str, List[str]],
    labels: Dict[str, int],
) -> Tuple[List[str], List[List[str]], List[int]]:
    """
    Align traces and labels by BlockId and verify consistency.

    Returns:
        block_ids:  ordered list of block IDs
        sequences:  matching event sequences
        targets:    matching binary labels
    """
    trace_keys = set(traces.keys())
    label_keys = set(labels.keys())

    common = trace_keys & label_keys
    only_traces = trace_keys - label_keys
    only_labels = label_keys - trace_keys

    print(f"  Blocks in Event_traces: {len(trace_keys):,}")
    print(f"  Blocks in anomaly_label: {len(label_keys):,}")
    print(f"  Common blocks:           {len(common):,}")
    if only_traces:
        print(f"  WARNING: {len(only_traces)} blocks only in traces (dropped)")
    if only_labels:
        print(f"  WARNING: {len(only_labels)} blocks only in labels (dropped)")

    block_ids = sorted(common)
    sequences = [traces[bid] for bid in block_ids]
    targets = [labels[bid] for bid in block_ids]

    assert len(sequences) == len(targets), (
        f"Sequence/label count mismatch: {len(sequences)} vs {len(targets)}"
    )
    assert len(sequences) > 0, "No aligned sessions found"

    return block_ids, sequences, targets


def encode_sequences(
    sessions: List[List[str]],
    token_to_id: Dict[str, int],
    max_seq_len: int,
    pad_id: int = 0,
) -> np.ndarray:
    """
    Convert event-ID string sequences to padded integer arrays.

    Sequences shorter than max_seq_len are right-padded with pad_id.
    Sequences longer than max_seq_len are truncated from the right.
    Unknown event IDs are mapped to UNK.
    """
    unk_id = token_to_id.get("UNK", pad_id)
    encoded = np.full((len(sessions), max_seq_len), pad_id, dtype=np.int32)

    unk_count = 0
    for i, events in enumerate(sessions):
        for j, event in enumerate(events[:max_seq_len]):
            token_id = token_to_id.get(event, unk_id)
            if token_id == unk_id and event != "UNK":
                unk_count += 1
            encoded[i, j] = token_id

    if unk_count > 0:
        print(f"  WARNING: {unk_count} event tokens mapped to UNK")

    return encoded


def stratified_split(
    sequences: np.ndarray,
    labels: np.ndarray,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[
    np.ndarray, np.ndarray,
    np.ndarray, np.ndarray,
    np.ndarray, np.ndarray,
]:
    """
    Perform stratified train/val/test split preserving class distribution.

    Returns:
        (train_seq, train_lbl, val_seq, val_lbl, test_seq, test_lbl)
    """
    holdout_ratio = val_ratio + test_ratio
    train_seq, holdout_seq, train_lbl, holdout_lbl = train_test_split(
        sequences, labels,
        test_size=holdout_ratio,
        random_state=seed,
        stratify=labels,
    )

    relative_test = test_ratio / holdout_ratio
    val_seq, test_seq, val_lbl, test_lbl = train_test_split(
        holdout_seq, holdout_lbl,
        test_size=relative_test,
        random_state=seed,
        stratify=holdout_lbl,
    )

    return train_seq, train_lbl, val_seq, val_lbl, test_seq, test_lbl
