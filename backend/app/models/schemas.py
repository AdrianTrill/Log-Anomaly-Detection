from typing import Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    id: str
    line_number: int
    raw_line: str
    timestamp: Optional[str] = None
    level: Optional[str] = None
    source: Optional[str] = None
    message: Optional[str] = None
    normalized_message: Optional[str] = None
    parse_status: str = "parsed"

    # AI placeholder fields -- populated by model inference later
    anomaly_score: Optional[float] = None
    prediction: Optional[str] = None
    explanation: Optional[str] = None
    model_name: Optional[str] = None
    inference_status: str = "not_run"


class NormalizationInfo(BaseModel):
    ip_masked: int = 0
    num_masked: int = 0
    uuid_masked: int = 0
    levels_standardized: int = 0


class TimeRange(BaseModel):
    earliest: Optional[str] = None
    latest: Optional[str] = None


class UploadResponse(BaseModel):
    file_name: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    level_distribution: dict[str, int] = Field(default_factory=dict)
    source_distribution: dict[str, int] = Field(default_factory=dict)
    time_range: Optional[TimeRange] = None
    entries: list[LogEntry] = Field(default_factory=list)
    normalization_info: NormalizationInfo = Field(default_factory=NormalizationInfo)
    ai_ready: bool = True


class ModelInfo(BaseModel):
    model_name: str
    status: str
    description: str


class AnalysisRequest(BaseModel):
    entry_ids: list[str] = Field(default_factory=list)
    model_name: str = "transformer_encoder"


class AnalysisResponse(BaseModel):
    model_name: str
    status: str
    entries: list[LogEntry] = Field(default_factory=list)
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    models: list[ModelInfo] = Field(default_factory=list)


# --- Dataset discovery and preview ---

class DatasetInfo(BaseModel):
    name: str
    description: str
    path: str
    format: str
    num_files: int = 1


class DatasetsListResponse(BaseModel):
    datasets_dir: str
    datasets: list[DatasetInfo] = Field(default_factory=list)


class DatasetPreviewRequest(BaseModel):
    dataset_name: str
    max_lines: int = Field(default=200, ge=1, le=10000)
