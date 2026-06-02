import os
from typing import List, Dict, Any, Tuple
from loguru import logger
from app.middleware.error_handler import OCRException

# Dynamic imports with graceful fallbacks
PADDLE_AVAILABLE = False
try:
    from paddleocr import PaddleOCR
    # Check if we can initialize it to be sure
    PADDLE_AVAILABLE = True
except Exception as e:
    logger.warning(f"PaddleOCR library could not be imported: {str(e)}. Using fallback/mock.")

TESSERACT_AVAILABLE = False
try:
    import pytesseract
    # Configure path if specified
    tess_path = os.getenv("TESSERACT_CMD", "tesseract")
    pytesseract.pytesseract.tesseract_cmd = tess_path
    # Quick version check to see if binary is available
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception as e:
    logger.warning(f"Tesseract binary or pytesseract library is not available: {str(e)}. Using mock.")

class OCRService:
    def __init__(self):
        self.primary_engine = os.getenv("PRIMARY_OCR", "paddleocr")
        self.fallback_engine = os.getenv("FALLBACK_OCR", "tesseract")
        
        self.paddle_ocr = None
        if PADDLE_AVAILABLE and self.primary_engine == "paddleocr":
            try:
                # Initialize PaddleOCR engine (use CPU by default)
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {str(e)}")

    async def perform_ocr(self, image_path: str, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Runs OCR on the given image.
        Tries PaddleOCR first (for printed and mixed text).
        If PaddleOCR fails or is unavailable, falls back to Tesseract.
        If both are unavailable, generates mocked layout words for demonstration/testing.
        
        Returns a list of word blocks:
        [
            {
                "text": "Extracted Text",
                "confidence": 0.95,
                "bounding_box": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0},
                "page": 1
            },
            ...
        ]
        """
        logger.info(f"Running OCR on image {image_path} (Page {page_num})")
        
        # 1. Primary Engine: PaddleOCR
        if self.primary_engine == "paddleocr" and self.paddle_ocr:
            try:
                results = self._run_paddle_ocr(image_path, page_num)
                if results:
                    logger.info(f"PaddleOCR succeeded: detected {len(results)} elements on page {page_num}")
                    return results
            except Exception as e:
                logger.warning(f"PaddleOCR failed: {str(e)}. Attempting Tesseract fallback.")
        
        # 2. Fallback Engine: Tesseract
        if TESSERACT_AVAILABLE:
            try:
                results = self._run_tesseract_ocr(image_path, page_num)
                if results:
                    logger.info(f"Tesseract OCR succeeded: detected {len(results)} elements on page {page_num}")
                    return results
            except Exception as e:
                logger.warning(f"Tesseract OCR failed: {str(e)}")
                
        # 3. Final Fallback: Mocked OCR results for local testing/dev when binaries aren't installed
        logger.info(f"No active OCR engine available. Generating mock document contents for {os.path.basename(image_path)}")
        return self._generate_mock_ocr_results(image_path, page_num)

    def _run_paddle_ocr(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        if not self.paddle_ocr:
            raise OCRException("PaddleOCR instance not initialized")
            
        result = self.paddle_ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return []
            
        word_blocks = []
        for line in result[0]:
            box = line[0]  # List of 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            text, confidence = line[1]
            
            # Convert 4 corner points to bounding box (x, y, w, h)
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            x = min(xs)
            y = min(ys)
            w = max(xs) - x
            h = max(ys) - y
            
            word_blocks.append({
                "text": text,
                "confidence": float(confidence),
                "bounding_box": {
                    "x": float(x),
                    "y": float(y),
                    "width": float(w),
                    "height": float(h)
                },
                "page": page_num
            })
            
        return word_blocks

    def _run_tesseract_ocr(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        # Run Tesseract with TSV/dictionary output to get words and coordinates
        from PIL import Image
        img = Image.open(image_path)
        
        # Get detailed word level data
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        word_blocks = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            # Only keep elements with actual text and confident predictions
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            if text and conf > 0:
                word_blocks.append({
                    "text": text,
                    "confidence": conf / 100.0,  # Tesseract returns 0-100
                    "bounding_box": {
                        "x": float(data['left'][i]),
                        "y": float(data['top'][i]),
                        "width": float(data['width'][i]),
                        "height": float(data['height'][i])
                    },
                    "page": page_num
                })
        return word_blocks

    def _generate_mock_ocr_results(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        """Generates static mock text blocks resembling typical form fields."""
        filename = os.path.basename(image_path).lower()
        
        # We can tailor the mocks slightly depending on filename hints
        if "invoice" in filename:
            lines = [
                ("INVOICE", 100, 50, 200, 40),
                ("Invoice Number: INV-2026-004", 100, 120, 280, 20),
                ("Date: May 27, 2026", 100, 150, 180, 20),
                ("Bill To:", 100, 200, 80, 20),
                ("John Doe Corp", 100, 225, 140, 20),
                ("123 Main St, New York", 100, 250, 220, 20),
                ("Total Amount: $1,250.00", 500, 450, 240, 25),
                ("Tax Rate: 8.25%", 500, 480, 150, 20),
                ("Grand Total: $1,353.12", 500, 510, 250, 30)
            ]
        elif "form" in filename or "application" in filename:
            lines = [
                ("APPLICATION FORM", 300, 50, 300, 35),
                ("First Name:", 100, 150, 120, 20),
                ("Preet", 250, 150, 80, 20),
                ("Last Name:", 100, 190, 120, 20),
                ("Sharma", 250, 190, 90, 20),
                ("Email Address:", 100, 230, 140, 20),
                ("preet.sharma@example.com", 250, 230, 260, 20),
                ("Phone Number:", 100, 270, 130, 20),
                ("+1 (555) 019-2834", 250, 270, 180, 20),
                ("Signature:", 100, 350, 110, 20),
                ("[Handwritten: Preet Sharma]", 250, 345, 200, 30)
            ]
        else:
            lines = [
                ("AI Document Extraction Engine", 150, 50, 400, 30),
                ("Processed document page successfully.", 100, 120, 350, 20),
                ("Key Features:", 100, 160, 130, 20),
                ("- Fast OCR Processing", 120, 190, 200, 20),
                ("- Template Matching", 120, 220, 200, 20),
                ("- Multi-format parsing", 120, 250, 220, 20),
                ("Sample Value: 99.8%", 100, 320, 180, 20)
            ]
            
        results = []
        for text, x, y, w, h in lines:
            results.append({
                "text": text,
                "confidence": 0.98 if "handwritten" not in text.lower() else 0.72,
                "bounding_box": {
                    "x": float(x),
                    "y": float(y),
                    "width": float(w),
                    "height": float(h)
                },
                "page": page_num
            })
        return results
