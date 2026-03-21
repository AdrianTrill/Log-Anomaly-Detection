"""
BGL preprocessing pipeline for Transformer-based log anomaly detection.

Produces training-ready artifacts from the raw BGL.log file (BlueGene/L
supercomputer logs from LLNL, ~4.75M lines).

Unlike the HDFS pipeline which uses Loghub-provided preprocessed CSVs,
BGL preprocessing works entirely from the raw log:

  Pass 1 — Stream + normalize + count
    Parses each line, normalizes the message with aggressive regex
    substitutions, and accumulates a frequency counter over unique
    normalized messages.  Only a Counter dict is held in memory.
    At the end, the top-K templates form the vocabulary.

  Pass 2 — Stream + map IDs + sliding windows
    Re-streams the log with the finalized vocabulary.  Each line's
    normalized message is looked up in the vocab to get a template ID.
    A rolling window buffer accumulates (template_id, is_anomaly)
    tuples and emits fixed-size sequences with window-level labels.

This two-pass design avoids holding 4.75M Python string objects in
memory simultaneously.

BGL line format (space-delimited, 9 fixed tokens + message):
  [0] label      — "-" for normal, alert category string for anomalous
  [1] unix_ts    — unix epoch seconds
  [2] date       — YYYY.MM.DD
  [3] node       — hardware location identifier
  [4] precise_ts — YYYY-MM-DD-HH.MM.SS.microseconds
  [5] node       — repeated
  [6] category   — e.g. RAS
  [7] component  — e.g. KERNEL, APP
  [8] level      — INFO, WARN, ERROR, FATAL, etc.
  [9+] message   — free-form text

Usage:
    python3 -m ml.preprocessing.preprocess_bgl
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ml.preprocessing.template_builder import save_vocab, PAD_TOKEN, UNK_TOKEN
from ml.preprocessing.sequence_builder import stratified_split


# ---------------------------------------------------------------------------
# BGL-specific normalization
# ---------------------------------------------------------------------------
# More aggressive than the backend normalizer: BGL messages contain many
# variable numeric fields (addresses, counters, core IDs, etc.) that must
# be masked to produce meaningful templates.

HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b")
PATH_PATTERN = re.compile(r"(?<!\w)/[a-zA-Z0-9_./-]{3,}")
NUM_PATTERN = re.compile(r"\b\d+\b")

KNOWN_LEVELS = frozenset({
    "INFO", "WARN", "WARNING", "ERROR", "FATAL",
    "CRITICAL", "DEBUG", "TRACE", "SEVERE", "FAILURE",
})


def _normalize_bgl_message(msg: str) -> str:
    """Mask variable tokens in a BGL log message for template extraction."""
    out = msg.strip()
    out = HEX_PATTERN.sub("<HEX>", out)
    out = IP_PATTERN.sub("<IP>", out)
    out = PATH_PATTERN.sub("<PATH>", out)
    out = NUM_PATTERN.sub("<NUM>", out)
    return out


def _parse_bgl_line(line: str) -> Optional[Tuple[bool, str]]:
    """
    Parse a single BGL log line.

    Returns:
        (is_anomaly, message) or None if the line is unparseable.
    """
    stripped = line.strip()
    if not stripped:
        return None

    tokens = stripped.split(None, 9)
    if len(tokens) < 10:
        return None

    label_token = tokens[0]
    level = tokens[8].upper()

    if level not in KNOWN_LEVELS:
        return None

    is_anomaly = label_token != "-"
    message = tokens[9]
    return is_anomaly, message


# ---------------------------------------------------------------------------
# Pass 1: Streaming frequency count
# ---------------------------------------------------------------------------

def pass1_count_templates(
    log_path: Path,
    max_lines: Optional[int] = None,
) -> Tuple[Counter, int, int, int]:
    """
    Stream BGL.log and count normalized-message frequencies.

    Returns:
        (template_counter, total_lines, parsed_lines, anomaly_lines)
    """
    counter: Counter = Counter()
    total = 0
    parsed = 0
    anomalies = 0

    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            if max_lines and total > max_lines:
                total -= 1
                break

            result = _parse_bgl_line(line)
            if result is None:
                continue

            is_anomaly, message = result
            parsed += 1
            if is_anomaly:
                anomalies += 1

            normalized = _normalize_bgl_message(message)
            counter[normalized] += 1

    return counter, total, parsed, anomalies


# ---------------------------------------------------------------------------
# Vocabulary construction from frequency counter
# ---------------------------------------------------------------------------

def build_vocab_from_counter(
    counter: Counter,
    max_templates: int,
) -> Tuple[Dict[str, int], Dict[int, str], Dict[str, str]]:
    """
    Build a template vocabulary from the frequency counter.

    Templates are named T1..TN sorted by descending frequency.
    Vocabulary: PAD=0, T1=1, ..., TN=N, UNK=N+1.

    Returns:
        (token_to_id, id_to_token, templates)
        where templates maps "T1" -> normalized message string.
    """
    most_common = counter.most_common(max_templates)

    token_to_id: Dict[str, int] = {PAD_TOKEN: 0}
    templates: Dict[str, str] = {}

    for idx, (normalized_msg, _count) in enumerate(most_common, start=1):
        tid = f"T{idx}"
        token_to_id[tid] = idx
        templates[tid] = normalized_msg

    unk_id = len(token_to_id)
    token_to_id[UNK_TOKEN] = unk_id

    id_to_token = {v: k for k, v in token_to_id.items()}

    return token_to_id, id_to_token, templates


def _build_message_to_tid(
    templates: Dict[str, str],
    token_to_id: Dict[str, int],
) -> Dict[str, int]:
    """Build a reverse lookup: normalized message -> integer template ID."""
    return {msg: token_to_id[tid] for tid, msg in templates.items()}


# ---------------------------------------------------------------------------
# Pass 2: Streaming window construction
# ---------------------------------------------------------------------------

def pass2_build_windows(
    log_path: Path,
    msg_to_id: Dict[str, int],
    unk_id: int,
    window_size: int,
    step_size: int,
    max_lines: Optional[int] = None,
) -> Tuple[List[List[int]], List[int]]:
    """
    Re-stream BGL.log and build sliding-window sequences.

    Each window is a list of template IDs of length window_size.
    Window label = 1 if any line in the window is anomalous.

    Returns:
        (sequences, labels) — lists of equal length.
    """
    buffer_ids: List[int] = []
    buffer_labels: List[int] = []

    sequences: List[List[int]] = []
    labels: List[int] = []
    total = 0

    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            total += 1
            if max_lines and total > max_lines:
                break

            result = _parse_bgl_line(line)
            if result is None:
                continue

            is_anomaly, message = result
            normalized = _normalize_bgl_message(message)
            tid = msg_to_id.get(normalized, unk_id)

            buffer_ids.append(tid)
            buffer_labels.append(1 if is_anomaly else 0)

            while len(buffer_ids) >= window_size:
                window_ids = buffer_ids[:window_size]
                window_label = 1 if any(buffer_labels[:window_size]) else 0

                sequences.append(window_ids)
                labels.append(window_label)

                buffer_ids = buffer_ids[step_size:]
                buffer_labels = buffer_labels[step_size:]

    return sequences, labels


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    datasets_dir: Path,
    output_dir: Path,
    max_lines: Optional[int],
    window_size: int,
    step_size: int,
    max_templates: int,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> None:
    log_path = datasets_dir / "BGL.log"

    if not log_path.exists():
        print(f"  ERROR: BGL.log not found at {log_path}")
        sys.exit(1)
    print(f"  Source: {log_path}")
    print(f"  Output: {output_dir}\n")

    # === Pass 1 ===
    print("=" * 60)
    print("PASS 1: Stream, parse, normalize, count template frequencies")
    print("=" * 60)

    t0 = time.time()
    counter, total_lines, parsed_lines, anomaly_lines = pass1_count_templates(
        log_path, max_lines=max_lines,
    )
    normal_lines = parsed_lines - anomaly_lines
    p1_time = time.time() - t0

    print(f"  Total lines:       {total_lines:,}")
    print(f"  Parsed lines:      {parsed_lines:,}")
    print(f"  Skipped:           {total_lines - parsed_lines:,}")
    print(f"  Normal lines:      {normal_lines:,} ({100 * normal_lines / max(parsed_lines, 1):.1f}%)")
    print(f"  Anomaly lines:     {anomaly_lines:,} ({100 * anomaly_lines / max(parsed_lines, 1):.1f}%)")
    print(f"  Unique templates:  {len(counter):,}")
    print(f"  Pass 1 time:       {p1_time:.1f}s\n")

    # --- Build vocabulary ---
    print(f"Building vocabulary (top {max_templates} templates by frequency)...")
    token_to_id, id_to_token, templates = build_vocab_from_counter(counter, max_templates)
    vocab_size = len(token_to_id)
    msg_to_id = _build_message_to_tid(templates, token_to_id)
    unk_id = token_to_id[UNK_TOKEN]

    kept_count = sum(counter[msg] for msg in msg_to_id.keys())
    unk_count = sum(counter.values()) - kept_count
    print(f"  Vocab size:        {vocab_size} (PAD + {len(templates)} templates + UNK)")
    print(f"  Lines covered:     {kept_count:,} ({100 * kept_count / max(parsed_lines, 1):.1f}%)")
    print(f"  Lines → UNK:       {unk_count:,} ({100 * unk_count / max(parsed_lines, 1):.1f}%)")

    top5 = list(templates.items())[:5]
    print("  Top 5 templates:")
    for tid, msg in top5:
        freq = counter[msg]
        print(f"    {tid:>4s} ({freq:>8,}x)  {msg[:80]}{'...' if len(msg) > 80 else ''}")
    print()

    # === Pass 2 ===
    print("=" * 60)
    print("PASS 2: Stream, map template IDs, build sliding windows")
    print("=" * 60)
    print(f"  Window size:       {window_size}")
    print(f"  Step size:         {step_size}")

    t0 = time.time()
    sequences, labels = pass2_build_windows(
        log_path, msg_to_id, unk_id,
        window_size=window_size,
        step_size=step_size,
        max_lines=max_lines,
    )
    p2_time = time.time() - t0

    n_windows = len(sequences)
    n_anomaly_windows = sum(labels)
    n_normal_windows = n_windows - n_anomaly_windows

    print(f"  Windows:           {n_windows:,}")
    print(f"  Normal windows:    {n_normal_windows:,} ({100 * n_normal_windows / max(n_windows, 1):.1f}%)")
    print(f"  Anomaly windows:   {n_anomaly_windows:,} ({100 * n_anomaly_windows / max(n_windows, 1):.1f}%)")
    print(f"  Pass 2 time:       {p2_time:.1f}s\n")

    assert n_windows > 0, "No windows produced — check log file and window_size"
    assert len(sequences) == len(labels), "Sequence/label count mismatch"

    # --- Encode into numpy arrays ---
    print("Encoding sequences into numpy arrays...")
    max_seq_len = window_size
    sequences_arr = np.array(sequences, dtype=np.int32)
    labels_arr = np.array(labels, dtype=np.int32)

    assert sequences_arr.shape == (n_windows, max_seq_len)
    assert labels_arr.shape == (n_windows,)

    unique_ids = set(sequences_arr.flatten()) - {0}
    max_valid_id = max(token_to_id.values())
    out_of_range = [tid for tid in unique_ids if tid > max_valid_id]
    assert len(out_of_range) == 0, f"Template IDs out of range: {out_of_range}"

    print(f"  Shape:             {sequences_arr.shape}")
    print(f"  Unique IDs used:   {len(unique_ids)} (excl. PAD)\n")

    # --- Stratified split ---
    print(f"Stratified split (val={val_ratio}, test={test_ratio}, seed={seed})...")
    (train_seq, train_lbl,
     val_seq, val_lbl,
     test_seq, test_lbl) = stratified_split(
        sequences_arr, labels_arr,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
    )

    def _split_stats(name: str, lbl: np.ndarray) -> None:
        n = len(lbl)
        anom = int(lbl.sum())
        norm = n - anom
        print(f"  {name:6s}: {n:>8,} total  |  {norm:>8,} normal  |  {anom:>6,} anomaly  "
              f"({100 * anom / n:.2f}%)")

    _split_stats("Train", train_lbl)
    _split_stats("Val", val_lbl)
    _split_stats("Test", test_lbl)
    print()

    # --- Save artifacts ---
    print(f"Saving artifacts to {output_dir}/...")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_vocab(output_dir / "template_vocab.json", token_to_id, id_to_token, templates)
    np.save(output_dir / "train_sequences.npy", train_seq)
    np.save(output_dir / "train_labels.npy", train_lbl)
    np.save(output_dir / "val_sequences.npy", val_seq)
    np.save(output_dir / "val_labels.npy", val_lbl)
    np.save(output_dir / "test_sequences.npy", test_seq)
    np.save(output_dir / "test_labels.npy", test_lbl)

    metadata = {
        "dataset": "BGL",
        "source_files": {
            "log": str(log_path),
        },
        "config": {
            "max_seq_len": max_seq_len,
            "window_size": window_size,
            "step_size": step_size,
            "max_templates": max_templates,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio,
            "seed": seed,
        },
        "preprocessing": {
            "strategy": "sliding_window",
            "template_extraction": "frequency_based_normalization",
            "window_labeling": "any_anomalous_line",
        },
        "vocab_size": vocab_size,
        "num_templates": len(templates),
        "total_lines": total_lines,
        "parsed_lines": parsed_lines,
        "total_windows": n_windows,
        "class_distribution": {
            "line_level": {
                "normal": normal_lines,
                "anomaly": anomaly_lines,
                "anomaly_ratio": round(anomaly_lines / max(parsed_lines, 1), 4),
            },
            "window_level": {
                "normal": n_normal_windows,
                "anomaly": n_anomaly_windows,
                "anomaly_ratio": round(n_anomaly_windows / max(n_windows, 1), 4),
            },
        },
        "splits": {
            "train": {"total": len(train_lbl), "anomaly": int(train_lbl.sum())},
            "val": {"total": len(val_lbl), "anomaly": int(val_lbl.sum())},
            "test": {"total": len(test_lbl), "anomaly": int(test_lbl.sum())},
        },
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    expected_files = [
        "template_vocab.json",
        "train_sequences.npy", "train_labels.npy",
        "val_sequences.npy", "val_labels.npy",
        "test_sequences.npy", "test_labels.npy",
        "metadata.json",
    ]
    for fname in expected_files:
        fpath = output_dir / fname
        assert fpath.exists(), f"Expected artifact not found: {fpath}"
        size_kb = fpath.stat().st_size / 1024
        print(f"  {fname:28s} ({size_kb:>10,.1f} KB)")

    print("\nAll artifacts saved.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BGL preprocessing pipeline for Transformer anomaly detection"
    )
    parser.add_argument(
        "--datasets-dir", type=Path,
        default=Path("datasets/raw/BGL"),
        help="Path to the BGL dataset directory containing BGL.log",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("ml/artifacts/bgl"),
        help="Where to save preprocessed artifacts",
    )
    parser.add_argument(
        "--max-lines", type=int, default=None,
        help="Process only the first N lines (for dev/testing)",
    )
    parser.add_argument(
        "--window-size", type=int, default=50,
        help="Number of log lines per sliding window (default: 50)",
    )
    parser.add_argument(
        "--step-size", type=int, default=None,
        help="Sliding window step size (default: same as window-size for non-overlapping)",
    )
    parser.add_argument(
        "--max-templates", type=int, default=300,
        help="Maximum number of templates to keep in vocabulary",
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.1,
        help="Fraction of data for validation split",
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.1,
        help="Fraction of data for test split",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible splits",
    )
    args = parser.parse_args()

    step = args.step_size if args.step_size is not None else args.window_size

    start = time.time()
    print()
    print("BGL Preprocessing Pipeline")
    print("=" * 60)
    print(f"  Dataset dir:     {args.datasets_dir}")
    print(f"  Output dir:      {args.output_dir}")
    print(f"  Max lines:       {args.max_lines or 'all'}")
    print(f"  Window size:     {args.window_size}")
    print(f"  Step size:       {step}")
    print(f"  Max templates:   {args.max_templates}")
    print(f"  Split ratios:    train={1 - args.val_ratio - args.test_ratio:.0%} / "
          f"val={args.val_ratio:.0%} / test={args.test_ratio:.0%}")
    print(f"  Seed:            {args.seed}")
    print()

    run_pipeline(
        datasets_dir=args.datasets_dir,
        output_dir=args.output_dir,
        max_lines=args.max_lines,
        window_size=args.window_size,
        step_size=step,
        max_templates=args.max_templates,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    elapsed = time.time() - start
    print("=" * 60)
    print(f"Pipeline complete in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
