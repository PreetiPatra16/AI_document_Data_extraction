from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from loguru import logger
from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import DocumentResponse

router = APIRouter()

@router.get("", response_model=List[DocumentResponse])
async def list_documents(storage: StorageService = Depends(get_storage_service)):
    """Retrieves all uploaded documents and their current statuses."""
    logger.info("Listing all document records.")
    return storage.get_all_document_records()

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    storage: StorageService = Depends(get_storage_service)
):
    """Retrieves a single document record by UUID, including JSON results and logging timeline."""
    logger.info(f"Retrieving document record: {document_id}")
    doc = storage.get_document_record(document_id)
    if not doc:
        logger.warning(f"Document {document_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    storage: StorageService = Depends(get_storage_service)
):
    """Deletes a document record and associated assets."""
    logger.info(f"Request to delete document record: {document_id}")
    doc = storage.get_document_record(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    storage.delete_document_record(document_id)
    return None
