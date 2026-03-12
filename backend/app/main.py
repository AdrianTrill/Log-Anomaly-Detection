"""
LogLens API — FastAPI backend for log parsing, normalization, and AI-ready
anomaly detection. Routes are organized under /api:
  - /api/health           — system status and registered ML models
  - /api/upload           — file upload → parse → normalize → summarize pipeline
  - /api/analyze          — placeholder for future model inference
  - /api/datasets         — list available research datasets on disk
  - /api/datasets/preview — parse a slice of a dataset for inspection
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, upload, analysis, datasets

app = FastAPI(
    title="Log Anomaly Detection API",
    version=settings.app_version,
    description="API for log parsing, normalization, and AI-ready anomaly detection",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
