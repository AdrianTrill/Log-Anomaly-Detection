from abc import ABC, abstractmethod
from app.models.schemas import LogEntry


class SequenceBuilder(ABC):
    """
    Abstract base for converting normalized log entries into model-ready sequences.

    Future implementations will:
    - extract_templates: Convert normalized messages into log templates
      (e.g., "Failed login for user <NUM> from <IP>" -> template ID)
    - build_vocab: Create a vocabulary mapping from templates to integer IDs
    - build_sequences: Group templates into fixed-size sliding windows
      suitable for Transformer Encoder or LogBERT input

    This is the integration point for dataset-specific preprocessing
    (e.g., HDFS session-based grouping, BGL/Thunderbird time-window grouping)
    without coupling any dataset logic to the API or UI layer.
    """

    @abstractmethod
    def extract_templates(self, entries: list[LogEntry]) -> list[str]:
        """Extract log templates from normalized messages."""
        ...

    @abstractmethod
    def build_vocab(self, templates: list[str]) -> dict[str, int]:
        """Build a template-to-ID vocabulary mapping."""
        ...

    @abstractmethod
    def build_sequences(
        self,
        template_ids: list[int],
        window_size: int = 20,
        step_size: int = 1,
    ) -> list[list[int]]:
        """Construct sliding windows of template IDs for model input."""
        ...


class PlaceholderSequenceBuilder(SequenceBuilder):
    """
    Stub implementation. Returns empty results.
    Will be replaced with real logic when model integration begins.
    """

    def extract_templates(self, entries: list[LogEntry]) -> list[str]:
        return [entry.normalized_message or entry.raw_line for entry in entries]

    def build_vocab(self, templates: list[str]) -> dict[str, int]:
        unique = sorted(set(templates))
        return {t: i for i, t in enumerate(unique)}

    def build_sequences(
        self,
        template_ids: list[int],
        window_size: int = 20,
        step_size: int = 1,
    ) -> list[list[int]]:
        if len(template_ids) < window_size:
            return [template_ids] if template_ids else []
        sequences = []
        for i in range(0, len(template_ids) - window_size + 1, step_size):
            sequences.append(template_ids[i : i + window_size])
        return sequences
