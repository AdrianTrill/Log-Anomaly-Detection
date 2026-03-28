#!/usr/bin/env python3
"""
Scan benchmark dataset slices to find the best ranges for model comparison demos.

Calls the existing /api/datasets/preview endpoint for many overlapping slices,
comparing Transformer Encoder vs LogBERT predictions on each one, then ranks
slices by disagreement count, score gap, and other metrics.

Usage:
    # Start the backend first, then:
    python scripts/find_comparison_slices.py --dataset BGL --line-count 500 --stride 250
    python scripts/find_comparison_slices.py --dataset both --output results/comparison_scan.json
    python scripts/find_comparison_slices.py --dataset HDFS_v1 --top-k 10 --max-start 100000
"""

from __future__ import annotations

import argparse
import json
import csv
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

# ── Model pairs per dataset ──

MODEL_PAIRS: dict[str, tuple[str, str]] = {
    "HDFS_v1": ("transformer_encoder_hdfs", "logbert_hdfs"),
    "BGL": ("transformer_encoder_bgl", "logbert_bgl"),
}


# ── Data structures ──

@dataclass
class SliceStats:
    dataset_name: str
    start_line: int
    end_line: int
    line_count: int
    model_a: str
    model_b: str
    both_anomaly: int = 0
    both_normal: int = 0
    only_a: int = 0
    only_b: int = 0
    disagreement_count: int = 0
    agreement_count: int = 0
    agreement_rate: float = 0.0
    avg_abs_score_gap: float = 0.0
    max_abs_score_gap: float = 0.0
    anomaly_count_a: int = 0
    anomaly_count_b: int = 0
    avg_score_a: float = 0.0
    avg_score_b: float = 0.0
    entries_compared: int = 0


@dataclass
class ScanConfig:
    base_url: str = "http://localhost:8000"
    datasets: list[str] = field(default_factory=lambda: ["HDFS_v1", "BGL"])
    line_count: int = 500
    stride: int = 250
    max_start: int | None = None
    output: str | None = None
    top_k: int = 20


# ── API helpers ──

def call_preview(base_url: str, dataset_name: str, max_lines: int,
                 start_line: int, model_name: str) -> dict[str, Any] | None:
    """POST to /api/datasets/preview and return the parsed JSON response."""
    url = f"{base_url}/api/datasets/preview"
    body = {
        "dataset_name": dataset_name,
        "max_lines": max_lines,
        "start_line": start_line,
        "model_name": model_name,
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {dataset_name} start={start_line} model={model_name}")
        return None
    except urllib.error.URLError as e:
        print(f"  Connection error: {e.reason}")
        return None


def extract_ai_pairs(entries_a: list[dict], entries_b: list[dict]) -> list[tuple[dict, dict]]:
    """Pair entries index-by-index, returning only pairs where both have AI output."""
    n = min(len(entries_a), len(entries_b))
    if len(entries_a) != len(entries_b):
        print(f"  Warning: entry count mismatch ({len(entries_a)} vs {len(entries_b)}), using min={n}")
    pairs = []
    for i in range(n):
        a, b = entries_a[i], entries_b[i]
        if a.get("inference_status") == "completed" and b.get("inference_status") == "completed":
            pairs.append((a, b))
    return pairs


# ── Comparison logic ──

def compare_slice(dataset_name: str, start_line: int, line_count: int,
                  model_a: str, model_b: str,
                  entries_a: list[dict], entries_b: list[dict]) -> SliceStats:
    """Compare two model outputs on the same slice and return stats."""
    pairs = extract_ai_pairs(entries_a, entries_b)
    stats = SliceStats(
        dataset_name=dataset_name,
        start_line=start_line,
        end_line=start_line + line_count - 1,
        line_count=line_count,
        model_a=model_a,
        model_b=model_b,
        entries_compared=len(pairs),
    )
    if not pairs:
        return stats

    score_gaps: list[float] = []
    scores_a: list[float] = []
    scores_b: list[float] = []

    for a, b in pairs:
        a_anom = a.get("prediction") == "anomaly"
        b_anom = b.get("prediction") == "anomaly"

        if a_anom and b_anom:
            stats.both_anomaly += 1
        elif not a_anom and not b_anom:
            stats.both_normal += 1
        elif a_anom:
            stats.only_a += 1
        else:
            stats.only_b += 1

        if a_anom:
            stats.anomaly_count_a += 1
        if b_anom:
            stats.anomaly_count_b += 1

        sa = a.get("anomaly_score")
        sb = b.get("anomaly_score")
        if sa is not None and sb is not None:
            score_gaps.append(abs(sa - sb))
            scores_a.append(sa)
            scores_b.append(sb)

    stats.disagreement_count = stats.only_a + stats.only_b
    stats.agreement_count = stats.both_anomaly + stats.both_normal
    total = stats.agreement_count + stats.disagreement_count
    stats.agreement_rate = round(stats.agreement_count / total, 4) if total > 0 else 0.0

    if score_gaps:
        stats.avg_abs_score_gap = round(sum(score_gaps) / len(score_gaps), 6)
        stats.max_abs_score_gap = round(max(score_gaps), 6)
    if scores_a:
        stats.avg_score_a = round(sum(scores_a) / len(scores_a), 6)
    if scores_b:
        stats.avg_score_b = round(sum(scores_b) / len(scores_b), 6)

    return stats


# ── Scanner ──

def scan_dataset(cfg: ScanConfig, dataset_name: str) -> list[SliceStats]:
    """Scan a dataset in stride increments and return comparison stats for each slice."""
    model_a, model_b = MODEL_PAIRS[dataset_name]
    results: list[SliceStats] = []
    start = 1
    consecutive_short = 0

    print(f"\n{'='*60}")
    print(f"Scanning {dataset_name}  |  {model_a} vs {model_b}")
    print(f"slice={cfg.line_count}  stride={cfg.stride}  max_start={cfg.max_start or 'auto'}")
    print(f"{'='*60}")

    while True:
        if cfg.max_start and start > cfg.max_start:
            print(f"  Reached max_start={cfg.max_start}, stopping.")
            break

        print(f"  [{len(results)+1:>4}] start={start:>8} ...", end=" ", flush=True)
        t0 = time.time()

        resp_a = call_preview(cfg.base_url, dataset_name, cfg.line_count, start, model_a)
        resp_b = call_preview(cfg.base_url, dataset_name, cfg.line_count, start, model_b)

        if resp_a is None or resp_b is None:
            print("API error, stopping.")
            break

        entries_a = resp_a.get("entries", [])
        entries_b = resp_b.get("entries", [])
        returned = len(entries_a)

        if returned == 0:
            print("0 entries returned, stopping.")
            break

        stats = compare_slice(dataset_name, start, cfg.line_count,
                              model_a, model_b, entries_a, entries_b)
        results.append(stats)

        dt = time.time() - t0
        print(f"{returned:>4} lines  disagree={stats.disagreement_count:>3}  "
              f"gap={stats.avg_abs_score_gap:.4f}  ({dt:.1f}s)")

        if returned < cfg.line_count:
            consecutive_short += 1
            if consecutive_short >= 2:
                print("  Short slices, reached end of file.")
                break
        else:
            consecutive_short = 0

        start += cfg.stride

    print(f"\n  Total slices scanned: {len(results)}")
    return results


# ── Ranking and recommendations ──

def print_ranking(results: list[SliceStats], top_k: int) -> None:
    """Print ranked summaries to the console."""
    if not results:
        print("  No results to rank.")
        return

    dataset = results[0].dataset_name

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by DISAGREEMENT COUNT  ({dataset})")
    print(f"{'─'*60}")
    by_disagree = sorted(results, key=lambda s: (-s.disagreement_count, -s.avg_abs_score_gap))
    for i, s in enumerate(by_disagree[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"disagree={s.disagreement_count:>3}  agree={s.agreement_rate:.2%}  "
              f"gap={s.avg_abs_score_gap:.4f}  max_gap={s.max_abs_score_gap:.4f}  "
              f"anom_a={s.anomaly_count_a} anom_b={s.anomaly_count_b}")

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by AVG SCORE GAP  ({dataset})")
    print(f"{'─'*60}")
    by_gap = sorted(results, key=lambda s: -s.avg_abs_score_gap)
    for i, s in enumerate(by_gap[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"gap={s.avg_abs_score_gap:.4f}  max_gap={s.max_abs_score_gap:.4f}  "
              f"disagree={s.disagreement_count:>3}  "
              f"anom_a={s.anomaly_count_a} anom_b={s.anomaly_count_b}")

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by MAX SCORE GAP  ({dataset})")
    print(f"{'─'*60}")
    by_max = sorted(results, key=lambda s: -s.max_abs_score_gap)
    for i, s in enumerate(by_max[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"max_gap={s.max_abs_score_gap:.4f}  gap={s.avg_abs_score_gap:.4f}  "
              f"disagree={s.disagreement_count:>3}  "
              f"anom_a={s.anomaly_count_a} anom_b={s.anomaly_count_b}")


def recommend_presets(results: list[SliceStats]) -> None:
    """Suggest three preset candidates for a dataset."""
    if not results:
        return
    dataset = results[0].dataset_name

    print(f"\n{'━'*60}")
    print(f"  RECOMMENDED PRESETS FOR {dataset}")
    print(f"{'━'*60}")

    # Best disagreement: highest disagreement_count, then avg score gap
    best_disagree = max(results, key=lambda s: (s.disagreement_count, s.avg_abs_score_gap))
    print(f"\n  1. Best Disagreement Slice")
    _print_preset(best_disagree)

    # Mixed / representative: decent anomaly presence from both models, moderate agreement
    has_anomalies = [s for s in results
                     if s.anomaly_count_a > 0 and s.anomaly_count_b > 0
                     and s.both_normal > 0]
    if has_anomalies:
        # Balance: close to 50% anomaly rate averaged across models, with some disagreement
        def mixed_score(s: SliceStats) -> float:
            if s.entries_compared == 0:
                return 0
            avg_anom_rate = (s.anomaly_count_a + s.anomaly_count_b) / (2 * s.entries_compared)
            balance = 1 - abs(avg_anom_rate - 0.35)  # prefer ~35% anomaly rate
            disagree_bonus = min(s.disagreement_count / max(s.entries_compared, 1), 0.2)
            return balance + disagree_bonus

        best_mixed = max(has_anomalies, key=mixed_score)
    else:
        best_mixed = results[len(results) // 2]
    print(f"\n  2. Mixed / Representative Slice")
    _print_preset(best_mixed)

    # High agreement with non-trivial anomaly presence
    with_anomalies = [s for s in results
                      if s.both_anomaly > 0 and s.both_normal > 0]
    if with_anomalies:
        best_agree = max(with_anomalies, key=lambda s: (s.agreement_rate, s.both_anomaly))
    else:
        best_agree = max(results, key=lambda s: s.agreement_rate)
    print(f"\n  3. High Agreement Slice (with anomalies)")
    _print_preset(best_agree)


def _print_preset(s: SliceStats) -> None:
    print(f"     lines {s.start_line}–{s.end_line}  ({s.line_count} lines)")
    print(f"     disagree={s.disagreement_count}  agreement={s.agreement_rate:.2%}")
    print(f"     both_anomaly={s.both_anomaly}  both_normal={s.both_normal}  "
          f"only_a={s.only_a}  only_b={s.only_b}")
    print(f"     avg_gap={s.avg_abs_score_gap:.4f}  max_gap={s.max_abs_score_gap:.4f}")
    print(f"     anomalies: {s.model_a}={s.anomaly_count_a}  {s.model_b}={s.anomaly_count_b}")


# ── Output ──

def save_results(all_results: dict[str, list[SliceStats]], output_path: str) -> None:
    """Save scan results to JSON (and CSV if .csv extension)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    flat = {ds: [asdict(s) for s in slices] for ds, slices in all_results.items()}

    json_path = path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(flat, f, indent=2)
    print(f"\nSaved JSON: {json_path}")

    csv_path = path.with_suffix(".csv")
    all_rows = [s for slices in all_results.values() for s in slices]
    if all_rows:
        fieldnames = list(asdict(all_rows[0]).keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in all_rows:
                writer.writerow(asdict(s))
        print(f"Saved CSV:  {csv_path}")


# ── CLI ──

def parse_args() -> ScanConfig:
    parser = argparse.ArgumentParser(
        description="Find best benchmark slices for model comparison demos")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--dataset", default="both",
                        choices=["HDFS_v1", "BGL", "both"])
    parser.add_argument("--line-count", type=int, default=500)
    parser.add_argument("--stride", type=int, default=250)
    parser.add_argument("--max-start", type=int, default=None)
    parser.add_argument("--output", default=None,
                        help="Output path for results (JSON + CSV)")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    datasets = list(MODEL_PAIRS.keys()) if args.dataset == "both" else [args.dataset]
    return ScanConfig(
        base_url=args.base_url,
        datasets=datasets,
        line_count=args.line_count,
        stride=args.stride,
        max_start=args.max_start,
        output=args.output,
        top_k=args.top_k,
    )


def main() -> None:
    cfg = parse_args()
    all_results: dict[str, list[SliceStats]] = {}

    for dataset in cfg.datasets:
        if dataset not in MODEL_PAIRS:
            print(f"Unknown dataset: {dataset}, skipping.")
            continue
        results = scan_dataset(cfg, dataset)
        all_results[dataset] = results
        print_ranking(results, cfg.top_k)
        recommend_presets(results)

    if cfg.output:
        save_results(all_results, cfg.output)

    print(f"\n{'━'*60}")
    print("  Scan complete.")
    print(f"{'━'*60}")


if __name__ == "__main__":
    main()
