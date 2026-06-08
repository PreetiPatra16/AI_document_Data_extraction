import os
import shutil
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_ocr_service, get_storage_service
from app.core.config import settings
from app.core.services.ocr_service import OCRService
from app.core.services.storage_service import StorageService

router = APIRouter()
START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    database_connected: bool
    storage_writable: bool
    dependencies: dict


def _checks(storage: StorageService, ocr: OCRService):
    database = storage_writable = False
    try:
        with storage.get_connection() as conn:
            database = conn.execute("SELECT 1").fetchone()[0] == 1
        test_path = os.path.join(storage.storage_dir, ".health")
        with open(test_path, "w") as handle:
            handle.write("ok")
        os.remove(test_path)
        storage_writable = True
    except Exception:
        pass
    dependencies = {
        **ocr.capabilities(),
        "poppler": bool(shutil.which("pdftoppm") or shutil.which("pdfinfo")),
    }
    return database, storage_writable, dependencies


@router.get("", response_model=HealthResponse)
async def health(storage: StorageService = Depends(get_storage_service), ocr: OCRService = Depends(get_ocr_service)):
    database, writable, dependencies = _checks(storage, ocr)
    return HealthResponse(
        status="ok" if database and writable else "unhealthy",
        uptime_seconds=time.time() - START_TIME,
        database_connected=database,
        storage_writable=writable,
        dependencies=dependencies,
    )


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready(storage: StorageService = Depends(get_storage_service), ocr: OCRService = Depends(get_ocr_service)):
    database, writable, dependencies = _checks(storage, ocr)
    ready_value = database and writable and dependencies["tesseract"] and dependencies["poppler"]
    if settings.paddle_required:
        ready_value = ready_value and dependencies["paddleocr"]
    if settings.trocr_required:
        ready_value = ready_value and dependencies["trocr"]
    return {"status": "ready" if ready_value else "not_ready", "dependencies": dependencies}
