import os
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from pdf2image import convert_from_path

from app.core.config import Settings, settings
from app.middleware.error_handler import PreprocessingException


class PreprocessingService:
    def __init__(self, config: Settings = settings):
        self.settings = config
        config.temp_dir.mkdir(parents=True, exist_ok=True)

    async def preprocess_document(self, file_path: str, document_id: str | None = None) -> List[Dict[str, Any]]:
        source = Path(file_path)
        doc_id = document_id or source.stem
        pages: List[Dict[str, Any]] = []
        if source.suffix.lower() == ".pdf":
            page_number = 1
            while True:
                try:
                    rendered = convert_from_path(
                        str(source), first_page=page_number, last_page=page_number, fmt="png", thread_count=1
                    )
                except Exception as exc:
                    raise PreprocessingException(f"Failed to render PDF page {page_number}.") from exc
                if not rendered:
                    break
                image = cv2.cvtColor(np.array(rendered[0]), cv2.COLOR_RGB2BGR)
                pages.append(self._create_variants(image, doc_id, page_number))
                page_number += 1
        else:
            image = cv2.imread(str(source))
            if image is None:
                raise PreprocessingException("Failed to decode source image.")
            pages.append(self._create_variants(image, doc_id, 1))
        if not pages:
            raise PreprocessingException("Document produced no renderable pages.")
        return pages

    def _create_variants(self, image: np.ndarray, document_id: str, page: int) -> Dict[str, Any]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        oriented = self._orient(gray)
        denoised = cv2.fastNlMeansDenoising(oriented, h=10, templateWindowSize=7, searchWindowSize=21)
        deskewed = self._deskew(denoised)
        thresholded = cv2.adaptiveThreshold(
            deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 9
        )
        variants = {"original": image, "grayscale": gray, "denoised": deskewed, "thresholded": thresholded}
        paths: Dict[str, str] = {}
        for name, variant in variants.items():
            path = self.settings.temp_dir / f"{document_id}_page_{page}_{name}.png"
            if not cv2.imwrite(str(path), variant):
                raise PreprocessingException(f"Failed to write {name} page variant.")
            paths[name] = str(path)
        laplacian = float(cv2.Laplacian(deskewed, cv2.CV_64F).var())
        contrast = float(deskewed.std())
        warnings = []
        if laplacian < 50:
            warnings.append("low_image_sharpness")
        if contrast < 25:
            warnings.append("low_image_contrast")
        return {
            "page": page,
            "variants": paths,
            "quality": {"sharpness": round(laplacian, 2), "contrast": round(contrast, 2)},
            "warnings": warnings,
        }

    def _orient(self, image: np.ndarray) -> np.ndarray:
        try:
            import pytesseract

            osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            rotation = int(osd.get("rotate", 0))
            # OSD misfires on photographed forms; only rotate on a confident reading.
            if float(osd.get("orientation_conf", 0.0)) < 2.5:
                return image
            if rotation == 90:
                return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            if rotation == 180:
                return cv2.rotate(image, cv2.ROTATE_180)
            if rotation == 270:
                return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        except Exception:
            pass
        return image

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        try:
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coordinates = np.column_stack(np.where(binary > 0))
            if len(coordinates) < 20:
                return image
            angle = cv2.minAreaRect(coordinates)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) < 0.4 or abs(angle) > 15:
                return image
            height, width = image.shape[:2]
            matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
            return cv2.warpAffine(
                image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
        except Exception:
            return image
