"""
Transformer Encoder analyzer — delegates to dataset-specific inference
services (HDFS block-level, BGL sliding-window) for anomaly detection.
For entries without a matching service, marks inference as not_available.
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
            logger.error("HDFS inference failed: %s", e)

        try:
            from app.services.bgl_inference_service import bgl_service
            if bgl_service.is_available():
                entries, _, _ = bgl_service.annotate_entries(entries)
                return entries
        except Exception as e:
            logger.error("BGL inference failed: %s", e)

        for entry in entries:
            entry.model_name = self.MODEL_NAME
            entry.inference_status = "not_available"
        return entries

    def model_info(self) -> ModelInfo:
        available_datasets: list[str] = []

        try:
            from app.services.hdfs_inference_service import hdfs_service
            if hdfs_service.is_available():
                available_datasets.append("HDFS")
        except Exception:
            pass

        try:
            from app.services.bgl_inference_service import bgl_service
            if bgl_service.is_available():
                available_datasets.append("BGL")
        except Exception:
            pass

        if available_datasets:
            datasets_str = ", ".join(available_datasets)
            return ModelInfo(
                model_name=self.MODEL_NAME,
                status="available",
                description=f"Transformer Encoder for log anomaly detection — {datasets_str} datasets available",
            )
        return ModelInfo(
            model_name=self.MODEL_NAME,
            status="unavailable",
            description="Transformer Encoder for log anomaly detection (no checkpoints found)",
        )
