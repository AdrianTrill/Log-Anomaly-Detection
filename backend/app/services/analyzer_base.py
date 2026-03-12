from abc import ABC, abstractmethod
from app.models.schemas import LogEntry, ModelInfo


class AnalyzerBase(ABC):
    """
    Abstract base for all anomaly detection models.
    Every model (Transformer Encoder, LogBERT, etc.) must implement this interface
    so the API layer and model registry remain model-agnostic.
    """

    @abstractmethod
    def analyze(self, entries: list[LogEntry]) -> list[LogEntry]:
        """Run inference on log entries, populating AI fields on each entry."""
        ...

    @abstractmethod
    def model_info(self) -> ModelInfo:
        """Return metadata about this model's name, status, and description."""
        ...
