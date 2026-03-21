"""
Training script for the Transformer Encoder log anomaly detector.

Usage:
    python3 -m ml.training.train_transformer \
        --artifacts-dir ml/artifacts/hdfs \
        --output-dir ml/artifacts/hdfs/checkpoints \
        --epochs 10 --batch-size 512
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.models.transformer_encoder import LogAnomalyTransformer
from ml.utils.dataset import load_split, load_metadata
from ml.utils.metrics import compute_metrics, format_metrics


@dataclass
class TrainConfig:
    artifacts_dir: str = "ml/artifacts/hdfs"
    output_dir: str = "ml/artifacts/hdfs/checkpoints"
    batch_size: int = 512
    d_model: int = 64
    nhead: int = 4
    num_layers: int = 2
    dim_feedforward: int = 128
    dropout: float = 0.1
    lr: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 10
    pad_id: int = 0


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    n_batches = 0

    for sequences, labels in loader:
        sequences, labels = sequences.to(device), labels.to(device)
        optimizer.zero_grad()
        logits = model(sequences)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, Any]:
    model.eval()
    all_labels: List[np.ndarray] = []
    all_probs: List[np.ndarray] = []
    total_loss = 0.0
    n_batches = 0

    for sequences, labels in loader:
        sequences, labels = sequences.to(device), labels.to(device)
        logits = model(sequences)
        loss = criterion(logits, labels)
        total_loss += loss.item()
        n_batches += 1

        probs = torch.sigmoid(logits).cpu().numpy()
        all_probs.append(probs)
        all_labels.append(labels.cpu().numpy())

    y_true = np.concatenate(all_labels)
    y_prob = np.concatenate(all_probs)
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = compute_metrics(y_true, y_pred, y_prob)
    metrics["loss"] = total_loss / max(n_batches, 1)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Transformer Encoder for log anomaly detection")
    parser.add_argument("--artifacts-dir", default="ml/artifacts/hdfs")
    parser.add_argument("--output-dir", default="ml/artifacts/hdfs/checkpoints")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--nhead", type=int, default=4)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dim-feedforward", type=int, default=128)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--epochs", type=int, default=10)

    args = parser.parse_args()

    cfg = TrainConfig(
        artifacts_dir=args.artifacts_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        lr=args.lr,
        weight_decay=args.weight_decay,
        epochs=args.epochs,
    )

    artifacts = Path(cfg.artifacts_dir)
    output = Path(cfg.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # --- verify artifacts ---
    required = [
        "template_vocab.json", "metadata.json",
        "train_sequences.npy", "train_labels.npy",
        "val_sequences.npy", "val_labels.npy",
    ]
    for name in required:
        if not (artifacts / name).exists():
            print(f"ERROR: Missing artifact: {artifacts / name}")
            sys.exit(1)

    metadata = load_metadata(artifacts)
    vocab_size = metadata["vocab_size"]
    max_seq_len = metadata["config"]["max_seq_len"]

    dataset_name = metadata.get("dataset", "Unknown")
    print("=" * 60, flush=True)
    print(f"Transformer Encoder — {dataset_name} Log Anomaly Detection", flush=True)
    print("=" * 60, flush=True)
    print(f"  Artifacts:       {artifacts}")
    print(f"  Output:          {output}")
    print(f"  Vocab size:      {vocab_size}")
    print(f"  Max seq len:     {max_seq_len}")
    print(f"  d_model:         {cfg.d_model}")
    print(f"  Heads:           {cfg.nhead}")
    print(f"  Layers:          {cfg.num_layers}")
    print(f"  dim_feedforward: {cfg.dim_feedforward}")
    print(f"  Dropout:         {cfg.dropout}")
    print(f"  LR:              {cfg.lr}")
    print(f"  Weight decay:    {cfg.weight_decay}")
    print(f"  Batch size:      {cfg.batch_size}")
    print(f"  Epochs:          {cfg.epochs}", flush=True)

    # --- datasets ---
    train_ds = load_split(artifacts, "train")
    val_ds = load_split(artifacts, "val")

    n_pos = int(train_ds.labels.sum().item())
    n_neg = len(train_ds) - n_pos
    print(f"\n  Train set:       {len(train_ds):,} ({n_neg:,} normal, {n_pos:,} anomaly)")
    print(f"  Val set:         {len(val_ds):,}")
    print(f"  Anomaly ratio:   {n_pos / len(train_ds):.4f}", flush=True)

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, num_workers=0)

    # --- model ---
    device = get_device()
    print(f"  Device:          {device}\n")

    model = LogAnomalyTransformer(
        vocab_size=vocab_size,
        d_model=cfg.d_model,
        nhead=cfg.nhead,
        num_layers=cfg.num_layers,
        dim_feedforward=cfg.dim_feedforward,
        max_seq_len=max_seq_len,
        dropout=cfg.dropout,
        pad_id=cfg.pad_id,
    ).to(device)

    param_count = sum(p.numel() for p in model.parameters())
    print(f"  Model params:    {param_count:,}\n")

    # --- loss with class-imbalance weighting ---
    pos_weight = torch.tensor([n_neg / max(n_pos, 1)], device=device)
    print(f"  pos_weight:      {pos_weight.item():.2f}")
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    # --- training loop ---
    history: List[Dict[str, Any]] = []
    best_f1 = 0.0
    best_epoch = -1

    print(f"\n{'Epoch':>5}  {'Train Loss':>10}  {'Val Loss':>10}  {'P':>7}  {'R':>7}  {'F1':>7}  {'Acc':>7}  {'AUC':>7}  Save")
    print("-" * 85, flush=True)

    for epoch in range(1, cfg.epochs + 1):
        t0 = time.time()

        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_metrics = evaluate(model, val_loader, criterion, device)
        elapsed = time.time() - t0

        saved = ""
        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            best_epoch = epoch
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "best_f1": best_f1,
                    "config": asdict(cfg),
                    "metadata": {
                        "vocab_size": vocab_size,
                        "max_seq_len": max_seq_len,
                        "pad_id": cfg.pad_id,
                    },
                },
                output / "best_model.pt",
            )
            saved = " *"

        auc_str = f"{val_metrics.get('roc_auc', 0):.4f}" if "roc_auc" in val_metrics else "   N/A"

        print(
            f"{epoch:5d}  {train_loss:10.4f}  {val_metrics['loss']:10.4f}  "
            f"{val_metrics['precision']:7.4f}  {val_metrics['recall']:7.4f}  "
            f"{val_metrics['f1']:7.4f}  {val_metrics['accuracy']:7.4f}  "
            f"{auc_str}{saved}",
            flush=True,
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "val_precision": val_metrics["precision"],
            "val_recall": val_metrics["recall"],
            "val_f1": val_metrics["f1"],
            "val_accuracy": val_metrics["accuracy"],
            "val_roc_auc": val_metrics.get("roc_auc"),
            "elapsed_s": round(elapsed, 1),
        })

    # --- save history ---
    with open(output / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print("-" * 85)
    print(f"\nBest epoch: {best_epoch} (val F1 = {best_f1:.4f})")
    print(f"Checkpoint saved to: {output / 'best_model.pt'}")
    print(f"History saved to:    {output / 'training_history.json'}")


if __name__ == "__main__":
    main()
