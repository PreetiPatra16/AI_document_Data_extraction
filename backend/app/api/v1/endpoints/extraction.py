from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import ExtractionTriggerResponse

from fastapi import BackgroundTasks
from app.core.workers.extraction_worker import ExtractionWorker


router = APIRouter()

@router.post("/{document_id}")
async def trigger_extraction(
    document_id: str,
    background_tasks: BackgroundTasks,
    storage: StorageService = Depends(get_storage_service)
):
    job = storage.create_job(document_id)

    worker = ExtractionWorker()
    background_tasks.add_task(worker.run_once)

    return ExtractionTriggerResponse(
        job_id=job["id"],
        document_id=document_id,
        status="PROCESSING",
        message="Extraction started."
    )
