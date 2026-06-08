import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_ingestion_service, get_storage_service
from app.core.services.ingestion_service import IngestionService
from app.core.services.storage_service import StorageService
from app.schemas.upload import UploadResponse

router = APIRouter()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    document_id = str(uuid.uuid4())
    filename, source_path, size, page_count, file_type = await ingestion.save_and_validate(file, document_id)
    try:
        storage.create_document_record(document_id, filename, file_type, size, page_count, source_path)
    except Exception:
        ingestion.cleanup_document_files(document_id)
        raise
    return UploadResponse(
        document_id=document_id,
        filename=filename,
        status="UPLOADED",
        message="File uploaded and validated. Extraction can be queued.",
    )
