"""
HDFS preprocessing pipeline for Transformer-based log anomaly detection.

This script produces training-ready artifacts from the Loghub HDFS_v1 dataset
using a hybrid approach:

  Phase 1 — Raw validation
    Parses a sample of HDFS.log using the same regex as the web-app backend
    (backend/app/services/dataset_parsers/hdfs_parser.py) and normalizes the
    messages (mirroring backend/app/services/normalizer.py).  This proves the
    full raw-log pipeline works but is NOT used for the training artifacts.

  Phase 2 — Benchmark-aligned artifact generation
    Uses the pre-extracted Event_traces.csv, anomaly_label.csv, and
    HDFS.log_templates.csv provided by Loghub.  These files were produced
    by the Drain log parser and are the standard reference for HDFS anomaly
    detection benchmarks.  This path is preferred for training artifacts
    because it ensures reproducibility and alignment with published results.

Usage:
    python -m ml.preprocessing.preprocess_hdfs \\
        --datasets-dir datasets/raw/HDFS_v1 \\
        --output-dir   ml/artifacts/hdfs \\
        --max-seq-len  50 \\
        --seed         42
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

from ml.preprocessing.template_builder import (
    build_vocab_from_csv,
    save_vocab,
    PAD_TOKEN,
    UNK_TOKEN,
)
from ml.preprocessing.sequence_builder import (
    load_traces,
    load_labels,
    align_and_verify,
    encode_sequences,
    stratified_split,
)


# ---------------------------------------------------------------------------
# Phase 1: Raw HDFS.log validation
# ---------------------------------------------------------------------------
# These patterns mirror the backend HDFS parser and normalizer.  They are
# duplicated here so the ML code stays self-contained (no backend imports).

HDFS_LINE_PATTERN = re.compile(
    r"^(\d{6})\s+(\d{6})\s+(\d+)\s+"
    r"(INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|DEBUG|TRACE)\s+"
    r"(\S+?):\s+"
    r"(.+)$",
    re.IGNORECASE,
)

BLOCK_ID_PATTERN = re.compile(r"blk_-?\d+")

IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
LONG_NUM_PATTERN = re.compile(r"\b\d{5,}\b")


def _normalize_message(msg: str) -> str:
    """Mask variable tokens — same order as backend/app/services/normalizer.py."""
    out = msg.strip()
    out = IP_PATTERN.sub("<IP>", out)
    out = UUID_PATTERN.sub("<UUID>", out)
    out = LONG_NUM_PATTERN.sub("<NUM>", out)
    return out


def _format_timestamp(date_part: str, time_part: str) -> str:
    yy, mm, dd = date_part[:2], date_part[2:4], date_part[4:6]
    year = f"20{yy}" if int(yy) < 70 else f"19{yy}"
    hh, mi, ss = time_part[:2], time_part[2:4], time_part[4:6]
    return f"{year}-{mm}-{dd} {hh}:{mi}:{ss}"


def run_raw_validation(hdfs_log_path: Path, sample_lines: int = 5000) -> None:
    """Phase 1: parse and normalize a sample of raw HDFS.log lines."""
    print("=" * 60)
    print("PHASE 1: Raw HDFS.log validation")
    print("=" * 60)
    print(f"  Source: {hdfs_log_path}")
    print(f"  Sample size: first {sample_lines:,} lines\n")

    if not hdfs_log_path.exists():
        print("  SKIP — HDFS.log not found (only preprocessed files required)\n")
        return

    parsed_count = 0
    fallback_count = 0
    block_ids = set()

    examples = []

    with open(hdfs_log_path) as f:
        for i, raw_line in enumerate(f):
            if i >= sample_lines:
                break
            stripped = raw_line.strip()
            if not stripped:
                continue

            m = HDFS_LINE_PATTERN.match(stripped)
            if m:
                parsed_count += 1
                message = m.group(6)
                normalized = _normalize_message(message)
                for blk in BLOCK_ID_PATTERN.findall(stripped):
                    block_ids.add(blk)
                if len(examples) < 3:
                    ts = _format_timestamp(m.group(1), m.group(2))
                    examples.append({
                        "raw": stripped,
                        "timestamp": ts,
                        "level": m.group(4).upper(),
                        "source": m.group(5),
                        "message": message,
                        "normalized": normalized,
                    })
            else:
                fallback_count += 1

    total = parsed_count + fallback_count
    print(f"  Lines read:       {total:,}")
    print(f"  Parsed:           {parsed_count:,}")
    print(f"  Fallback:         {fallback_count:,}")
    print(f"  Unique block IDs: {len(block_ids):,}")
    print()

    for idx, ex in enumerate(examples):
        print(f"  --- Example {idx + 1} ---")
        print(f"  Raw:        {ex['raw'][:120]}...")
        print(f"  Timestamp:  {ex['timestamp']}")
        print(f"  Level:      {ex['level']}")
        print(f"  Source:     {ex['source']}")
        print(f"  Message:    {ex['message'][:100]}...")
        print(f"  Normalized: {ex['normalized'][:100]}...")
        print()

    print("  Phase 1 complete — raw parsing/normalization validated.\n")


# ---------------------------------------------------------------------------
# Phase 2: Benchmark-aligned artifact generation
# ---------------------------------------------------------------------------

def run_artifact_generation(
    datasets_dir: Path,
    output_dir: Path,
    max_seq_len: int,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> None:
    """Phase 2: build training artifacts from preprocessed benchmark files."""
    print("=" * 60)
    print("PHASE 2: Benchmark-aligned artifact generation")
    print("=" * 60)

    templates_path = datasets_dir / "preprocessed" / "HDFS.log_templates.csv"
    traces_path = datasets_dir / "preprocessed" / "Event_traces.csv"
    labels_path = datasets_dir / "preprocessed" / "anomaly_label.csv"

    for p in [templates_path, traces_path, labels_path]:
        if not p.exists():
            print(f"  ERROR: Required file not found: {p}")
            sys.exit(1)
        print(f"  Found: {p}")
    print()

    # --- Step 1: Build template vocabulary ---
    print("Step 1: Building template vocabulary...")
    token_to_id, id_to_token, templates = build_vocab_from_csv(templates_path)
    vocab_size = len(token_to_id)
    print(f"  Templates loaded: {len(templates)}")
    print(f"  Vocabulary size:  {vocab_size} (incl. PAD={PAD_TOKEN}, UNK={UNK_TOKEN})")
    print()

    # --- Step 2: Load event traces ---
    print("Step 2: Loading event traces...")
    t0 = time.time()
    traces = load_traces(traces_path)
    print(f"  Sessions loaded: {len(traces):,}  ({time.time() - t0:.1f}s)")

    seq_lengths = [len(v) for v in traces.values()]
    print(f"  Sequence lengths — min: {min(seq_lengths)}, "
          f"max: {max(seq_lengths)}, "
          f"mean: {np.mean(seq_lengths):.1f}, "
          f"median: {np.median(seq_lengths):.1f}")
    truncated = sum(1 for l in seq_lengths if l > max_seq_len)
    print(f"  Sequences exceeding max_seq_len={max_seq_len}: "
          f"{truncated:,} ({100 * truncated / len(seq_lengths):.2f}%)")
    print()

    # --- Step 3: Load anomaly labels ---
    print("Step 3: Loading anomaly labels...")
    labels = load_labels(labels_path)
    normal_count = sum(1 for v in labels.values() if v == 0)
    anomaly_count = sum(1 for v in labels.values() if v == 1)
    print(f"  Total labels:  {len(labels):,}")
    print(f"  Normal:        {normal_count:,}  ({100 * normal_count / len(labels):.1f}%)")
    print(f"  Anomaly:       {anomaly_count:,}  ({100 * anomaly_count / len(labels):.1f}%)")
    print()

    # --- Step 4: Align and verify ---
    print("Step 4: Aligning traces and labels...")
    block_ids, sessions, targets = align_and_verify(traces, labels)
    print(f"  Aligned sessions: {len(sessions):,}")
    print()

    # --- Step 5: Encode sequences ---
    print(f"Step 5: Encoding sequences (max_seq_len={max_seq_len})...")
    sequences_arr = encode_sequences(sessions, token_to_id, max_seq_len)
    labels_arr = np.array(targets, dtype=np.int32)

    assert sequences_arr.shape[0] == labels_arr.shape[0], "Seq/label count mismatch"
    assert sequences_arr.shape == (len(sessions), max_seq_len)

    unique_ids = set(sequences_arr.flatten()) - {0}
    max_valid_id = max(token_to_id.values())
    out_of_range = [tid for tid in unique_ids if tid > max_valid_id]
    assert len(out_of_range) == 0, f"Template IDs out of range: {out_of_range}"

    print(f"  Encoded shape: {sequences_arr.shape}")
    print(f"  Unique token IDs used (excl. PAD): {len(unique_ids)}")
    print()

    # --- Step 6: Stratified split ---
    print(f"Step 6: Stratified split (val={val_ratio}, test={test_ratio}, seed={seed})...")
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

    # --- Step 7: Save artifacts ---
    print(f"Step 7: Saving artifacts to {output_dir}/...")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_vocab(output_dir / "template_vocab.json", token_to_id, id_to_token, templates)
    np.save(output_dir / "train_sequences.npy", train_seq)
    np.save(output_dir / "train_labels.npy", train_lbl)
    np.save(output_dir / "val_sequences.npy", val_seq)
    np.save(output_dir / "val_labels.npy", val_lbl)
    np.save(output_dir / "test_sequences.npy", test_seq)
    np.save(output_dir / "test_labels.npy", test_lbl)

    metadata = {
        "dataset": "HDFS_v1",
        "source_files": {
            "templates": str(templates_path),
            "traces": str(traces_path),
            "labels": str(labels_path),
        },
        "config": {
            "max_seq_len": max_seq_len,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio,
            "seed": seed,
        },
        "vocab_size": vocab_size,
        "num_templates": len(templates),
        "total_sessions": len(sessions),
        "class_distribution": {
            "normal": normal_count,
            "anomaly": anomaly_count,
            "anomaly_ratio": round(anomaly_count / len(labels), 4),
        },
        "sequence_length_stats": {
            "min": int(min(seq_lengths)),
            "max": int(max(seq_lengths)),
            "mean": round(float(np.mean(seq_lengths)), 1),
            "median": round(float(np.median(seq_lengths)), 1),
            "truncated_count": truncated,
        },
        "splits": {
            "train": {"total": len(train_lbl), "anomaly": int(train_lbl.sum())},
            "val": {"total": len(val_lbl), "anomaly": int(val_lbl.sum())},
            "test": {"total": len(test_lbl), "anomaly": int(test_lbl.sum())},
        },
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Verify files were actually written
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
        print(f"  ✓ {fname:28s} ({size_kb:>10,.1f} KB)")

    print()
    print("Phase 2 complete — all artifacts saved.\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HDFS preprocessing pipeline for Transformer anomaly detection"
    )
    parser.add_argument(
        "--datasets-dir", type=Path,
        default=Path("datasets/raw/HDFS_v1"),
        help="Path to the HDFS_v1 dataset directory",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("ml/artifacts/hdfs"),
        help="Where to save preprocessed artifacts",
    )
    parser.add_argument(
        "--max-seq-len", type=int, default=50,
        help="Maximum event sequence length (pad/truncate)",
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
    parser.add_argument(
        "--skip-raw-validation", action="store_true",
        help="Skip Phase 1 (raw HDFS.log parsing validation)",
    )
    args = parser.parse_args()

    start = time.time()
    print()
    print("HDFS Preprocessing Pipeline")
    print("=" * 60)
    print(f"  Dataset dir:   {args.datasets_dir}")
    print(f"  Output dir:    {args.output_dir}")
    print(f"  Max seq len:   {args.max_seq_len}")
    print(f"  Split ratios:  train={1 - args.val_ratio - args.test_ratio:.0%} / "
          f"val={args.val_ratio:.0%} / test={args.test_ratio:.0%}")
    print(f"  Seed:          {args.seed}")
    print()

    if not args.skip_raw_validation:
        run_raw_validation(args.datasets_dir / "HDFS.log")

    run_artifact_generation(
        datasets_dir=args.datasets_dir,
        output_dir=args.output_dir,
        max_seq_len=args.max_seq_len,
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
