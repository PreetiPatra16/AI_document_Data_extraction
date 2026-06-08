"""Provision required OCR model assets into the persistent model directory."""
import os
from pathlib import Path

from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from app.core.config import settings


TROCR_MODEL_ID = "microsoft/trocr-base-handwritten"


def provision_trocr() -> None:
    target = Path(settings.trocr_model_path)
    if (target / "config.json").exists() and (target / "preprocessor_config.json").exists():
        print(f"TrOCR model already provisioned at {target}")
        return
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {TROCR_MODEL_ID} to {target}")
    TrOCRProcessor.from_pretrained(TROCR_MODEL_ID).save_pretrained(target)
    VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL_ID).save_pretrained(target)


def provision_paddle() -> None:
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(settings.model_dir / "paddlex"))
    from paddleocr import PaddleOCR

    print(
        "Ensuring PaddleOCR models are available: "
        f"{settings.paddle_detection_model}, {settings.paddle_recognition_model}"
    )
    PaddleOCR(
        text_detection_model_name=settings.paddle_detection_model,
        text_recognition_model_name=settings.paddle_recognition_model,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )


def main() -> None:
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    provision_trocr()
    provision_paddle()
    print(f"OCR model provisioning complete in {settings.model_dir}")


if __name__ == "__main__":
    main()
