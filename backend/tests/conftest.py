import os
from pathlib import Path

import pytest


@pytest.fixture
def configured_services(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "temp"))
    from app.core.config import Settings
    from app.core.services.ingestion_service import IngestionService
    from app.core.services.storage_service import StorageService

    config = Settings()
    return config, StorageService(config), IngestionService(config)
