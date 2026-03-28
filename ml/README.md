# ML Pipeline — Log Anomaly Detection

Offline preprocessing and training code for the Transformer-based log anomaly detection thesis.

This directory is **separate from the FastAPI backend and Next.js frontend**.  The web app handles interactive upload/parsing/visualization; this pipeline handles full-dataset preprocessing and model training offline.

---

## Directory Structure

```
ml/
├── README.md
├── requirements.txt
├── preprocessing/
│   ├── __init__.py
│   ├── preprocess_hdfs.py          # HDFS pipeline (Phase 1 raw validation + Phase 2 artifacts)
│   ├── preprocess_bgl.py           # BGL pipeline (two-pass streaming from raw log)
│   ├── template_builder.py         # Shared: vocabulary save/load (+ HDFS CSV builder)
│   └── sequence_builder.py         # Shared: encoding, stratified splitting (+ HDFS trace loading)
├── models/
│   ├── __init__.py
│   ├── transformer_encoder.py      # LogAnomalyTransformer (supervised baseline)
│   └── logbert.py                  # LogBERT (MLM pre-train + supervised fine-tune)
├── training/
│   ├── __init__.py
│   ├── train_transformer.py        # Transformer Encoder training
│   ├── evaluate.py                 # Transformer Encoder evaluation
│   ├── train_logbert.py            # LogBERT two-phase training (MLM + fine-tune)
│   └── evaluate_logbert.py         # LogBERT evaluation
├── utils/
│   ├── __init__.py
│   ├── dataset.py                  # Shared: PyTorch Dataset wrappers
│   └── metrics.py                  # Shared: P/R/F1/AUC/CM computation
└── artifacts/
    ├── hdfs/                       # HDFS preprocessing artifacts (shared by all models)
    │   ├── template_vocab.json
    │   ├── metadata.json
    │   ├── {train,val,test}_{sequences,labels}.npy
    │   └── checkpoints/            # Transformer Encoder checkpoints
    ├── hdfs_logbert/               # LogBERT HDFS checkpoints (separate from TE)
    │   ├── pretrained.pt           # MLM pre-trained encoder
    │   ├── best_model.pt           # Fine-tuned classification model
    │   ├── pretrain_history.json
    │   ├── training_history.json
    │   └── eval_results.json
    ├── bgl/                        # BGL preprocessing artifacts (shared by TE + LogBERT)
    │   ├── template_vocab.json
    │   ├── metadata.json
    │   ├── {train,val,test}_{sequences,labels}.npy
    │   └── checkpoints/            # Transformer Encoder checkpoints
    └── bgl_logbert/                # LogBERT BGL checkpoints (separate from TE)
        ├── pretrained.pt           # MLM pre-trained encoder
        ├── best_model.pt           # Fine-tuned classification model
        ├── pretrain_history.json
        ├── training_history.json
        └── eval_results.json
```

---

## Architecture Overview

The pipeline supports multiple benchmark datasets through a shared core and dataset-specific preprocessing:

| Component | Scope | Description |
|-----------|-------|-------------|
| `LogAnomalyTransformer` | Model 1 | Supervised Transformer Encoder baseline |
| `LogBERT` | Model 2 | BERT-style: MLM pre-training + supervised fine-tuning |
| `train_transformer.py` | Model 1 | Parameterized by `--artifacts-dir` and `--output-dir` |
| `evaluate.py` | Model 1 | Parameterized by `--artifacts-dir` and `--checkpoint` |
| `train_logbert.py` | Model 2 | Two-phase training: MLM pre-train then classification fine-tune |
| `evaluate_logbert.py` | Model 2 | Evaluation using fine-tuned LogBERT checkpoint |
| `dataset.py` | Shared | Generic PyTorch Dataset wrappers |
| `metrics.py` | Shared | Binary classification metrics |
| `template_builder.py` | Shared | `save_vocab()` / `load_vocab()` reused by both pipelines |
| `sequence_builder.py` | Shared | `stratified_split()` reused by both pipelines |
| `preprocess_hdfs.py` | HDFS only | Uses Loghub preprocessed CSVs |
| `preprocess_bgl.py` | BGL only | Two-pass streaming from raw BGL.log |

Each dataset produces the same artifact layout (`template_vocab.json`, `metadata.json`, `{split}_{sequences,labels}.npy`) under its own `ml/artifacts/{dataset}/` directory.  Both models consume the same preprocessing artifacts — LogBERT does not need separate preprocessing.

---

## Quick Reference — All Commands

Install dependencies (once):
```bash
pip3 install -r ml/requirements.txt
```

### HDFS

```bash
# Preprocess
backend/venv/bin/python3 -m ml.preprocessing.preprocess_hdfs

# Train
backend/venv/bin/python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs/checkpoints \
    --epochs 10 --batch-size 512

# Evaluate
backend/venv/bin/python3 -m ml.training.evaluate \
    --artifacts-dir ml/artifacts/hdfs \
    --checkpoint ml/artifacts/hdfs/checkpoints/best_model.pt
```

### BGL

```bash
# Preprocess
backend/venv/bin/python3 -m ml.preprocessing.preprocess_bgl

# Train
backend/venv/bin/python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl/checkpoints \
    --epochs 10 --batch-size 512

# Evaluate
backend/venv/bin/python3 -m ml.training.evaluate \
    --artifacts-dir ml/artifacts/bgl \
    --checkpoint ml/artifacts/bgl/checkpoints/best_model.pt
```

### LogBERT (HDFS)

```bash
# Train (both phases: MLM pre-training + supervised fine-tuning)
backend/venv/bin/python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs_logbert \
    --pretrain-epochs 20 --finetune-epochs 10 --batch-size 512

# Re-run fine-tuning only (skip MLM pre-training, reuse pretrained.pt)
backend/venv/bin/python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs_logbert \
    --skip-pretrain --finetune-epochs 10

# Evaluate
backend/venv/bin/python3 -m ml.training.evaluate_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --checkpoint ml/artifacts/hdfs_logbert/best_model.pt
```

### LogBERT (BGL)

```bash
# Train (both phases: MLM pre-training + supervised fine-tuning)
backend/venv/bin/python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl_logbert \
    --pretrain-epochs 20 --finetune-epochs 10 --batch-size 512

# Re-run fine-tuning only (skip MLM pre-training, reuse pretrained.pt)
backend/venv/bin/python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl_logbert \
    --skip-pretrain --finetune-epochs 10

# Evaluate
backend/venv/bin/python3 -m ml.training.evaluate_logbert \
    --artifacts-dir ml/artifacts/bgl \
    --checkpoint ml/artifacts/bgl_logbert/best_model.pt

# Evaluate at different threshold
backend/venv/bin/python3 -m ml.training.evaluate_logbert \
    --artifacts-dir ml/artifacts/bgl \
    --checkpoint ml/artifacts/bgl_logbert/best_model.pt \
    --threshold 0.8
```

### Saving separate runs

The only difference between datasets is the two path arguments (`--artifacts-dir` and `--output-dir` / `--checkpoint`). To save a separate training run without overwriting, change `--output-dir`:

```bash
backend/venv/bin/python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl/checkpoints/second_run \
    --epochs 20 --d-model 128
```

---

## HDFS Preprocessing

The HDFS pipeline targets the **HDFS_v1** dataset from [Loghub](https://github.com/logpai/loghub).

### Hybrid Approach

The preprocessing uses a practical two-phase strategy:

| Phase | Purpose | Data Source | Used for Training? |
|-------|---------|-------------|-------------------|
| **Phase 1 — Raw Validation** | Prove that raw `HDFS.log` can be parsed and normalized using the same logic as the web-app backend | `HDFS.log` (first 5,000 lines) | No |
| **Phase 2 — Artifact Generation** | Build reproducible, benchmark-aligned training sequences | `Event_traces.csv`, `anomaly_label.csv`, `HDFS.log_templates.csv` | **Yes** |

**Why this split?**

- Phase 1 demonstrates the full raw-log pipeline (parsing regex + normalization masks) works correctly — important for the thesis technical chapter.
- Phase 2 uses the Loghub-provided preprocessed files (extracted by the Drain log parser) for the actual training artifacts.  This ensures reproducibility and alignment with published HDFS anomaly detection benchmarks.

---

## HDFS Dataset

Source: Loghub HDFS_v1 — Hadoop Distributed File System block-operation logs.

```
datasets/raw/HDFS_v1/
├── HDFS.log                         # 11.2M raw log lines
└── preprocessed/
    ├── anomaly_label.csv            # 575,061 block sessions (Normal / Anomaly)
    ├── Event_traces.csv             # Per-session event sequences [E5, E22, ...]
    └── HDFS.log_templates.csv       # 29 canonical event templates (E1–E29)
```

### Key Facts

- **575,061** block sessions (each identified by a `blk_*` ID)
- **558,223** Normal (97.1%) / **16,838** Anomaly (2.9%)
- **29** unique event templates extracted by the Drain parser
- Session sequence lengths: min=2, max=298, mean=19.4, median=19.0

---

## Template Vocabulary

Built from `HDFS.log_templates.csv`.  Each log message is mapped to a canonical event template (E1–E29) by the Drain parser.

| Token | ID | Description |
|-------|----|-------------|
| PAD   | 0  | Padding for short sequences |
| E1    | 1  | Adding an already existing block |
| E2    | 2  | Verification succeeded for ... |
| ...   | ...| ... |
| E29   | 29 | PendingReplicationMonitor timed out block ... |
| UNK   | 30 | Unknown / unseen template fallback |

Total vocabulary size: **31 tokens**.

---

## Session-Based Sequence Construction

HDFS is naturally session-based: each block operation (`blk_*`) is a session consisting of an ordered sequence of event templates.

The `Event_traces.csv` Features column already provides these per-session sequences, e.g.:
```
[E5, E22, E5, E5, E11, E9, E11, E9, E11, E9, E26, E26, E26, ...]
```

These are converted to padded integer arrays:
- Event IDs → integer token IDs via the vocabulary
- Sequences shorter than `max_seq_len` (default: 50) are **right-padded** with PAD (0)
- Sequences longer than `max_seq_len` are **truncated** from the right
- Default max_seq_len of 50 covers 99.99% of sessions without truncation (only 55 of 575,061 are truncated)

---

## Label Assignment

Labels come from `anomaly_label.csv`:
- `Normal` → **0**
- `Anomaly` → **1**

This was verified to perfectly align with `Event_traces.csv` (Label column: `Success` = Normal, `Fail` = Anomaly).  All 575,061 block IDs match 1:1 between both files.

---

## Artifacts Produced

Saved to `ml/artifacts/hdfs/`:

| File | Shape | Description |
|------|-------|-------------|
| `template_vocab.json` | — | Token-to-ID mapping, reverse mapping, template descriptions |
| `train_sequences.npy` | `(460048, 50)` | Training integer sequences |
| `train_labels.npy` | `(460048,)` | Training binary labels (0/1) |
| `val_sequences.npy` | `(57506, 50)` | Validation integer sequences |
| `val_labels.npy` | `(57506,)` | Validation binary labels |
| `test_sequences.npy` | `(57507, 50)` | Test integer sequences |
| `test_labels.npy` | `(57507,)` | Test binary labels |
| `metadata.json` | — | Config, split sizes, class distribution, statistics |

Default split: **80% train / 10% val / 10% test**, stratified by label to preserve the ~2.9% anomaly ratio across all splits.

---

## How to Run

### Install dependencies

From the **project root**:

```bash
pip3 install -r ml/requirements.txt
```

### Run the full pipeline

```bash
python3 -m ml.preprocessing.preprocess_hdfs
```

This runs both phases with default settings:
- `--datasets-dir datasets/raw/HDFS_v1`
- `--output-dir ml/artifacts/hdfs`
- `--max-seq-len 50`
- `--val-ratio 0.1`
- `--test-ratio 0.1`
- `--seed 42`

### Custom options

```bash
python3 -m ml.preprocessing.preprocess_hdfs \
    --datasets-dir datasets/raw/HDFS_v1 \
    --output-dir ml/artifacts/hdfs \
    --max-seq-len 75 \
    --val-ratio 0.15 \
    --test-ratio 0.15 \
    --seed 123
```

### Skip raw validation (Phase 1)

```bash
python3 -m ml.preprocessing.preprocess_hdfs --skip-raw-validation
```

---

## How to Verify

The pipeline prints validation output at each step:

1. **Phase 1** — shows parsed/fallback counts, unique block IDs, and 3 raw → parsed → normalized examples
2. **Phase 2** — prints:
   - Vocabulary size and template count
   - Session count and sequence length statistics
   - Label distribution (Normal vs Anomaly)
   - Alignment verification (should show 0 mismatches)
   - Any UNK token warnings
   - Stratified split sizes with per-split anomaly ratios
   - File-by-file artifact verification with sizes

A successful run ends with `Pipeline complete` and all 8 artifact files listed with their sizes.

**Expected output** (with default settings):

```
Phase 1:  5,000 lines parsed, 0 fallback, 626 unique block IDs
Phase 2:  575,061 sessions aligned, 31-token vocab, 29 unique templates used
  Train:  460,048 (13,470 anomaly = 2.93%)
  Val:     57,506  (1,684 anomaly = 2.93%)
  Test:    57,507  (1,684 anomaly = 2.93%)
Pipeline complete in ~6s
```

### Quick smoke test

```bash
python3 -c "
import numpy as np, json
d = 'ml/artifacts/hdfs'
train_seq = np.load(f'{d}/train_sequences.npy')
train_lbl = np.load(f'{d}/train_labels.npy')
meta = json.load(open(f'{d}/metadata.json'))
print(f'Train: {train_seq.shape}, labels: {train_lbl.shape}')
print(f'Anomaly ratio: {train_lbl.mean():.4f}')
print(f'Vocab size: {meta[\"vocab_size\"]}')
print('OK')
"
```

---

## BGL Preprocessing

The BGL pipeline targets the **BGL** dataset from [Loghub](https://github.com/logpai/loghub) — BlueGene/L supercomputer logs from Lawrence Livermore National Labs.

### BGL Dataset

```
datasets/raw/BGL/
└── BGL.log                          # ~4.75M raw log lines (~709 MB)
```

BGL line format (space-delimited, 9 fixed tokens + message):
```
[label] [unix_ts] [date] [node] [precise_ts] [node] [category] [component] [level] [message...]
```

- Column 0 (`label`): `"-"` for normal, alert category string (e.g. `APPREAD`, `KERNDTLB`) for anomalous
- ~4.75M lines, per-line labels (unlike HDFS which has per-session labels)
- No preprocessed CSV files — everything is built from the raw log

### Key Differences from HDFS

| Aspect | HDFS | BGL |
|--------|------|-----|
| Preprocessed CSVs available | Yes (Drain parser output) | No |
| Natural session boundaries | Yes (block IDs) | No |
| Labels | Per session | Per line |
| Template source | Drain-extracted CSV | Frequency-based from normalized messages |
| Sequence strategy | Session-based | Fixed-size sliding window |

### Two-Pass Streaming Approach

BGL preprocessing uses two passes over the raw log to stay memory-safe on 4.75M lines:

| Pass | Purpose | Memory Held |
|------|---------|-------------|
| **Pass 1** | Parse, normalize messages, count template frequencies | Only a `Counter` dict (~thousands of entries) |
| **Pass 2** | Map template IDs, build sliding windows | Rolling buffer of window_size tuples |

**Template extraction:** Each message is aggressively normalized (hex addresses, numbers, IPs, file paths replaced with tokens), then unique normalized messages are ranked by frequency. The top K (default 300) become the vocabulary; the rest map to UNK.

**Sliding windows:** Fixed-size windows of consecutive log lines (default: 50 lines, matching HDFS `max_seq_len`). Non-overlapping by default. A window is labeled anomalous if it contains any anomalous line.

### How to Run BGL Preprocessing

```bash
python3 -m ml.preprocessing.preprocess_bgl
```

Default settings:
- `--datasets-dir datasets/raw/BGL`
- `--output-dir ml/artifacts/bgl`
- `--window-size 50`
- `--step-size 50` (non-overlapping)
- `--max-templates 300`
- `--val-ratio 0.1`, `--test-ratio 0.1`
- `--seed 42`

Custom options:
```bash
python3 -m ml.preprocessing.preprocess_bgl \
    --window-size 100 \
    --step-size 50 \
    --max-templates 500 \
    --max-lines 100000
```

Use `--max-lines` for quick dev/testing on a subset of the log.

### BGL Verification

The pipeline prints detailed statistics at each step:

1. **Pass 1** — total lines, parsed lines, normal/anomaly counts, unique templates, top 5 templates
2. **Pass 2** — window count, normal/anomaly window distribution, encoding shape, split sizes

A successful run ends with `Pipeline complete` and all 8 artifact files listed.

### BGL Smoke Test

```bash
python3 -c "
import numpy as np, json
d = 'ml/artifacts/bgl'
train_seq = np.load(f'{d}/train_sequences.npy')
train_lbl = np.load(f'{d}/train_labels.npy')
meta = json.load(open(f'{d}/metadata.json'))
print(f'Train: {train_seq.shape}, labels: {train_lbl.shape}')
print(f'Anomaly ratio: {train_lbl.mean():.4f}')
print(f'Vocab size: {meta[\"vocab_size\"]}')
print(f'Window size: {meta[\"config\"][\"window_size\"]}')
print('OK')
"
```

---

## Transformer Encoder Training & Evaluation

### Model Architecture

`LogAnomalyTransformer` — a lightweight Transformer Encoder for binary sequence classification.  The same architecture is used for both HDFS and BGL; the `vocab_size` and `max_seq_len` are read from each dataset's `metadata.json`.

```
Input (batch, seq_len)  integer token IDs
        │
  Token Embedding   nn.Embedding(vocab_size, d_model, padding_idx=0)
        +
  Position Embedding nn.Embedding(max_seq_len, d_model)  ← learned positions
        │
  Dropout
        │
  TransformerEncoder (N layers, H heads, pre-norm)
        │
  Mean Pooling       over non-PAD positions
        │
  Linear(d_model, 1) → single logit per sequence
```

### Class Imbalance Handling

Both datasets are imbalanced.  The training script addresses this with `BCEWithLogitsLoss(pos_weight=...)`:
- `pos_weight = num_normal / num_anomaly` (computed from training labels)
- This upweights the loss contribution of anomaly samples without resampling
- Precision, Recall, and F1 are the primary evaluation metrics — accuracy is reported but not used for model selection

### How to Train

From the **project root** (requires preprocessing artifacts to already exist).  Point `--artifacts-dir` and `--output-dir` at the dataset you want to train on:

**HDFS:**
```bash
python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs/checkpoints \
    --epochs 10 --batch-size 512
```

**BGL:**
```bash
python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl/checkpoints \
    --epochs 10 --batch-size 512
```

All hyperparameters are overridable via CLI:

```bash
python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/bgl \
    --output-dir ml/artifacts/bgl/checkpoints \
    --epochs 20 \
    --batch-size 256 \
    --d-model 128 \
    --nhead 8 \
    --num-layers 3 \
    --dim-feedforward 256 \
    --lr 5e-4 \
    --dropout 0.2
```

### Default Hyperparameters

| Parameter       | Default | Rationale                                 |
|-----------------|---------|-------------------------------------------|
| batch_size      | 512     | Fast iteration on 460K samples            |
| d_model         | 64      | Small vocab (31), short sequences         |
| nhead           | 4       | d_model / nhead = 16 per head             |
| num_layers      | 2       | Simple baseline                           |
| dim_feedforward | 128     | 2x d_model                                |
| dropout         | 0.1     | Standard                                  |
| lr              | 1e-3    | AdamW default range                       |
| weight_decay    | 1e-4    | Light regularization                      |
| epochs          | 10      | Sufficient for convergence on this dataset|

### How to Evaluate

After training, evaluate the saved checkpoint on the held-out test set:

**HDFS:**
```bash
python3 -m ml.training.evaluate \
    --artifacts-dir ml/artifacts/hdfs \
    --checkpoint ml/artifacts/hdfs/checkpoints/best_model.pt
```

**BGL:**
```bash
python3 -m ml.training.evaluate \
    --artifacts-dir ml/artifacts/bgl \
    --checkpoint ml/artifacts/bgl/checkpoints/best_model.pt
```

This prints full test metrics and saves them to `eval_results.json`.

### Checkpoint & Output Files

Saved under `ml/artifacts/{dataset}/checkpoints/`:

| File | Description |
|------|-------------|
| `best_model.pt` | Model weights, optimizer state, best F1, epoch, config |
| `training_history.json` | Per-epoch: train_loss, val_loss, val_P/R/F1/accuracy/AUC |
| `eval_results.json` | Final test metrics: P/R/F1/accuracy/AUC + confusion matrix |

### Which Metrics to Focus On

| Metric | Why |
|--------|-----|
| **F1** | Primary — balances precision and recall; used for checkpoint selection |
| **Precision** | What fraction of flagged anomalies are real? |
| **Recall** | What fraction of real anomalies are caught? |
| **ROC-AUC** | Threshold-independent ranking quality |
| Accuracy | Reported but not reliable at 2.9% anomaly ratio |

---

## LogBERT Training & Evaluation

### What is LogBERT?

LogBERT is the second anomaly detection model in this project, providing a comparison against the Transformer Encoder baseline.  While the Transformer Encoder is a **one-stage supervised classifier** (embeddings → encoder → mean pool → BCE loss), LogBERT uses a **two-phase approach** inspired by BERT:

1. **Phase 1 — Masked Log Key Prediction (MLM pre-training):** Randomly mask template IDs in log sequences and train the encoder to reconstruct them.  This learns general log pattern representations without any labels.
2. **Phase 2 — Supervised fine-tuning:** Load the pre-trained encoder, add a classification head, and fine-tune with BCEWithLogitsLoss on labeled data.

The thesis value is in comparing whether self-supervised pre-training on log sequences improves anomaly detection over training from scratch.

### Key Differences from Transformer Encoder

| Aspect | Transformer Encoder | LogBERT |
|--------|-------------------|---------|
| Training | One-stage supervised | Two-phase: MLM pre-train → supervised fine-tune |
| Special tokens | None (PAD + events + UNK) | `[MASK]` and `[CLS]` added internally |
| Effective vocab | 31 (HDFS) | 33 (31 + MASK + CLS) |
| Pooling | Mean pooling over non-PAD | CLS token output |
| Heads | Single classification head | MLM head (pre-training) + classification head (fine-tuning) |
| Pre-training | None | Masked token prediction on all training sequences |

Both models use the same encoder architecture (TransformerEncoderLayer, pre-norm, batch_first) and consume the exact same preprocessing artifacts.

### LogBERT Architecture

```
Input (batch, seq_len)  integer token IDs
        │
  [CLS] Prepend         (batch, seq_len) → (batch, seq_len + 1)
        │
  Token Embedding   nn.Embedding(vocab_size + 2, d_model, padding_idx=0)
        +
  Position Embedding nn.Embedding(max_seq_len + 1, d_model)
        │
  LayerNorm + Dropout
        │
  TransformerEncoder (N layers, H heads, pre-norm)
        │
        ├── forward_mlm():  MLM Head → (batch, seq_len+1, vocab) token logits
        │                   Loss on masked positions only (CrossEntropyLoss)
        │
        └── forward_cls():  CLS output → Linear(d_model, 1) → (batch,) logit
                            Binary classification (BCEWithLogitsLoss)
```

The MLM head is a two-layer projection: `Linear → GELU → LayerNorm → Linear`.

### Data Reuse

LogBERT uses the **exact same** preprocessing artifacts as the Transformer Encoder for each dataset — no new preprocessing is needed. The `train_logbert.py` and `evaluate_logbert.py` scripts are fully dataset-agnostic; the only difference between HDFS and BGL is the `--artifacts-dir` argument.

**HDFS:**
- `ml/artifacts/hdfs/template_vocab.json` (31-token vocab; LogBERT extends internally to 33)
- `ml/artifacts/hdfs/metadata.json` (reads `vocab_size`, `max_seq_len`)
- `ml/artifacts/hdfs/{train,val,test}_{sequences,labels}.npy`

**BGL:**
- `ml/artifacts/bgl/template_vocab.json` (302-token vocab; LogBERT extends internally to 304)
- `ml/artifacts/bgl/metadata.json` (reads `vocab_size`, `max_seq_len`)
- `ml/artifacts/bgl/{train,val,test}_{sequences,labels}.npy`

### How to Train LogBERT

From the **project root**:

```bash
python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs_logbert \
    --pretrain-epochs 20 \
    --finetune-epochs 10 \
    --batch-size 512
```

This runs both phases sequentially:
1. MLM pre-training (saves `pretrained.pt` + `pretrain_history.json`)
2. Loads the best pre-trained weights, reinitializes the classification head, fine-tunes (saves `best_model.pt` + `training_history.json`)

To **skip Phase 1** and re-run only fine-tuning (e.g. with different hyperparameters):

```bash
python3 -m ml.training.train_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs_logbert \
    --skip-pretrain \
    --finetune-epochs 15 \
    --finetune-lr 1e-4
```

### LogBERT CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--artifacts-dir` | `ml/artifacts/hdfs` | Input preprocessing artifacts |
| `--output-dir` | `ml/artifacts/hdfs_logbert` | Output directory for checkpoints |
| `--batch-size` | 512 | Batch size for both phases |
| `--d-model` | 64 | Embedding / encoder dimension |
| `--nhead` | 4 | Attention heads |
| `--num-layers` | 2 | Encoder layers |
| `--dim-feedforward` | 128 | Feed-forward dimension |
| `--dropout` | 0.1 | Dropout rate |
| `--pretrain-lr` | 1e-3 | Learning rate for MLM pre-training |
| `--finetune-lr` | 5e-4 | Learning rate for fine-tuning (lower to preserve pre-trained features) |
| `--weight-decay` | 1e-4 | AdamW weight decay |
| `--pretrain-epochs` | 20 | MLM pre-training epochs |
| `--finetune-epochs` | 10 | Supervised fine-tuning epochs |
| `--mask-ratio` | 0.15 | Fraction of non-PAD tokens masked for MLM |
| `--skip-pretrain` | flag | Skip Phase 1, load existing `pretrained.pt` |

### How to Evaluate LogBERT

```bash
python3 -m ml.training.evaluate_logbert \
    --artifacts-dir ml/artifacts/hdfs \
    --checkpoint ml/artifacts/hdfs_logbert/best_model.pt
```

Supports `--threshold` (default 0.5) for direct comparison with the Transformer Encoder.

### LogBERT Output Artifacts

Saved to `ml/artifacts/hdfs_logbert/` (HDFS) or `ml/artifacts/bgl_logbert/` (BGL):

| File | Phase | Description |
|------|-------|-------------|
| `pretrained.pt` | 1 (MLM) | Encoder weights after MLM pre-training |
| `pretrain_history.json` | 1 (MLM) | Per-epoch: train_loss, val_loss, val_mask_accuracy |
| `best_model.pt` | 2 (fine-tune) | Full model: encoder + cls_head + config + metadata |
| `training_history.json` | 2 (fine-tune) | Per-epoch: train_loss, val_loss, val_P/R/F1/accuracy/AUC |
| `eval_results.json` | eval | Test metrics: P/R/F1/accuracy/AUC + confusion matrix |

---

## Stage 3 — Backend & Frontend Integration (Completed)

Four model checkpoints are wired into the FastAPI backend with dataset-specific inference services, thresholds, and a model selection mechanism in the frontend.

**Centralized configuration** (`backend/app/core/inference_config.py`) — keyed by model identifier:

| Model | Checkpoint | Threshold | Scope | Dataset |
|-------|-----------|-----------|-------|---------|
| `transformer_encoder_hdfs` | `ml/artifacts/hdfs/checkpoints/fourth_run-BEST/best_model.pt` | 0.5 | `hdfs_block_session` | HDFS |
| `transformer_encoder_bgl` | `ml/artifacts/bgl/checkpoints/fourth_run-BEST/best_model.pt` | 0.8 | `bgl_sliding_window` | BGL |
| `logbert_hdfs` | `ml/artifacts/hdfs_logbert/checkpoints/third_run-BEST/best_model.pt` | 0.5 | `hdfs_block_session` | HDFS |
| `logbert_bgl` | `ml/artifacts/bgl_logbert/checkpoints/second_run-BEST/best_model.pt` | 0.8 | `bgl_sliding_window` | BGL |

**Model selection:** The frontend passes an optional `model_name` in the dataset preview request. If omitted, the backend resolves the dataset's default model (HDFS → `transformer_encoder_hdfs`, BGL → `transformer_encoder_bgl`).

**HDFS inference flow** (shared by both Transformer Encoder and LogBERT):

1. User selects HDFS dataset and model (Transformer Encoder or LogBERT) in the benchmark demo
2. Backend parses and normalizes the raw log lines
3. The selected inference service extracts block IDs (`blk_*`) from each entry
4. Looks up the full event sequence per block from `Event_traces.csv`
5. Encodes sequences using `template_vocab.json` with `max_seq_len=50`
6. Runs batch inference through the selected model (lazy-loaded on first request)
7. Maps block-level scores back to all log entries belonging to that block

The only model-level difference is that LogBERT uses `forward_cls()` (CLS-based pooling) while the Transformer Encoder uses `forward()` (mean pooling).

**BGL inference flow** (shared by both Transformer Encoder and LogBERT):

1. User selects BGL dataset and model (Transformer Encoder or LogBERT) in the benchmark demo
2. Backend parses and normalizes the raw log lines
3. The selected inference service normalizes each message using the same BGL regex patterns from preprocessing
4. Maps normalized messages to template IDs via `template_vocab.json`
5. Groups entries into non-overlapping sliding windows of size 50
6. Runs batch inference through the selected model (lazy-loaded on first request)
7. Maps window-level scores back to all log entries in each window
8. Trailing entries that don't fill a complete window get `inference_status = "not_run"`

The only model-level difference is that LogBERT uses `forward_cls()` (CLS-based pooling) while the Transformer Encoder uses `forward()` (mean pooling) — same distinction as HDFS.

**Frontend** displays real `anomaly_score`, `prediction`, and `inference_status` through the existing AI fields. The model selector appears for both HDFS and BGL (each offers Transformer Encoder / LogBERT). A benchmark-only comparison mode allows running both models on the same data slice and viewing results side by side with agreement statistics. The landing page shows offline benchmark results (F1, Precision, Recall, ROC-AUC, confusion matrix) for all 4 models and provides mode-aware presets with guided demo paths.

**Limitations:**
- Inference is benchmark-aligned only — non-HDFS/BGL data gets `inference_status = "not_run"`
- HDFS predictions are per block/session, BGL predictions are per sliding window — not per individual log line
- No explanation system yet (`explanation` field remains null)

## What Comes Next

1. **Generalized inference** — Template matching for arbitrary uploaded logs
2. **Attention visualization** — Explainability for model predictions
