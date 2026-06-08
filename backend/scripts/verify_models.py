"""Verify local OCR packages and model assets without downloading anything."""
import importlib.util
from pathlib import Path

from app.core.config import settings


def main() -> int:
    failures = []
    paddle_available = bool(importlib.util.find_spec("paddleocr") and importlib.util.find_spec("paddle"))
    path = Path(settings.trocr_model_path) if settings.trocr_model_path else None
    trocr_packages = bool(importlib.util.find_spec("torch") and importlib.util.find_spec("transformers"))
    print(f"PaddleOCR packages: {'available' if paddle_available else 'missing'}")
    print(f"TrOCR packages: {'available' if trocr_packages else 'missing'}")
    print(f"TrOCR model: {'available' if path and path.exists() else 'missing'}")
    if settings.paddle_required and not paddle_available:
        failures.append("Missing required PaddleOCR packages.")
    if settings.trocr_required and (not path or not path.exists()):
        failures.append("Missing required local TrOCR model directory.")
    if settings.trocr_required and not trocr_packages:
        failures.append("Missing required TrOCR packages.")
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
