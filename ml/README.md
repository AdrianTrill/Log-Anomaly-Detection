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
│   ├── preprocess_hdfs.py          # Main pipeline script (Phase 1 + Phase 2)
│   ├── template_builder.py         # Template vocabulary builder (E1–E29 + PAD + UNK)
│   └── sequence_builder.py         # Trace loading, encoding, stratified splitting
├── models/
│   ├── __init__.py
│   └── transformer_encoder.py      # LogAnomalyTransformer model
├── training/
│   ├── __init__.py
│   ├── train_transformer.py        # Training script with CLI
│   └── evaluate.py                 # Test-set evaluation script
├── utils/
│   ├── __init__.py
│   ├── dataset.py                  # PyTorch Dataset wrappers
│   └── metrics.py                  # P/R/F1/AUC/CM computation
└── artifacts/
    └── hdfs/                       # Generated artifacts (gitignored)
        ├── template_vocab.json
        ├── metadata.json
        ├── train_sequences.npy / train_labels.npy
        ├── val_sequences.npy   / val_labels.npy
        ├── test_sequences.npy  / test_labels.npy
        └── checkpoints/
            ├── best_model.pt
            ├── training_history.json
            └── eval_results.json
```

---

## Preprocessing Overview

The first implemented pipeline targets the **HDFS_v1** dataset from [Loghub](https://github.com/logpai/loghub).

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

## Stage 2 — Transformer Encoder Training & Evaluation

### Model Architecture

`LogAnomalyTransformer` — a lightweight Transformer Encoder for binary sequence classification.

```
Input (batch, 50)  integer token IDs
        │
  Token Embedding   nn.Embedding(31, 64, padding_idx=0)
        +
  Position Embedding nn.Embedding(50, 64)       ← learned positions
        │
  Dropout(0.1)
        │
  TransformerEncoder (2 layers, 4 heads, pre-norm)
        │
  Mean Pooling       over non-PAD positions
        │
  Linear(64, 1)     → single logit per sequence
```

The model is intentionally small (vocabulary of 31 tokens, sequences of length 50) — a large model would overfit this structured data.

### Class Imbalance Handling

The HDFS dataset is heavily imbalanced (~2.9% anomaly). Plain accuracy would reach 97% by predicting "Normal" for everything.

The training script addresses this with `BCEWithLogitsLoss(pos_weight=...)`:
- `pos_weight = num_normal / num_anomaly` (~33x for HDFS)
- This upweights the loss contribution of anomaly samples without resampling
- Precision, Recall, and F1 are the primary evaluation metrics — accuracy is reported but not used for model selection

### How to Train

From the **project root** (requires preprocessing artifacts to already exist):

```bash
python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs/checkpoints \
    --epochs 10 --batch-size 512
```

All hyperparameters are overridable via CLI:

```bash
python3 -m ml.training.train_transformer \
    --artifacts-dir ml/artifacts/hdfs \
    --output-dir ml/artifacts/hdfs/checkpoints \
    --epochs 20 \
    --batch-size 256 \
    --d-model 128 \
    --nhead 8 \
    --num-layers 3 \
    --dim-feedforward 256 \
    --lr 5e-4 \
    --dropout 0.2
```

**Expected output:**

```
============================================================
Transformer Encoder — HDFS Log Anomaly Detection
============================================================
  Artifacts:       ml/artifacts/hdfs
  Vocab size:      31
  Max seq len:     50
  d_model:         64
  ...
  Train set:       460,048 (446,578 normal, 13,470 anomaly)
  Anomaly ratio:   0.0293

Epoch  Train Loss    Val Loss        P        R       F1      Acc      AUC  Save
-------------------------------------------------------------------------------------
    1      ...         ...       0.XXXX  0.XXXX  0.XXXX  0.XXXX  0.XXXX   *
    ...
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

```bash
python3 -m ml.training.evaluate \
    --artifacts-dir ml/artifacts/hdfs \
    --checkpoint ml/artifacts/hdfs/checkpoints/best_model.pt
```

This prints full test metrics and saves them to `eval_results.json`.

### Checkpoint & Output Files

All saved under `ml/artifacts/hdfs/checkpoints/` (gitignored):

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

## Stage 3 — Backend & Frontend Integration (Completed)

The trained HDFS Transformer Encoder checkpoint is now wired into the FastAPI backend via `backend/app/services/hdfs_inference_service.py`.

**How it works:**

1. User previews the HDFS dataset in the web app
2. Backend parses and normalizes the raw log lines (existing flow)
3. `HdfsInferenceService` extracts block IDs (`blk_*`) from each entry
4. Looks up the full event sequence per block from `Event_traces.csv`
5. Encodes sequences using the same `template_vocab.json` and `max_seq_len=50` used in training
6. Runs batch inference through the loaded model (lazy-loaded on first request)
7. Maps block-level scores back to all log entries belonging to that block
8. Frontend displays real `anomaly_score`, `prediction`, and `inference_status` through the existing AI fields

**Current checkpoint:** `ml/artifacts/hdfs/checkpoints/fourth_run/best_model.pt`

**Limitations:**
- Inference is HDFS benchmark-aligned only — non-HDFS data gets `inference_status = "not_run"`
- Predictions are per block/session, not per individual log line
- No explanation system yet (`explanation` field remains null)

## What Comes Next

1. **LogBERT** — Add as a second model for comparison
2. **BGL dataset** — Train and integrate a BGL-specific model
3. **Generalized inference** — Template matching for arbitrary uploaded logs
4. **Attention visualization** — Explainability for model predictions
