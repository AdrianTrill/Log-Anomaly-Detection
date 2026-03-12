from pathlib import Path
from pydantic_settings import BaseSettings

# config.py is at backend/app/core/config.py → 3 parents up = backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"
    app_version: str = "0.1.0"
    max_upload_size_mb: int = 50
    datasets_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def resolved_datasets_dir(self) -> Path:
        """Return the datasets directory as an absolute Path.
        Uses DATASETS_DIR env var if set, otherwise defaults to <project_root>/datasets."""
        if self.datasets_dir:
            return Path(self.datasets_dir).resolve()
        return _PROJECT_ROOT / "datasets"

    class Config:
        env_file = ".env"


settings = Settings()
