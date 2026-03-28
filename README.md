# Log Anomaly Detection Platform

A full-stack web application for log anomaly detection using Transformer-based models. Supports two benchmark datasets (HDFS, BGL) with two model architectures each (Transformer Encoder and LogBERT), plus custom log upload for parsing and inspection.

## Tech Stack

| Layer    | Technology                                            |
|----------|-------------------------------------------------------|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4  |
| UI       | shadcn/ui, Recharts, TanStack Table, react-dropzone   |
| Backend  | FastAPI, Python 3.9+, Pydantic v2                     |
| ML       | PyTorch, NumPy, scikit-learn                           |
| Theme    | Dark/light mode via next-themes                        |

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### One-command startup (both servers)

```bash
./scripts/dev.sh
```

This launches the backend on `http://localhost:8000` and frontend on `http://localhost:3000` together. Press `Ctrl+C` to stop both.

### Or run them separately

**Backend:**

```bash
./scripts/dev-backend.sh
```

**Frontend** (in a second terminal):

```bash
./scripts/dev-frontend.sh
```

Each script handles setup automatically on first run -- creates the venv, installs dependencies, copies `.env` files. Subsequent runs skip straight to starting the server.

### Setup only (no server start)

If you just want to install dependencies without starting anything:

```bash
./scripts/setup-backend.sh
./scripts/setup-frontend.sh
```

### Manual setup

If you prefer running commands yourself:

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### URLs

| Service  | URL                       |
|----------|---------------------------|
| Frontend | http://localhost:3000      |
| Backend  | http://localhost:8000      |
| API Docs | http://localhost:8000/docs |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app with CORS
│   │   ├── api/routes/
│   │   │   ├── health.py           # GET  /api/health
│   │   │   ├── upload.py           # POST /api/upload
│   │   │   ├── analysis.py         # POST /api/analyze
│   │   │   └── datasets.py         # GET  /api/datasets, POST /api/datasets/preview
│   │   ├── core/
│   │   │   ├── config.py           # Settings via pydantic-settings
│   │   │   └── inference_config.py # Model-keyed inference config (4 models)
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models (LogEntry, UploadResponse, InferenceSummary)
│   │   ├── services/
│   │   │   ├── parser.py           # Regex + fallback log parsing (generic upload)
│   │   │   ├── normalizer.py       # IP/NUM/UUID masking, level standardization
│   │   │   ├── summarizer.py       # Stats generation
│   │   │   ├── dataset_loader.py   # Dataset discovery, model resolution, dispatch
│   │   │   ├── dataset_parsers/
│   │   │   │   ├── base_dataset_parser.py   # Abstract base for dataset parsers
│   │   │   │   ├── hdfs_parser.py           # HDFS log format parser
│   │   │   │   └── bgl_parser.py            # BGL log format parser
│   │   │   ├── hdfs_inference_service.py       # HDFS Transformer Encoder inference
│   │   │   ├── logbert_inference_service.py    # HDFS LogBERT inference
│   │   │   ├── bgl_inference_service.py        # BGL Transformer Encoder inference
│   │   │   └── logbert_bgl_inference_service.py # BGL LogBERT inference
│   │   └── utils/
│   │       └── file_utils.py       # File validation and reading
│   ├── requirements.txt
│   └── .env.example
│
├── datasets/
│   ├── raw/
│   │   ├── HDFS_v1/
│   │   │   ├── HDFS.log            # Loghub HDFS dataset
│   │   │   ├── README.md
│   │   │   └── preprocessed/       # Pre-computed labels and templates
│   │   └── BGL/
│   │       ├── BGL.log             # Loghub BGL dataset (~4.7M lines)
│   │       └── README.md
│   └── sample_logs/
│       ├── sample.log              # ~50 lines, mixed formats
│       └── sample2.log             # ~30 lines, different services
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Entry page (benchmark demo + custom upload)
│   │   └── layout.tsx              # Root layout with theme
│   ├── components/
│   │   ├── ai/                     # AI summary section (model name, anomalies)
│   │   ├── dashboard/              # Summary cards, charts, run metadata, comparison view
│   │   ├── landing/                # Offline benchmark results section
│   │   ├── logs/                   # Table, filters, detail panel (score bar, scope context)
│   │   ├── upload/                 # Dataset preview (model + preset selector), file dropzone
│   │   └── ui/                     # shadcn/ui components
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   ├── benchmark-results.ts    # Static offline benchmark metrics (F1, confusion matrix)
│   │   ├── inference.ts            # Model names, scope helpers, threshold formatting
│   │   ├── comparison.ts           # Merge + agreement utilities for comparison mode
│   │   └── utils.ts                # Shared utilities
│   ├── types/                      # TypeScript types matching backend schemas
│   └── package.json
│
├── ml/                             # Offline ML pipeline (separate from web app)
│   ├── models/
│   │   ├── transformer_encoder.py  # LogAnomalyTransformer (supervised baseline)
│   │   └── logbert.py              # LogBERT (MLM pre-train + supervised fine-tune)
│   ├── training/
│   │   ├── train_transformer.py    # Transformer Encoder training
│   │   ├── train_logbert.py        # LogBERT two-phase training
│   │   ├── evaluate.py             # Transformer Encoder evaluation
│   │   └── evaluate_logbert.py     # LogBERT evaluation
│   ├── preprocessing/              # Dataset-specific preprocessing scripts
│   ├── artifacts/                  # Trained models + preprocessing artifacts
│   └── README.md                   # Full ML pipeline documentation
│
└── scripts/
    ├── dev.sh                      # Start both servers
    ├── dev-backend.sh              # Start backend only
    ├── dev-frontend.sh             # Start frontend only
    ├── setup-backend.sh            # Install backend dependencies
    ├── setup-frontend.sh           # Install frontend dependencies
    └── find_comparison_slices.py   # Offline utility to discover best comparison presets
```

## API Endpoints

| Method | Endpoint                | Description                                  |
|--------|-------------------------|----------------------------------------------|
| GET    | `/api/health`           | Health check + available models              |
| POST   | `/api/upload`           | Upload, parse, normalize, summarize          |
| POST   | `/api/analyze`          | Run anomaly detection on entries             |
| GET    | `/api/datasets`         | List registered datasets found on disk       |
| POST   | `/api/datasets/preview` | Preview N lines of a dataset with inference  |

## Datasets

### Folder structure

Place raw dataset files under `datasets/raw/<DatasetName>/`. The backend auto-discovers datasets that have a registered parser.

```
datasets/
  raw/
    HDFS_v1/
      HDFS.log          # required
      README.md
      preprocessed/     # optional pre-computed files
    BGL/
      BGL.log           # required
      README.md
  sample_logs/
    sample.log
    sample2.log
```

### Supported datasets

| Dataset | Log Format                                                        | Parser           |
|---------|-------------------------------------------------------------------|------------------|
| HDFS_v1 | `YYMMDD HHMMSS pid LEVEL component: message`                     | `hdfs_parser.py` |
| BGL     | `label unix_ts date node precise_ts node cat comp level message`  | `bgl_parser.py`  |

### Testing dataset endpoints

List available datasets:

```bash
curl http://localhost:8000/api/datasets
```

Preview 200 lines of HDFS (default model: Transformer Encoder):

```bash
curl -X POST http://localhost:8000/api/datasets/preview \
  -H "Content-Type: application/json" \
  -d '{"dataset_name": "HDFS_v1", "max_lines": 200}'
```

Preview HDFS with LogBERT:

```bash
curl -X POST http://localhost:8000/api/datasets/preview \
  -H "Content-Type: application/json" \
  -d '{"dataset_name": "HDFS_v1", "max_lines": 200, "model_name": "logbert_hdfs"}'
```

Preview BGL with LogBERT:

```bash
curl -X POST http://localhost:8000/api/datasets/preview \
  -H "Content-Type: application/json" \
  -d '{"dataset_name": "BGL", "max_lines": 200, "start_line": 75051, "model_name": "logbert_bgl"}'
```

If `model_name` is omitted, the backend resolves the dataset's default model (HDFS -> Transformer Encoder, BGL -> Transformer Encoder).

### Custom dataset path

By default the backend looks for `datasets/` at the project root. To override:

```bash
export DATASETS_DIR=/path/to/your/datasets
```

Or set `DATASETS_DIR` in `backend/.env`.

### Adding a new dataset parser

1. Create a class extending `BaseDatasetParser` in `backend/app/services/dataset_parsers/`
2. Implement `parse_file()` and `dataset_info()`
3. Register it in `DATASET_REGISTRY` in `dataset_loader.py`
4. Place the raw log file under `datasets/raw/<DatasetName>/`

## Features

### Parsing

Generic upload parsing supports:
- Structured format: `2026-03-09 10:22:00 ERROR auth-service Failed login`
- Bracketed format: `[2026-03-09 10:22:00] [WARN] [db] Connection slow`
- Syslog format: `Mar  9 10:22:00 myhost auth-service[1234]: message`
- ISO 8601 format: `2026-03-09T10:22:00Z ERROR auth-service message`
- Fallback: preserves raw lines that don't match known patterns

### Normalization
- IP addresses masked as `<IP>`
- Long numbers (5+ digits) masked as `<NUM>`
- UUIDs masked as `<UUID>`
- Log levels standardized to uppercase

### Benchmark Evaluation UI

The app is designed for thesis presentation with a clear two-track interface:

**Benchmark Evaluation** (primary):
- Landing page with "Offline Benchmark Results" cards showing F1, Precision, Recall, ROC-AUC, Threshold, and confusion matrix summary for all 4 trained models
- "Recommended Demo Paths" quick-action cards that auto-configure dataset, comparison mode, and preset
- Mode-aware presets: single-model presets (Balanced Sample, Anomaly-Dense Region, Normal-Dominant Region) and comparison presets (Best Disagreement, Mixed + Disagreement, Confidence Gap) with explanation panels
- Model selection per dataset (Transformer Encoder or LogBERT)
- Single Model / Model Comparison toggle for benchmark datasets
- Compact metadata strip on results page (dataset, model, scope, threshold, sample, line range)
- Score-vs-threshold visualization in the detail panel
- Lightweight scope context ("why this was flagged") per entry

**Model Comparison Mode** (benchmark only):
- Automatic model pairing per dataset (Transformer Encoder vs LogBERT)
- Two parallel API calls merged client-side -- no backend changes required
- Side-by-side model cards showing anomalies, normal count, anomaly rate, and subtle threshold
- Agreement card with clear agreement/disagreement percentages, renamed labels (Flagged by both, Normal by both, Only Transformer Encoder, Only LogBERT), and contextual interpretation line
- Helper line explaining entry-level counts and threshold behavior
- Dual-column comparison table with compact headers (TE / LogBERT)
- Comparison-aware filters (All, Flagged by either, Flagged by both, Disagree)
- Side-by-side AI analysis in the detail panel with score-vs-threshold bars
- Subtle left-border highlight for disagreement rows

**Custom Log Inspection** (secondary, collapsible):
- Upload any log file for parsing and inspection
- No trained model inference on arbitrary uploads

### Dashboard
- Anomaly detection summary card with model name, anomaly count, and rate
- Searchable, filterable, sortable log table with AI prediction column
- Click-to-inspect detail panel with raw line, extracted fields, normalized pattern, and AI analysis
- Comparison detail panel with side-by-side model predictions and score bars
- Collapsible parsing details (summary cards, log level chart, source chart)
- Export parsed logs as JSON
- Dark/light theme toggle

### Anomaly Detection

Four trained models are integrated into the app, covering two datasets and two architectures:

| Model                       | Dataset | Threshold |     F1 | Precision | Recall | ROC-AUC |
|-----------------------------|---------|-----------|--------|-----------|--------|---------|
| Transformer Encoder (HDFS)  | HDFS_v1 |       0.5 | 99.35% |    98.77% | 99.94% |  99.99% |
| LogBERT (HDFS)              | HDFS_v1 |       0.5 | 99.56% |    99.12% |   100% |  99.99% |
| Transformer Encoder (BGL)   | BGL     |       0.8 | 93.85% |    97.90% | 90.11% |  99.78% |
| LogBERT (BGL)               | BGL     |       0.8 | 94.49% |    98.64% | 90.68% |  99.81% |

Prediction granularity:
- **HDFS** -- per block-session (all log lines sharing a `blk_*` ID get the same score)
- **BGL** -- per sliding window (consecutive groups of 50 lines)

The landing page is designed as a curated thesis presentation. An "Offline Benchmark Results" section shows F1, Precision, Recall, ROC-AUC, threshold, and confusion matrix summaries for all 4 models at a glance. "Recommended Demo Paths" cards guide the professor to the most interesting comparison slices. Presets are mode-aware: single-model mode shows general-purpose presets (Balanced Sample, Anomaly-Dense Region, Normal-Dominant Region), while comparison mode shows presets optimized for model disagreement (Best Disagreement, Mixed + Disagreement, Confidence Gap). Each preset includes an explanation panel. In comparison mode, the frontend fires two parallel API calls for the same data slice and merges results client-side into a side-by-side view with agreement statistics and a dual-column comparison table. Comparison summary cards show anomalies, normal counts, anomaly rates, agreement/disagreement percentages, and contextual interpretation. A compact metadata strip at the top of the results page shows the full run context for easy screenshots. Custom uploads get parsing and inspection only (no inference). Models are lazy-loaded on first request and cached in memory. Thresholds are centralized in `inference_config.py` and surfaced in the API response.

## ML Pipeline

The offline ML pipeline lives in `ml/` and handles preprocessing, training, and evaluation separately from the web app. See [`ml/README.md`](ml/README.md) for full documentation.

Two model architectures across two datasets:

**Transformer Encoder** -- one-stage supervised training. Log-template embeddings pass through a Transformer encoder, are mean-pooled, and classified with binary cross-entropy.

**LogBERT** -- two-phase training. Phase 1: self-supervised Masked Log Key Prediction (MLKP) pre-trains the encoder on unlabelled sequences. Phase 2: supervised fine-tuning adds a `[CLS]`-based classification head for anomaly detection.

Both architectures consume the same preprocessing artifacts per dataset (`template_vocab.json`, `metadata.json`, `{split}_{sequences,labels}.npy`). Training and evaluation scripts are dataset-agnostic -- only `--artifacts-dir` and `--output-dir` differ between runs.

```
ml/artifacts/
├── hdfs/              # HDFS preprocessing + Transformer Encoder checkpoints
├── hdfs_logbert/      # LogBERT HDFS checkpoints
├── bgl/               # BGL preprocessing + Transformer Encoder checkpoints
└── bgl_logbert/       # LogBERT BGL checkpoints
```

## Future Roadmap

1. **Generalized inference** -- Template matching for arbitrary uploaded logs
2. **Attention visualization** -- Explainability for model predictions
