import os
from collections import defaultdict
from pathlib import Path
from time import monotonic
from typing import Any, Dict, List, Optional

from PIL import Image
from loguru import logger

from app.core.config import Settings, settings
from app.middleware.error_handler import OCRException

settings.model_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(settings.model_dir / "paddlex"))

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception:
    PADDLE_AVAILABLE = False


class OCRService:
    def __init__(self, config: Settings = settings):
        self.settings = config
        self.initialization_errors: Dict[str, str] = {}
        self.paddle = None
        if PADDLE_AVAILABLE:
            try:
                self.paddle = PaddleOCR(
                    text_detection_model_name=config.paddle_detection_model,
                    text_recognition_model_name=config.paddle_recognition_model,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                )
            except Exception as exc:
                self.initialization_errors["paddleocr"] = str(exc)
                logger.exception("PaddleOCR initialization failed")
                self.paddle = None
        self.trocr = None
        self.trocr_device = "cpu"
        if config.trocr_model_path and Path(config.trocr_model_path).exists():
            try:
                import torch
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel

                model = VisionEncoderDecoderModel.from_pretrained(config.trocr_model_path, local_files_only=True)
                if torch.backends.mps.is_available():
                    self.trocr_device = "mps"
                    model = model.to(self.trocr_device)
                self.trocr = (TrOCRProcessor.from_pretrained(config.trocr_model_path, local_files_only=True), model)
            except Exception as exc:
                self.initialization_errors["trocr"] = str(exc)
                logger.exception("TrOCR initialization failed")
                self.trocr = None

    def capabilities(self) -> Dict[str, Any]:
        return {
            "paddleocr": bool(self.paddle),
            "tesseract": TESSERACT_AVAILABLE,
            "trocr": bool(self.trocr),
            "trocr_device": self.trocr_device if self.trocr else None,
            "initialization_errors": self.initialization_errors,
        }

    async def perform_ocr(self, image_path: str, page_num: int = 1, variant: str = "denoised") -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        paddle_error = None
        if self.paddle:
            started = monotonic()
            try:
                results = self._run_paddle(image_path, page_num, variant)
                logger.info(
                    "OCR engine=paddleocr page={} variant={} blocks={} duration_ms={:.2f}",
                    page_num, variant, len(results), (monotonic() - started) * 1000,
                )
            except Exception as exc:
                paddle_error = str(exc)
                logger.exception("OCR engine=paddleocr failed page={} variant={}", page_num, variant)
                results = []
        if not results and TESSERACT_AVAILABLE:
            started = monotonic()
            try:
                results = self._run_tesseract(image_path, page_num, variant)
                logger.info(
                    "OCR engine=tesseract page={} variant={} blocks={} duration_ms={:.2f} fallback_reason={}",
                    page_num,
                    variant,
                    len(results),
                    (monotonic() - started) * 1000,
                    "paddle_failed" if paddle_error else "paddle_unavailable_or_empty",
                )
            except Exception as exc:
                logger.exception("OCR engine=tesseract failed page={} variant={}", page_num, variant)
                raise OCRException(
                    "All configured OCR engines failed.",
                    details={"page": page_num, "paddle_error": paddle_error, "tesseract_error": str(exc)},
                ) from exc
        if not results:
            raise OCRException("No local OCR engine produced text.", details={"capabilities": self.capabilities()})
        return results

    def _block(self, text: str, confidence: float, box: Dict[str, float], page: int, engine: str, variant: str):
        return {
            "text": text.strip(),
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
            "bounding_box": box,
            "polygon": [
                [box["x"], box["y"]],
                [box["x"] + box["width"], box["y"]],
                [box["x"] + box["width"], box["y"] + box["height"]],
                [box["x"], box["y"] + box["height"]],
            ],
            "page": page,
            "source_engine": engine,
            "image_variant": variant,
        }

    def _run_paddle(self, image_path: str, page: int, variant: str) -> List[Dict[str, Any]]:
        raw = self.paddle.predict(image_path)
        output = []
        for result in raw or []:
            data = result.json.get("res", result.json) if hasattr(result, "json") else result
            texts = data.get("rec_texts", [])
            scores = data.get("rec_scores", [])
            polygons = data.get("rec_polys", data.get("dt_polys", []))
            for text, confidence, polygon in zip(texts, scores, polygons):
                points = polygon.tolist() if hasattr(polygon, "tolist") else polygon
                xs, ys = [point[0] for point in points], [point[1] for point in points]
                box = {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}
                output.append(self._block(text, float(confidence), box, page, "paddleocr", variant))
        return output

    def _run_tesseract(self, image_path: str, page: int, variant: str) -> List[Dict[str, Any]]:
        data = pytesseract.image_to_data(Image.open(image_path), output_type=pytesseract.Output.DICT)
        lines: Dict[tuple, List[int]] = defaultdict(list)
        for index, text in enumerate(data["text"]):
            if text.strip() and float(data["conf"][index]) > 0:
                key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
                lines[key].append(index)
        output = []
        for indexes in lines.values():
            text = " ".join(data["text"][i].strip() for i in indexes)
            left = min(data["left"][i] for i in indexes)
            top = min(data["top"][i] for i in indexes)
            right = max(data["left"][i] + data["width"][i] for i in indexes)
            bottom = max(data["top"][i] + data["height"][i] for i in indexes)
            confidence = sum(float(data["conf"][i]) for i in indexes) / len(indexes) / 100
            box = {"x": float(left), "y": float(top), "width": float(right - left), "height": float(bottom - top)}
            output.append(self._block(text, confidence, box, page, "tesseract", variant))
        return output

    async def perform_ocr_multi_variant(self, variants: Dict[str, str], page_num: int) -> List[Dict[str, Any]]:
        """Run OCR on denoised + thresholded variants and merge, keeping the higher-confidence reading per region.

        The thresholded pass is skipped when the denoised pass is already confident,
        which roughly halves processing time on clean digital pages.
        """
        all_blocks: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None
        for variant_name in ("denoised", "thresholded"):
            path = variants.get(variant_name)
            if not path:
                continue
            try:
                blocks = await self.perform_ocr(path, page_num, variant=variant_name)
                all_blocks.extend(blocks)
                if variant_name == "denoised" and blocks:
                    confidences = [b["confidence"] for b in blocks]
                    if len(blocks) >= 5 and sum(confidences) / len(confidences) >= 0.9:
                        logger.info(
                            "OCR variant=thresholded skipped page={} reason=denoised_confident", page_num
                        )
                        break
            except OCRException as exc:
                last_error = exc
                logger.warning("OCR variant={} skipped page={} reason={}", variant_name, page_num, exc.message)
        if not all_blocks:
            if last_error:
                raise last_error
            raise OCRException("No variant produced OCR results.", details={"page": page_num})
        return self._merge_blocks(all_blocks)

    def _iou(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
        bx1, by1 = b["x"], b["y"]
        bx2, by2 = bx1 + b["width"], by1 + b["height"]
        inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
        inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
        inter = inter_w * inter_h
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return inter / union if union > 0 else 0.0

    def _merge_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        used: set = set()
        for i, block in enumerate(blocks):
            if i in used:
                continue
            best = block
            for j in range(i + 1, len(blocks)):
                if j in used or blocks[j]["page"] != block["page"]:
                    continue
                if self._iou(block["bounding_box"], blocks[j]["bounding_box"]) > 0.3:
                    used.add(j)
                    if blocks[j]["confidence"] > best["confidence"]:
                        best = blocks[j]
            merged.append(best)
        return merged

    def recognize_handwriting(self, image_path: str) -> Dict[str, Any]:
        if not self.trocr:
            raise OCRException("Local TrOCR model is unavailable.", details={"engine": "trocr"})
        processor, model = self.trocr
        pixels = processor(images=Image.open(image_path).convert("RGB"), return_tensors="pt").pixel_values.to(self.trocr_device)
        generated = model.generate(pixels)
        text = processor.batch_decode(generated, skip_special_tokens=True)[0]
        return {"text": text, "confidence": 0.7, "source_engine": "trocr"}

    def recognize_handwriting_region(self, image_path: str, bounding_box: Dict[str, float]) -> Dict[str, Any]:
        """Crop a bounding box region from image_path and run TrOCR on it."""
        if not self.trocr:
            raise OCRException("Local TrOCR model is unavailable.", details={"engine": "trocr"})
        img = Image.open(image_path).convert("RGB")
        pad = max(4, int(bounding_box["height"] * 0.15))
        x1 = max(0, int(bounding_box["x"]) - pad)
        y1 = max(0, int(bounding_box["y"]) - pad)
        x2 = min(img.width, int(bounding_box["x"] + bounding_box["width"]) + pad)
        y2 = min(img.height, int(bounding_box["y"] + bounding_box["height"]) + pad)
        if x2 <= x1 or y2 <= y1:
            raise OCRException("Bounding box produced an empty crop.", details={"bounding_box": bounding_box})
        cropped = img.crop((x1, y1, x2, y2))
        processor, model = self.trocr
        pixels = processor(images=cropped, return_tensors="pt").pixel_values.to(self.trocr_device)
        generated = model.generate(pixels)
        text = processor.batch_decode(generated, skip_special_tokens=True)[0]
        return {"text": text.strip(), "confidence": 0.6, "source_engine": "trocr"}
