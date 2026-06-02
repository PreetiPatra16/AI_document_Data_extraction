import os
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple
from loguru import logger
from app.middleware.error_handler import PreprocessingException

# pdf2image might raise an exception if poppler is not installed, so handle it gracefully
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image library not installed or poppler not available. PDF conversion will be mocked.")

class PreprocessingService:
    def __init__(self):
        self.temp_dir = os.getenv("TEMP_DIR", "temp_uploads")

    async def preprocess_document(self, file_path: str) -> List[str]:
        """
        Ingests a PDF or image, converts pages to images, preprocesses them using OpenCV,
        and saves preprocessed images for OCR. Returns a list of paths to preprocessed images.
        """
        logger.info(f"Starting preprocessing pipeline for file: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        
        page_images: List[Tuple[np.ndarray, int]] = []
        
        # 1. Image ingestion & PDF conversion
        if ext == ".pdf":
            page_images = await self._convert_pdf_to_images(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            img = cv2.imread(file_path)
            if img is None:
                raise PreprocessingException(f"Failed to read image at path: {file_path}")
            page_images = [(img, 1)]
        else:
            raise PreprocessingException(f"Unsupported file format: {ext}")
            
        preprocessed_paths = []
        
        # 2. Core Image Preprocessing (CV)
        for idx, (img, page_num) in enumerate(page_images):
            try:
                # Base operations: Grayscale, Denoising, Deskewing, Adaptive Thresholding
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # A. Denoise
                denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
                
                # B. Deskew
                deskewed = self._deskew_image(denoised)
                
                # C. Adaptive Thresholding
                thresholded = cv2.adaptiveThreshold(
                    deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
                
                # D. Morphological Operations (Optional, let's keep text crisp)
                # We can perform a slight dilation/erosion if needed for handwritten lines, 
                # but Adaptive Threshold is typically sufficient for primary PaddleOCR.
                
                # E. Save preprocessed image page
                base_name = os.path.basename(file_path).split('.')[0]
                target_path = os.path.join(self.temp_dir, f"preprocessed_{base_name}_page_{page_num}.png")
                cv2.imwrite(target_path, thresholded)
                
                logger.info(f"Page {page_num} preprocessed and saved: {target_path}")
                preprocessed_paths.append(target_path)
            except Exception as e:
                logger.error(f"Failed preprocessing page {page_num}: {str(e)}")
                raise PreprocessingException(f"Failed to preprocess page {page_num}: {str(e)}")
                
        return preprocessed_paths

    async def _convert_pdf_to_images(self, pdf_path: str) -> List[Tuple[np.ndarray, int]]:
        """Converts PDF pages to OpenCV matrices."""
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("PDF conversion using pdf2image is unavailable (poppler missing). Mocking PDF pages.")
            # Mock return a single blank white image
            blank_img = np.ones((1100, 850, 3), dtype=np.uint8) * 255
            return [(blank_img, 1)]
            
        try:
            images = convert_from_path(pdf_path)
            page_images = []
            for i, img in enumerate(images):
                # Convert PIL image to OpenCV format (BGR)
                open_cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                page_images.append((open_cv_image, i + 1))
            return page_images
        except Exception as e:
            logger.error(f"Error during pdf2image conversion: {str(e)}")
            # Fail gracefully with a descriptive error
            raise PreprocessingException(f"Failed to convert PDF pages: {str(e)}")

    def _deskew_image(self, img: np.ndarray) -> np.ndarray:
        """Calculates deskew angle and rotates image if necessary."""
        try:
            # Threshold the image to make text stand out
            _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find coordinates of all white pixels (the text)
            coords = np.column_stack(np.where(thresh > 0))
            
            # Get the minimum bounding box around all text pixels
            angle = cv2.minAreaRect(coords)[-1]
            
            # Adjust angle depending on rotation orientation
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            # If the angle is very small, do not rotate
            if abs(angle) < 0.5 or abs(angle) > 20:
                return img
                
            logger.info(f"Deskewing image by angle: {angle:.2f} degrees")
            
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception as e:
            logger.warning(f"Deskewing failed (skipping): {str(e)}")
            return img
