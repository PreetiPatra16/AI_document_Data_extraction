import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load Environment Variables from file if exists
load_dotenv()

from app.utils.logger import setup_logger
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_handler import global_exception_handler, DocumentSystemException
from app.api.v1.endpoints import upload, extraction, document
from app.api.v1 import health

# 1. Setup Loguru custom logging
setup_logger()

# 2. FastAPI instance
app = FastAPI(
    title=os.getenv("API_TITLE", "AI Document Data Extraction API"),
    version=os.getenv("API_VERSION", "1.0.0"),
    description="Scalable system to extract structured JSON data from mixed content locally.",
    debug=os.getenv("API_ENV", "development") == "development"
)

# 3. CORS configuration
origins = ["*"]  # In production, specify allowed domains.
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
app.add_exception_handler(Exception, global_exception_handler)

# 6. Route registration
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(extraction.router, prefix="/api/v1/extract", tags=["Extraction"])
app.include_router(document.router, prefix="/api/v1/document", tags=["Documents"])

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
