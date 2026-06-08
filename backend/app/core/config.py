import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> List[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    api_env: str = field(default_factory=lambda: os.getenv("API_ENV", "development"))
    api_title: str = field(default_factory=lambda: os.getenv("API_TITLE", "AI Document Data Extraction API"))
    api_version: str = field(default_factory=lambda: os.getenv("API_VERSION", "1.0.0"))
    storage_dir: Path = field(default_factory=lambda: Path(os.getenv("STORAGE_DIR", "storage")))
    temp_dir: Path = field(default_factory=lambda: Path(os.getenv("TEMP_DIR", "temp_uploads")))
    model_dir: Path = field(default_factory=lambda: Path(os.getenv("MODEL_DIR", "models")))
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))))
    max_pdf_pages: int = field(default_factory=lambda: int(os.getenv("MAX_PDF_PAGES", "100")))
    upload_chunk_bytes: int = field(default_factory=lambda: int(os.getenv("UPLOAD_CHUNK_BYTES", str(1024 * 1024))))
    job_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("JOB_TIMEOUT_SECONDS", "900")))
    max_job_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_JOB_ATTEMPTS", "2")))
    worker_poll_seconds: float = field(default_factory=lambda: float(os.getenv("WORKER_POLL_SECONDS", "1")))
    worker_concurrency: int = field(default_factory=lambda: int(os.getenv("WORKER_CONCURRENCY", "1")))
    orphan_max_age_hours: int = field(default_factory=lambda: int(os.getenv("ORPHAN_MAX_AGE_HOURS", "24")))
    accepted_confidence: float = field(default_factory=lambda: float(os.getenv("ACCEPTED_CONFIDENCE", "0.85")))
    review_confidence: float = field(default_factory=lambda: float(os.getenv("REVIEW_CONFIDENCE", "0.70")))
    paddle_required: bool = field(default_factory=lambda: _bool("PADDLE_REQUIRED", False))
    paddle_detection_model: str = field(default_factory=lambda: os.getenv("PADDLE_DETECTION_MODEL", "PP-OCRv5_mobile_det"))
    paddle_recognition_model: str = field(default_factory=lambda: os.getenv("PADDLE_RECOGNITION_MODEL", "en_PP-OCRv5_mobile_rec"))
    trocr_required: bool = field(default_factory=lambda: _bool("TROCR_REQUIRED", False))
    trocr_model_path: str = field(default_factory=lambda: os.getenv("TROCR_MODEL_PATH", ""))
    cors_origins: List[str] = field(default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:3000"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "logs/app.log"))

    @property
    def db_path(self) -> Path:
        return self.storage_dir / "documents.db"

    @property
    def production(self) -> bool:
        return self.api_env == "production"

    def validate(self) -> None:
        if self.max_upload_bytes <= 0 or self.max_pdf_pages <= 0 or self.worker_concurrency <= 0:
            raise ValueError("Upload and PDF page limits must be positive.")
        if not 0 <= self.review_confidence <= self.accepted_confidence <= 1:
            raise ValueError("Confidence thresholds must satisfy 0 <= review <= accepted <= 1.")
        if self.production and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed in production.")


settings = Settings()
settings.validate()
