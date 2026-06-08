from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import DocumentResponse

router = APIRouter()


@router.get("", response_model=List[DocumentResponse])
async def list_documents(storage: StorageService = Depends(get_storage_service)):
    return storage.get_all_document_records()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, storage: StorageService = Depends(get_storage_service)):
    document = storage.get_document_record(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, storage: StorageService = Depends(get_storage_service)):
    if not storage.get_document_record(document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    storage.delete_document_record(document_id)
