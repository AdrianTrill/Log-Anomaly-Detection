from typing import Optional
from app.models.schemas import ModelInfo
from app.services.analyzer_base import AnalyzerBase
from app.services.transformer_encoder_analyzer import TransformerEncoderAnalyzer


class ModelRegistry:
    """
    Central registry for all anomaly detection models.
    Adding a new model (e.g. LogBERT) means:
    1. Create a class that extends AnalyzerBase
    2. Register it here in __init__
    """

    def __init__(self) -> None:
        self._analyzers: dict[str, AnalyzerBase] = {
            "transformer_encoder": TransformerEncoderAnalyzer(),
        }

    def get_analyzer(self, name: str) -> Optional[AnalyzerBase]:
        return self._analyzers.get(name)

    def list_models(self) -> list[ModelInfo]:
        return [analyzer.model_info() for analyzer in self._analyzers.values()]

    def available_model_names(self) -> list[str]:
        return list(self._analyzers.keys())


registry = ModelRegistry()
