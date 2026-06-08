"""Download TrOCR once into the configured local model directory."""
from pathlib import Path

from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from app.core.config import settings


MODEL_ID = "microsoft/trocr-base-handwritten"


def main() -> None:
    target = Path(settings.trocr_model_path)
    target.mkdir(parents=True, exist_ok=True)
    TrOCRProcessor.from_pretrained(MODEL_ID).save_pretrained(target)
    VisionEncoderDecoderModel.from_pretrained(MODEL_ID).save_pretrained(target)
    print(f"TrOCR model saved to {target}")


if __name__ == "__main__":
    main()
