"""
Two-phase training script for LogBERT log anomaly detection.

Phase 1 — Masked Log Key Prediction (MLM pre-training):
    Masks random template IDs and trains the encoder to reconstruct them.
    No labels are used.

Phase 2 — Supervised fine-tuning:
    Loads the pre-trained encoder, adds a classification head on [CLS],
    and fine-tunes with BCEWithLogitsLoss for binary anomaly detection.

Usage:
    python3 -m ml.training.train_logbert \
        --artifacts-dir ml/artifacts/hdfs \
        --output-dir ml/artifacts/hdfs_logbert \
        --pretrain-epochs 20 \
        --finetune-epochs 10 \
        --batch-size 512
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.models.logbert import LogBERT
from ml.utils.dataset import load_split, load_metadata
from ml.utils.metrics import compute_metrics, format_metrics


@dataclass
class LogBERTConfig:
    artifacts_dir: str = "ml/artifacts/hdfs"
    output_dir: str = "ml/artifacts/hdfs_logbert"
    batch_size: int = 512
    d_model: int = 64
    nhead: int = 4
    num_layers: int = 2
    dim_feedforward: int = 128
    dropout: float = 0.1
    pretrain_lr: float = 1e-3
    finetune_lr: float = 5e-4
    weight_decay: float = 1e-4
    pretrain_epochs: int = 20
    finetune_epochs: int = 10
    mask_ratio: float = 0.15
    pad_id: int = 0


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# MLM masking utilities
# ---------------------------------------------------------------------------

def mask_sequences(
    sequences: torch.Tensor,
    mask_ratio: float,
    mask_id: int,
    pad_id: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Apply random masking for MLM pre-training.

    Args:
        sequences:  (batch, seq_len) original token IDs
        mask_ratio: fraction of non-PAD tokens to mask
        mask_id:    token ID for [MASK]
        pad_id:     token ID for [PAD]

    Returns:
        masked:  (batch, seq_len) sequences with masked positions replaced
        targets: (batch, seq_len) original token IDs (for loss computation)
        mask:    (batch, seq_len) boolean — True at masked positions
    """
    targets = sequences.clone()
    masked = sequences.clone()

    non_pad = sequences != pad_id
    rand = torch.rand_like(sequences, dtype=torch.float)
    selected = non_pad & (rand < mask_ratio)

    masked[selected] = mask_id

    return masked, targets, selected


# ---------------------------------------------------------------------------
# Phase 1: MLM pre-training
# ---------------------------------------------------------------------------

def pretrain_one_epoch(
    model: LogBERT,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    mask_ratio: float,
) -> float:
    model.train()
    total_loss = 0.0
    n_batches = 0
    criterion = nn.CrossEntropyLoss(ignore_index=-100)

    for sequences, _labels in loader:
        sequences = sequences.to(device)

        masked, targets, mask_positions = mask_sequences(
            sequences, mask_ratio, model.mask_id, model.pad_id
        )

        optimizer.zero_grad()
        logits = model.forward_mlm(masked)

        # logits: (batch, seq_len+1, vocab)  — +1 because CLS is prepended
        # Targets need the same CLS offset: position 0 is CLS (ignored),
        # positions 1.. correspond to the original sequence positions.
        batch_size, seq_len = sequences.size()
        cls_pad = torch.full((batch_size, 1), -100, dtype=torch.long, device=device)
        mlm_targets = torch.full_like(targets, -100, dtype=torch.long)
        mlm_targets[mask_positions] = targets[mask_positions]
        mlm_targets = torch.cat([cls_pad, mlm_targets], dim=1)

        loss = criterion(logits.reshape(-1, logits.size(-1)), mlm_targets.reshape(-1))
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def pretrain_validate(
    model: LogBERT,
    loader: DataLoader,
    device: torch.device,
    mask_ratio: float,
) -> Dict[str, float]:
    model.eval()
    criterion = nn.CrossEntropyLoss(ignore_index=-100)
    total_loss = 0.0
    correct = 0
    total_masked = 0
    n_batches = 0

    for sequences, _labels in loader:
        sequences = sequences.to(device)
        masked, targets, mask_positions = mask_sequences(
            sequences, mask_ratio, model.mask_id, model.pad_id
        )

        logits = model.forward_mlm(masked)

        batch_size, seq_len = sequences.size()
        cls_pad = torch.full((batch_size, 1), -100, dtype=torch.long, device=device)
        mlm_targets = torch.full_like(targets, -100, dtype=torch.long)
        mlm_targets[mask_positions] = targets[mask_positions]
        mlm_targets = torch.cat([cls_pad, mlm_targets], dim=1)

        loss = criterion(logits.reshape(-1, logits.size(-1)), mlm_targets.reshape(-1))
        total_loss += loss.item()
        n_batches += 1

        preds = logits.argmax(dim=-1)
        masked_flat = mlm_targets != -100
        correct += (preds[masked_flat] == mlm_targets[masked_flat]).sum().item()
        total_masked += masked_flat.sum().item()

    return {
        "loss": total_loss / max(n_batches, 1),
        "accuracy": correct / max(total_masked, 1),
    }


def run_pretraining(
    model: LogBERT,
    train_loader: DataLoader,
    val_loader: DataLoader,
    cfg: LogBERTConfig,
    device: torch.device,
    output: Path,
) -> None:
    print("\n" + "=" * 70)
    print("Phase 1 — Masked Log Key Prediction (MLM Pre-training)")
    print("=" * 70)
    print(f"  Mask ratio:      {cfg.mask_ratio}")
    print(f"  LR:              {cfg.pretrain_lr}")
    print(f"  Epochs:          {cfg.pretrain_epochs}", flush=True)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.pretrain_lr, weight_decay=cfg.weight_decay
    )

    best_loss = float("inf")
    history: List[Dict[str, Any]] = []

    print(f"\n{'Epoch':>5}  {'Train Loss':>10}  {'Val Loss':>10}  {'Val Acc':>8}  Save")
    print("-" * 55, flush=True)

    for epoch in range(1, cfg.pretrain_epochs + 1):
        t0 = time.time()

        train_loss = pretrain_one_epoch(
            model, train_loader, optimizer, device, cfg.mask_ratio
        )
        val_metrics = pretrain_validate(model, val_loader, device, cfg.mask_ratio)
        elapsed = time.time() - t0

        saved = ""
        if val_metrics["loss"] < best_loss:
            best_loss = val_metrics["loss"]
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "best_mlm_loss": best_loss,
                    "phase": "pretrain",
                },
                output / "pretrained.pt",
            )
            saved = " *"

        print(
            f"{epoch:5d}  {train_loss:10.4f}  {val_metrics['loss']:10.4f}  "
            f"{val_metrics['accuracy']:8.4f}{saved}",
            flush=True,
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "val_mask_accuracy": val_metrics["accuracy"],
            "elapsed_s": round(elapsed, 1),
        })

    with open(output / "pretrain_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print("-" * 55)
    print(f"\nPre-training complete. Best MLM val loss: {best_loss:.4f}")
    print(f"Checkpoint: {output / 'pretrained.pt'}")
    print(f"History:    {output / 'pretrain_history.json'}")


# ---------------------------------------------------------------------------
# Phase 2: supervised fine-tuning
# ---------------------------------------------------------------------------

def finetune_one_epoch(
    model: LogBERT,
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
        logits = model.forward_cls(sequences)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def finetune_evaluate(
    model: LogBERT,
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
        logits = model.forward_cls(sequences)
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


def run_finetuning(
    model: LogBERT,
    train_loader: DataLoader,
    val_loader: DataLoader,
    cfg: LogBERTConfig,
    device: torch.device,
    output: Path,
    vocab_size: int,
    max_seq_len: int,
) -> None:
    n_pos = 0
    n_total = 0
    for _seq, lbl in train_loader:
        n_pos += lbl.sum().item()
        n_total += len(lbl)
    n_neg = n_total - n_pos

    print("\n" + "=" * 70)
    print("Phase 2 — Supervised Fine-tuning (Classification)")
    print("=" * 70)
    print(f"  LR:              {cfg.finetune_lr}")
    print(f"  Epochs:          {cfg.finetune_epochs}")
    print(f"  Train set:       {n_total:,} ({int(n_neg):,} normal, {int(n_pos):,} anomaly)")
    print(f"  pos_weight:      {n_neg / max(n_pos, 1):.2f}", flush=True)

    pos_weight = torch.tensor([n_neg / max(n_pos, 1)], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.finetune_lr, weight_decay=cfg.weight_decay
    )

    history: List[Dict[str, Any]] = []
    best_f1 = 0.0
    best_epoch = -1

    print(f"\n{'Epoch':>5}  {'Train Loss':>10}  {'Val Loss':>10}  {'P':>7}  {'R':>7}  {'F1':>7}  {'Acc':>7}  {'AUC':>7}  Save")
    print("-" * 85, flush=True)

    for epoch in range(1, cfg.finetune_epochs + 1):
        t0 = time.time()

        train_loss = finetune_one_epoch(model, train_loader, criterion, optimizer, device)
        val_metrics = finetune_evaluate(model, val_loader, criterion, device)
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
                    "phase": "finetune",
                    "config": asdict(cfg),
                    "metadata": {
                        "vocab_size": vocab_size,
                        "max_seq_len": max_seq_len,
                        "pad_id": cfg.pad_id,
                        "model_type": "logbert",
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

    with open(output / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print("-" * 85)
    print(f"\nFine-tuning complete. Best epoch: {best_epoch} (val F1 = {best_f1:.4f})")
    print(f"Checkpoint: {output / 'best_model.pt'}")
    print(f"History:    {output / 'training_history.json'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train LogBERT (MLM pre-train + supervised fine-tune)"
    )
    parser.add_argument("--artifacts-dir", default="ml/artifacts/hdfs")
    parser.add_argument("--output-dir", default="ml/artifacts/hdfs_logbert")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--nhead", type=int, default=4)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dim-feedforward", type=int, default=128)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--pretrain-lr", type=float, default=1e-3)
    parser.add_argument("--finetune-lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--pretrain-epochs", type=int, default=20)
    parser.add_argument("--finetune-epochs", type=int, default=10)
    parser.add_argument("--mask-ratio", type=float, default=0.15)
    parser.add_argument(
        "--skip-pretrain", action="store_true",
        help="Skip Phase 1 and load existing pretrained.pt for fine-tuning",
    )

    args = parser.parse_args()

    cfg = LogBERTConfig(
        artifacts_dir=args.artifacts_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pretrain_lr=args.pretrain_lr,
        finetune_lr=args.finetune_lr,
        weight_decay=args.weight_decay,
        pretrain_epochs=args.pretrain_epochs,
        finetune_epochs=args.finetune_epochs,
        mask_ratio=args.mask_ratio,
    )

    artifacts = Path(cfg.artifacts_dir)
    output = Path(cfg.output_dir)
    output.mkdir(parents=True, exist_ok=True)

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

    print("=" * 70, flush=True)
    print(f"LogBERT — {dataset_name} Log Anomaly Detection", flush=True)
    print("=" * 70, flush=True)
    print(f"  Artifacts:       {artifacts}")
    print(f"  Output:          {output}")
    print(f"  Vocab size:      {vocab_size} (+ MASK, CLS = {vocab_size + 2})")
    print(f"  Max seq len:     {max_seq_len} (+ CLS = {max_seq_len + 1})")
    print(f"  d_model:         {cfg.d_model}")
    print(f"  Heads:           {cfg.nhead}")
    print(f"  Layers:          {cfg.num_layers}")
    print(f"  dim_feedforward: {cfg.dim_feedforward}")
    print(f"  Dropout:         {cfg.dropout}")
    print(f"  Batch size:      {cfg.batch_size}", flush=True)

    device = get_device()
    print(f"  Device:          {device}")

    train_ds = load_split(artifacts, "train")
    val_ds = load_split(artifacts, "val")
    print(f"  Train set:       {len(train_ds):,}")
    print(f"  Val set:         {len(val_ds):,}", flush=True)

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, num_workers=0)

    model = LogBERT(
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
    print(f"  Model params:    {param_count:,}")

    # --- Phase 1: MLM pre-training ---
    if args.skip_pretrain:
        pretrained_path = output / "pretrained.pt"
        if not pretrained_path.exists():
            print(f"\nERROR: --skip-pretrain but {pretrained_path} not found")
            sys.exit(1)
        print(f"\n  Skipping Phase 1 — loading pre-trained weights from {pretrained_path}")
        ckpt = torch.load(pretrained_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
    else:
        run_pretraining(model, train_loader, val_loader, cfg, device, output)
        ckpt = torch.load(output / "pretrained.pt", map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        print("  Loaded best pre-trained weights for fine-tuning.")

    # --- Phase 2: supervised fine-tuning ---
    nn.init.xavier_uniform_(model.cls_head.weight)
    nn.init.zeros_(model.cls_head.bias)

    run_finetuning(
        model, train_loader, val_loader, cfg, device, output,
        vocab_size=vocab_size, max_seq_len=max_seq_len,
    )


if __name__ == "__main__":
    main()
