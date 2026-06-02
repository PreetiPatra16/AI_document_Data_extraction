import time
import os
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from loguru import logger
from app.api.dependencies import get_storage_service
from app.core.services.storage_service import StorageService

router = APIRouter()

START_TIME = time.time()

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    database_connected: bool
    storage_writable: bool

@router.get("", response_model=HealthResponse)
async def check_health(storage: StorageService = Depends(get_storage_service)):
    """Simple API status and connection validation check."""
    logger.info("Health check endpoint accessed.")
    
    # 1. Database Connection check
    db_connected = False
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            db_connected = True
    except Exception as e:
        logger.error(f"Health Check: Database connection failed: {str(e)}")
        
    # 2. Check Storage write access
    storage_writable = False
    try:
        test_file = os.path.join(storage.storage_dir, ".health_check_test")
        with open(test_file, "w") as f:
            f.write("OK")
        os.remove(test_file)
        storage_writable = True
    except Exception as e:
        logger.error(f"Health Check: Storage write test failed: {str(e)}")
        
    overall_status = "ok" if (db_connected and storage_writable) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        uptime_seconds=time.time() - START_TIME,
        database_connected=db_connected,
        storage_writable=storage_writable
    )
