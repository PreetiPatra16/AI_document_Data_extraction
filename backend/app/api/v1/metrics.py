from fastapi import APIRouter, Depends

from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService

router = APIRouter()


@router.get("")
async def metrics(storage: StorageService = Depends(get_storage_service)):
    documents = storage.get_all_document_records()
    return {
        "documents_total": len(documents),
        "queue_depth": storage.queue_depth(),
        "completed_total": sum(1 for item in documents if item["status"] == "COMPLETED"),
        "failed_total": sum(1 for item in documents if item["status"] == "FAILED"),
    }
