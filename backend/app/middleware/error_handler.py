import uuid

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

class DocumentSystemException(Exception):
    """Base exception class for document extraction system"""
    default_code = "document_system_error"

    def __init__(self, message: str, status_code: int = 500, details: dict = None, code: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.code = code or self.default_code
        super().__init__(self.message)

class StorageException(DocumentSystemException):
    """Raised when file storage operations fail"""
    default_code = "storage_error"

class PreprocessingException(DocumentSystemException):
    """Raised when CV preprocessing operations fail"""
    default_code = "preprocessing_error"

class OCRException(DocumentSystemException):
    """Raised when OCR engine fails"""
    default_code = "ocr_error"

class ExtractionException(DocumentSystemException):
    """Raised when template/schema extraction fails"""
    default_code = "extraction_error"

class ConflictException(DocumentSystemException):
    default_code = "conflict"

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=409, details=details)

class ValidationException(DocumentSystemException):
    default_code = "validation_error"

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message, status_code=status_code, details=details)

async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    if isinstance(exc, DocumentSystemException):
        logger.warning(
            "Domain error request_id={} code={} status={} message={}",
            request_id, exc.code, exc.status_code, exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            }
        )
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "request_id": request_id,
            }},
        )
    logger.exception(f"Unhandled exception request_id={request_id}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {
            "code": "internal_error",
            "message": "An unexpected error occurred on the server.",
            "details": {},
            "request_id": request_id,
        }},
    )
