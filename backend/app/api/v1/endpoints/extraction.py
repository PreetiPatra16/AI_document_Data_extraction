import os
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from loguru import logger
from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import ExtractionTriggerResponse
from app.core.workers.extraction_worker import run_extraction_pipeline

router = APIRouter()

@router.post("/{document_id}", response_model=ExtractionTriggerResponse)
async def trigger_extraction(
    document_id: str,
    background_tasks: BackgroundTasks,
    storage: StorageService = Depends(get_storage_service)
):
    """
    Triggers the asynchronous extraction pipeline for a previously uploaded document.
    """
    logger.info(f"Triggering extraction pipeline for ID: {document_id}")
    
    # 1. Fetch document record
    doc = storage.get_document_record(document_id)
    if not doc:
        logger.warning(f"Document {document_id} not found in DB")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Check if the file is in temp uploads directory
    temp_dir = storage.temp_dir
    ext = os.path.splitext(doc["filename"])[1]
    file_path = os.path.join(temp_dir, f"{document_id}{ext}")
    
    if not os.path.exists(file_path):
        logger.error(f"Physical file for document {document_id} missing at path: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source file missing from temporary storage. Please re-upload."
        )
        
    # 2. Add pipeline task to background runner
    storage.update_document_record(document_id, status="PROCESSING")
    background_tasks.add_task(run_extraction_pipeline, document_id, file_path)
    
    return ExtractionTriggerResponse(
        document_id=document_id,
        status="PROCESSING",
        message="Extraction pipeline kicked off in background."
    )
