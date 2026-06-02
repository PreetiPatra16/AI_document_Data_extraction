from app.core.services.storage_service import StorageService
from app.core.services.preprocessing_service import PreprocessingService
from app.core.services.ocr_service import OCRService
from app.core.services.extraction_service import ExtractionService

# Central dependency injection container
class Dependencies:
    def __init__(self):
        self.storage = StorageService()
        self.preprocessing = PreprocessingService()
        self.ocr = OCRService()
        self.extraction = ExtractionService()

# Singleton instance for simple DI
_deps = Dependencies()

def get_storage_service() -> StorageService:
    return _deps.storage

def get_preprocessing_service() -> PreprocessingService:
    return _deps.preprocessing

def get_ocr_service() -> OCRService:
    return _deps.ocr

def get_extraction_service() -> ExtractionService:
    return _deps.extraction
