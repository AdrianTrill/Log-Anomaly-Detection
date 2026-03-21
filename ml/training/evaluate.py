"""
Evaluation script for the trained Transformer Encoder checkpoint.

Usage:
    python3 -m ml.training.evaluate \
        --artifacts-dir ml/artifacts/hdfs \
        --checkpoint ml/artifacts/hdfs/checkpoints/best_model.pt
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from ml.models.transformer_encoder import LogAnomalyTransformer
from ml.utils.dataset import load_split
from ml.utils.metrics import compute_metrics, format_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Transformer Encoder on test set")
    parser.add_argument("--artifacts-dir", default="ml/artifacts/hdfs")
    parser.add_argument("--checkpoint", default="ml/artifacts/hdfs/checkpoints/best_model.pt")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--threshold", type=float, default=0.5, help="Anomaly score threshold (default: 0.5)")
    parser.add_argument("--output", default=None, help="Path to save eval_results.json (default: next to checkpoint)")

    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    artifacts_dir = Path(args.artifacts_dir)

    if not ckpt_path.exists():
        print(f"ERROR: Checkpoint not found: {ckpt_path}")
        sys.exit(1)

    for name in ["test_sequences.npy", "test_labels.npy"]:
        if not (artifacts_dir / name).exists():
            print(f"ERROR: Missing test artifact: {artifacts_dir / name}")
            sys.exit(1)

    # --- load checkpoint ---
    device = torch.device("cpu")
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    cfg = ckpt["config"]
    meta = ckpt["metadata"]

    print("=" * 60)
    print("Transformer Encoder — Test Evaluation")
    print("=" * 60)
    print(f"  Checkpoint: {ckpt_path}")
    print(f"  Epoch:      {ckpt['epoch']}")
    print(f"  Val F1:     {ckpt['best_f1']:.4f}")
    print(f"  Device:     {device}")

    # --- reconstruct model ---
    model = LogAnomalyTransformer(
        vocab_size=meta["vocab_size"],
        d_model=cfg["d_model"],
        nhead=cfg["nhead"],
        num_layers=cfg["num_layers"],
        dim_feedforward=cfg["dim_feedforward"],
        max_seq_len=meta["max_seq_len"],
        dropout=0.0,
        pad_id=meta["pad_id"],
    ).to(device)

    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    # --- load test data ---
    test_ds = load_split(artifacts_dir, "test")
    n_pos = int(test_ds.labels.sum().item())
    n_neg = len(test_ds) - n_pos
    print(f"\n  Test set:   {len(test_ds):,} ({n_neg:,} normal, {n_pos:,} anomaly)")
    print(f"  Anomaly %:  {n_pos / len(test_ds) * 100:.2f}%\n")

    loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # --- inference ---
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for sequences, labels in loader:
            sequences = sequences.to(device)
            logits = model(sequences)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.append(probs)
            all_labels.append(labels.numpy())

    y_true = np.concatenate(all_labels)
    y_prob = np.concatenate(all_probs)
    y_pred = (y_prob >= args.threshold).astype(int)

    print(f"  Threshold:  {args.threshold}\n")
    metrics = compute_metrics(y_true, y_pred, y_prob)

    print("Test Results:")
    print(format_metrics(metrics))

    # --- save results ---
    output_path = Path(args.output) if args.output else ckpt_path.parent / "eval_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = {
        "checkpoint": str(ckpt_path),
        "epoch": ckpt["epoch"],
        "threshold": args.threshold,
        "test_size": len(test_ds),
        "metrics": metrics,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
