from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService
from app.schemas.document import JobResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, storage: StorageService = Depends(get_storage_service)):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
