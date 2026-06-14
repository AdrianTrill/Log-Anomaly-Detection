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
    # Ground-truth-aware metrics (require API responses to include `ground_truth`)
    gt_known_count: int = 0
    gt_anomaly_count: int = 0
    gt_normal_count: int = 0
    correct_a: int = 0
    correct_b: int = 0
    accuracy_a: float = 0.0
    accuracy_b: float = 0.0
    both_correct: int = 0
    both_wrong: int = 0
    only_a_correct: int = 0
    only_b_correct: int = 0


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

        # Ground-truth-aware accounting (requires `ground_truth` on entry)
        gt = a.get("ground_truth") or b.get("ground_truth")
        if gt in ("anomaly", "normal"):
            stats.gt_known_count += 1
            if gt == "anomaly":
                stats.gt_anomaly_count += 1
            else:
                stats.gt_normal_count += 1
            a_correct = (a.get("prediction") == gt)
            b_correct = (b.get("prediction") == gt)
            if a_correct:
                stats.correct_a += 1
            if b_correct:
                stats.correct_b += 1
            if a_correct and b_correct:
                stats.both_correct += 1
            elif not a_correct and not b_correct:
                stats.both_wrong += 1
            elif a_correct:
                stats.only_a_correct += 1
            else:
                stats.only_b_correct += 1

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

    if stats.gt_known_count > 0:
        stats.accuracy_a = round(stats.correct_a / stats.gt_known_count, 4)
        stats.accuracy_b = round(stats.correct_b / stats.gt_known_count, 4)

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
        gt_known = stats.gt_known_count
        gt_str = (f"gt={gt_known} (A={stats.accuracy_a:.0%}/B={stats.accuracy_b:.0%})"
                  if gt_known else "gt=0")
        print(f"{returned:>4} lines  disagree={stats.disagreement_count:>3}  "
              f"gap={stats.avg_abs_score_gap:.4f}  {gt_str}  ({dt:.1f}s)")

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

    # Ground-truth-aware rankings (only printed when GT data is present)
    gt_results = [s for s in results if s.gt_known_count > 0]
    if not gt_results:
        return

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by BOTH-MODELS-CORRECT  ({dataset})")
    print(f"{'─'*60}")
    by_both_correct = sorted(gt_results, key=lambda s: (-s.both_correct, -s.gt_anomaly_count))
    for i, s in enumerate(by_both_correct[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"both_correct={s.both_correct:>3}  acc_a={s.accuracy_a:.0%} acc_b={s.accuracy_b:.0%}  "
              f"gt(a/n)={s.gt_anomaly_count}/{s.gt_normal_count}")

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by ONLY-ONE-CORRECT  ({dataset})")
    print(f"{'─'*60}")
    by_only_one = sorted(gt_results,
                          key=lambda s: -max(s.only_a_correct, s.only_b_correct))
    for i, s in enumerate(by_only_one[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"only_a_correct={s.only_a_correct:>3}  only_b_correct={s.only_b_correct:>3}  "
              f"acc_a={s.accuracy_a:.0%} acc_b={s.accuracy_b:.0%}")

    print(f"\n{'─'*60}")
    print(f"  Top {top_k} slices by BOTH-MODELS-WRONG  ({dataset})")
    print(f"{'─'*60}")
    by_both_wrong = sorted(gt_results, key=lambda s: -s.both_wrong)
    for i, s in enumerate(by_both_wrong[:top_k]):
        print(f"  {i+1:>2}. lines {s.start_line:>8}–{s.end_line:>8}  "
              f"both_wrong={s.both_wrong:>3}  acc_a={s.accuracy_a:.0%} acc_b={s.accuracy_b:.0%}  "
              f"gt(a/n)={s.gt_anomaly_count}/{s.gt_normal_count}")


def recommend_presets(results: list[SliceStats]) -> None:
    """Suggest four preset candidates for a dataset, grounded in ground-truth labels.

    Categories:
      1. BOTH CORRECT  — both models agree with ground truth (showcase agreement)
      2. ONLY ONE CORRECT — exactly one model gets ground truth right (highlight model differences)
      3. BOTH WRONG  — both models disagree with ground truth (failure modes)
      4. CONFIDENCE GAP — large score gap (regardless of correctness)

    Falls back to disagreement-only ranking when no ground truth is available.
    """
    if not results:
        return
    dataset = results[0].dataset_name

    # Filter to slices with ground-truth info if available.
    gt_results = [s for s in results if s.gt_known_count > 0]
    has_gt = len(gt_results) > 0

    print(f"\n{'━'*60}")
    print(f"  RECOMMENDED PRESETS FOR {dataset}")
    print(f"  (ground-truth available on {len(gt_results)}/{len(results)} slices)")
    print(f"{'━'*60}")

    if not has_gt:
        print("\n  No ground-truth metadata on any slice — falling back to disagreement-only ranking.")
        print("  (Restart the backend after updating parsers to enable ground-truth presets.)")
        best_disagree = max(results, key=lambda s: (s.disagreement_count, s.avg_abs_score_gap))
        print("\n  1. Best Disagreement Slice")
        _print_preset(best_disagree)
        return

    # Require both classes present so the slice is pedagogically meaningful.
    mixed = [s for s in gt_results if s.gt_anomaly_count > 0 and s.gt_normal_count > 0]
    pool = mixed if mixed else gt_results

    picks: dict[str, SliceStats | None] = {}

    # 1. BOTH CORRECT — prefer slices with the highest both_correct count AND mixed labels.
    picks["both_correct"] = max(pool, key=lambda s: (s.both_correct, s.gt_anomaly_count))

    # 2. ONLY ONE CORRECT — maximise either only_a_correct or only_b_correct.
    picks["only_one_right"] = max(pool, key=lambda s: max(s.only_a_correct, s.only_b_correct))

    # 3. BOTH WRONG — both models miss the ground truth.
    both_wrong_pool = [s for s in pool if s.both_wrong > 0]
    picks["both_fail"] = (max(both_wrong_pool, key=lambda s: s.both_wrong)
                          if both_wrong_pool else max(pool, key=lambda s: s.both_wrong))

    # 4. CONFIDENCE GAP — largest score gap, prefer non-trivial slices.
    picks["confidence_gap"] = max(pool, key=lambda s: (s.avg_abs_score_gap, s.max_abs_score_gap))

    titles = {
        "both_correct":    "1. BOTH MODELS CORRECT  (showcase agreement with ground truth)",
        "only_one_right":  "2. ONLY ONE MODEL CORRECT  (showcase model differences)",
        "both_fail":       "3. BOTH MODELS WRONG  (showcase failure modes)",
        "confidence_gap":  "4. LARGEST CONFIDENCE GAP  (showcase score divergence)",
    }
    for key, title in titles.items():
        s = picks[key]
        if s is None:
            continue
        print(f"\n  {title}")
        _print_preset(s)

    # Copy-paste-ready TypeScript preset block for `DatasetPreview.tsx`.
    print(f"\n{'─'*60}")
    print(f"  TS PRESET BLOCK FOR {dataset}.compare  (copy into DatasetPreview.tsx)")
    print(f"{'─'*60}\n")
    print(_format_ts_preset_block(dataset, picks))


def _format_ts_preset_block(dataset: str, picks: dict[str, SliceStats | None]) -> str:
    """Format the 4 picks as a TypeScript array entries snippet."""
    descriptions = {
        "both_correct":   ("Both models right", "Slice where both models agree with the ground-truth label."),
        "only_one_right": ("Only one model right", "Slice where one model matches ground truth and the other misses."),
        "both_fail":      ("Both models wrong", "Slice where both models miss the ground-truth label."),
        "confidence_gap": ("Largest confidence gap", "Slice with the largest average anomaly-score gap between the two models."),
    }
    lines = []
    for key, s in picks.items():
        if s is None:
            continue
        label, desc = descriptions[key]
        thesis = (
            f"acc(A)={s.accuracy_a:.0%}  acc(B)={s.accuracy_b:.0%}  "
            f"both_correct={s.both_correct} both_wrong={s.both_wrong} "
            f"only_A_correct={s.only_a_correct} only_B_correct={s.only_b_correct} "
            f"gt(anom/normal)={s.gt_anomaly_count}/{s.gt_normal_count} "
            f"gap={s.avg_abs_score_gap:.4f}"
        )
        lines.append(
            "  {\n"
            f"    id: \"{key}\",\n"
            f"    label: \"{label}\",\n"
            f"    description: \"{desc}\",\n"
            f"    thesis: \"{thesis}\",\n"
            f"    lines: {s.line_count},\n"
            f"    startLine: {s.start_line},\n"
            "  },"
        )
    return "[\n" + "\n".join(lines) + "\n]"


def _print_preset(s: SliceStats) -> None:
    print(f"     lines {s.start_line}–{s.end_line}  ({s.line_count} lines)")
    print(f"     disagree={s.disagreement_count}  agreement={s.agreement_rate:.2%}")
    print(f"     both_anomaly={s.both_anomaly}  both_normal={s.both_normal}  "
          f"only_a={s.only_a}  only_b={s.only_b}")
    print(f"     avg_gap={s.avg_abs_score_gap:.4f}  max_gap={s.max_abs_score_gap:.4f}")
    print(f"     anomalies: {s.model_a}={s.anomaly_count_a}  {s.model_b}={s.anomaly_count_b}")
    if s.gt_known_count > 0:
        print(f"     ground truth: anomaly={s.gt_anomaly_count} normal={s.gt_normal_count} "
              f"(known on {s.gt_known_count}/{s.entries_compared})")
        print(f"     correctness: acc_a={s.accuracy_a:.2%} acc_b={s.accuracy_b:.2%}  "
              f"both_correct={s.both_correct} both_wrong={s.both_wrong}  "
              f"only_a_correct={s.only_a_correct} only_b_correct={s.only_b_correct}")


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
