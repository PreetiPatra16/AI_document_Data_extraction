from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import ExtractionTriggerResponse

router = APIRouter()


@router.post(
    "/{document_id}",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_extraction(
    document_id: str,
    storage: StorageService = Depends(get_storage_service),
):
    job = storage.create_job(document_id)
    return ExtractionTriggerResponse(
        job_id=job["id"],
        document_id=document_id,
        status=job["status"],
        message="Extraction queued.",
    )
