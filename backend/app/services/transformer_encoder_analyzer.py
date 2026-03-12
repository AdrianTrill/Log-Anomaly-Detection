from app.models.schemas import LogEntry, ModelInfo
from app.services.analyzer_base import AnalyzerBase


class TransformerEncoderAnalyzer(AnalyzerBase):
    """
    Placeholder for the Transformer Encoder anomaly detection model.
    When implemented, this will:
    1. Accept normalized log entries
    2. Convert them to model-ready sequences via SequenceBuilder
    3. Run inference through the encoder
    4. Populate anomaly_score, prediction, and explanation on each entry
    """

    MODEL_NAME = "transformer_encoder"

    def analyze(self, entries: list[LogEntry]) -> list[LogEntry]:
        for entry in entries:
            entry.model_name = self.MODEL_NAME
            entry.inference_status = "not_available"
            entry.anomaly_score = None
            entry.prediction = None
            entry.explanation = None
        return entries

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_name=self.MODEL_NAME,
            status="not_implemented",
            description="Transformer Encoder for log sequence anomaly detection (coming soon)",
        )
