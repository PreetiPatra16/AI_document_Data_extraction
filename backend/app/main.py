import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load Environment Variables from file if exists
load_dotenv()

from app.utils.logger import setup_logger
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_handler import global_exception_handler, DocumentSystemException
from app.api.v1.endpoints import upload, extraction, document
from app.api.v1.endpoints import jobs
from app.api.v1 import health, metrics
from app.core.config import settings

# 1. Setup Loguru custom logging
setup_logger()

# 2. FastAPI instance
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Scalable system to extract structured JSON data from mixed content locally.",
    debug=not settings.production
)

# 3. CORS configuration
origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Custom Middlewares
app.add_middleware(LoggingMiddleware)

# 5. Centralized Error Handlers
app.add_exception_handler(DocumentSystemException, global_exception_handler)
app.add_exception_handler(HTTPException, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {
            "code": "request_validation_failed",
            "message": "Request validation failed.",
            "details": {"errors": exc.errors()},
            "request_id": getattr(request.state, "request_id", ""),
        }},
    )

# 6. Route registration
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(extraction.router, prefix="/api/v1/extract", tags=["Extraction"])
app.include_router(document.router, prefix="/api/v1/document", tags=["Documents"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])

@app.get("/")
async def root():
    return {
        "app": app.title,
        "version": app.version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
