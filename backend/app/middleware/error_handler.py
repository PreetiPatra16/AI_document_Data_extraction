from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger
import traceback

class DocumentSystemException(Exception):
    """Base exception class for document extraction system"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class StorageException(DocumentSystemException):
    """Raised when file storage operations fail"""
    pass

class PreprocessingException(DocumentSystemException):
    """Raised when CV preprocessing operations fail"""
    pass

class OCRException(DocumentSystemException):
    """Raised when OCR engine fails"""
    pass

class ExtractionException(DocumentSystemException):
    """Raised when template/schema extraction fails"""
    pass

async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, DocumentSystemException):
        logger.warning(f"Domain Error: {exc.message} - Status: {exc.status_code} - Details: {exc.details}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    # Generic unhandled exception
    tb = traceback.format_exc()
    logger.error(f"Unhandled Exception: {str(exc)}\n{tb}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred on the server.",
                "details": {"info": str(exc)} if request.app.debug else {}
            }
        }
    )
