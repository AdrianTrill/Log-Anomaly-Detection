"""
Transformer Encoder analyzer — delegates to HdfsInferenceService for
HDFS block-level anomaly detection. For non-HDFS entries, marks
inference as not_available.
"""

import logging
from app.models.schemas import LogEntry, ModelInfo
from app.services.analyzer_base import AnalyzerBase

logger = logging.getLogger(__name__)


class TransformerEncoderAnalyzer(AnalyzerBase):

    MODEL_NAME = "transformer_encoder"

    def analyze(self, entries: list[LogEntry]) -> list[LogEntry]:
        try:
            from app.services.hdfs_inference_service import hdfs_service

            if hdfs_service.is_available():
                entries, _, _ = hdfs_service.annotate_entries(entries)
                return entries
        except Exception as e:
            logger.error("Inference failed: %s", e)

        for entry in entries:
            entry.model_name = self.MODEL_NAME
            entry.inference_status = "not_available"
        return entries

    def model_info(self) -> ModelInfo:
        try:
            from app.services.hdfs_inference_service import hdfs_service
            available = hdfs_service.is_available()
        except Exception:
            available = False

        if available:
            return ModelInfo(
                model_name=self.MODEL_NAME,
                status="available",
                description="Transformer Encoder for HDFS log sequence anomaly detection (trained, F1=0.99)",
            )
        return ModelInfo(
            model_name=self.MODEL_NAME,
            status="unavailable",
            description="Transformer Encoder for log sequence anomaly detection (checkpoint not found)",
        )
