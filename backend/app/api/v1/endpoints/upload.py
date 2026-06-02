import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from loguru import logger
from app.api.dependencies import get_storage_service
from app.schemas.upload import UploadResponse
from app.core.services.storage_service import StorageService

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Uploads a scanned document or PDF, saves it securely to temp storage,
    and creates a placeholder record in the database.
    """
    logger.info(f"File upload request received: {file.filename}")
    
    # 1. Validate file extension
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Unsupported file upload extension attempted: {ext}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    try:
        # Generate a unique document UUID
        doc_id = str(uuid.uuid4())
        
        # Read file contents and write to temporary directory
        content = await file.read()
        file_path = await storage.save_uploaded_file(doc_id, file.filename, content)
        
        # Create SQLite database record
        storage.create_document_record(
            doc_id=doc_id,
            filename=file.filename,
            file_type=file.content_type or "application/octet-stream"
        )
        
        return UploadResponse(
            document_id=doc_id,
            filename=file.filename,
            status="PENDING",
            message="File uploaded successfully. Extraction can be triggered."
        )
    except Exception as e:
        logger.error(f"Error during file upload handling: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File saving failed: {str(e)}"
        )
