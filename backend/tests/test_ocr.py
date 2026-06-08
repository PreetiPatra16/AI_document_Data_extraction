import asyncio

import pytest

import app.core.services.ocr_service as ocr_module
from app.core.services.ocr_service import OCRService
from app.middleware.error_handler import OCRException


def test_ocr_never_returns_fabricated_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_module, "TESSERACT_AVAILABLE", False)
    service = OCRService()
    service.paddle = None
    with pytest.raises(OCRException):
        asyncio.run(service.perform_ocr(str(tmp_path / "missing.png")))
