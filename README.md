# Log Anomaly Detection Platform

A full-stack web application for log analysis with a modular architecture ready for AI-based anomaly detection. Upload raw log files, parse and normalize them, visualize results in an interactive dashboard, and prepare for transformer-based anomaly detection.

## Tech Stack

| Layer     | Technology                                              |
|-----------|---------------------------------------------------------|
| Frontend  | Next.js 16 (App Router), TypeScript, Tailwind CSS v4   |
| UI        | shadcn/ui, Recharts, TanStack Table, react-dropzone    |
| Backend   | FastAPI, Python, Pydantic v2                            |
| Theme     | Dark/light mode via next-themes                         |

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

| Service  | URL                                  |
|----------|--------------------------------------|
| Frontend | http://localhost:3000                 |
| Backend  | http://localhost:8000                 |
| API Docs | http://localhost:8000/docs            |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app with CORS
│   │   ├── api/routes/
│   │   │   ├── health.py           # GET  /api/health
│   │   │   ├── upload.py           # POST /api/upload
│   │   │   ├── analysis.py         # POST /api/analyze (AI stub)
│   │   │   └── datasets.py         # GET  /api/datasets, POST /api/datasets/preview
│   │   ├── core/
│   │   │   └── config.py           # Settings via pydantic-settings
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models (LogEntry, UploadResponse, etc.)
│   │   ├── services/
│   │   │   ├── parser.py           # Regex + fallback log parsing (generic upload)
│   │   │   ├── normalizer.py       # IP/NUM/UUID masking, level standardization
│   │   │   ├── summarizer.py       # Stats generation
│   │   │   ├── dataset_loader.py   # Dataset discovery and dispatch
│   │   │   ├── dataset_parsers/
│   │   │   │   ├── base_dataset_parser.py   # Abstract base for dataset parsers
│   │   │   │   ├── hdfs_parser.py           # HDFS log format parser
│   │   │   │   └── bgl_parser.py            # BGL log format parser
│   │   │   ├── analyzer_base.py    # Abstract model interface (ABC)
│   │   │   ├── transformer_encoder_analyzer.py  # Placeholder
│   │   │   ├── model_registry.py   # Model registration and lookup
│   │   │   └── sequence_builder.py # Future ML preprocessing stub
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
│   │   ├── page.tsx                # Landing page
│   │   ├── analyze/page.tsx        # Upload + dashboard page
│   │   └── layout.tsx              # Root layout with nav and theme
│   ├── components/
│   │   ├── ai/                     # AI placeholder section
│   │   ├── dashboard/              # Summary cards, charts, orchestrator
│   │   ├── logs/                   # Table, filters, details drawer
│   │   ├── upload/                 # Dropzone, sample data button
│   │   └── ui/                     # shadcn/ui components
│   ├── lib/                        # API client, utilities
│   ├── types/                      # TypeScript types matching backend schemas
│   └── package.json
│
└── scripts/
    ├── dev.sh                      # Start both servers
    ├── dev-backend.sh              # Start backend only
    ├── dev-frontend.sh             # Start frontend only
    ├── setup-backend.sh            # Install backend dependencies
    └── setup-frontend.sh           # Install frontend dependencies
```

## API Endpoints

| Method | Endpoint              | Description                                        |
|--------|-----------------------|----------------------------------------------------|
| GET    | /api/health           | Health check + available models                    |
| POST   | /api/upload           | Upload, parse, normalize, summarize                |
| POST   | /api/analyze          | AI analysis stub (placeholder)                     |
| GET    | /api/datasets         | List registered datasets found on disk             |
| POST   | /api/datasets/preview | Parse first N lines of a dataset (returns UploadResponse) |

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

| Dataset | Format | Parser |
|---------|--------|--------|
| HDFS_v1 | `YYMMDD HHMMSS pid LEVEL component: message` | `hdfs_parser.py` |
| BGL     | `label unix_ts date node precise_ts node cat comp level message` | `bgl_parser.py` |

### Testing dataset endpoints

List available datasets:

```bash
curl http://localhost:8000/api/datasets
```

Preview 200 lines of HDFS:

```bash
curl -X POST http://localhost:8000/api/datasets/preview \
  -H "Content-Type: application/json" \
  -d '{"dataset_name": "HDFS_v1", "max_lines": 200}'
```

Preview 500 lines of BGL:

```bash
curl -X POST http://localhost:8000/api/datasets/preview \
  -H "Content-Type: application/json" \
  -d '{"dataset_name": "BGL", "max_lines": 500}'
```

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

### Dashboard
- Summary stat cards (total, parsed, failed, errors, warnings, info)
- Log level distribution bar chart
- Source/component distribution chart
- Searchable, filterable, sortable log table
- Click-to-inspect entry details drawer
- Export parsed logs as JSON
- Dark/light theme toggle

### AI Integration Points
Every log entry includes AI-ready fields from day one:
- `anomaly_score`: null (will contain float 0-1)
- `prediction`: null (will contain "normal" | "anomaly")
- `explanation`: null (will contain model reasoning)
- `model_name`: null (will contain "transformer_encoder" | "logbert")
- `inference_status`: "not_run" (will transition through "completed" | "error")

The frontend renders these fields generically, so plugging in real model output requires zero UI changes.

## Architecture for Future ML Integration

```
Upload → Parse → Normalize → [Sequence Builder] → [Model Inference] → Results
                                    ↑                      ↑
                              Future: template         Future: Transformer
                              extraction + vocab       Encoder → LogBERT
```

### Adding a New Model

1. Create a class extending `AnalyzerBase` in `backend/app/services/`
2. Implement `analyze()` and `model_info()`
3. Register it in `ModelRegistry.__init__`
4. The API and frontend will pick it up automatically

### Sequence Builder

The `SequenceBuilder` abstract class defines the preprocessing pipeline:
- `extract_templates()` — convert normalized messages to log templates
- `build_vocab()` — map templates to integer IDs
- `build_sequences()` — create sliding windows for model input

Dataset-specific logic (HDFS sessions, BGL time windows, etc.) stays encapsulated inside concrete `SequenceBuilder` implementations.

## Future Roadmap

1. **Transformer Encoder** — Integrate the first anomaly detection model
2. **LogBERT** — Add as a second model option
3. **Model comparison mode** — Side-by-side results from multiple models
4. **Dataset preprocessing** — HDFS, BGL, Thunderbird-specific sequence builders
5. **Batch processing** — Large file streaming and async analysis
