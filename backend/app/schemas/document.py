from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.domain import DocumentStatus, JobStatus


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ExtractedField(BaseModel):
    value: Any = None
    normalized_value: Any = None
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    page: Optional[int] = None
    raw_text: Optional[str] = None
    source_engine: Optional[str] = None
    review_required: bool = False


class ExtractedTable(BaseModel):
    name: str
    page: int
    rows: List[Dict[str, Any]]
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionData(BaseModel):
    schema_version: str = "1.0"
    document_type: str
    confidence_summary: float = Field(ge=0.0, le=1.0)
    review_required: bool
    fields: Dict[str, ExtractedField]
    tables: List[ExtractedTable] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
    paragraphs: Optional[List[str]] = None


class ProcessingEvent(BaseModel):
    stage: str
    status: str
    progress: int = Field(ge=0, le=100)
    timestamp: datetime
    details: str = ""


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    page_count: int
    status: DocumentStatus
    current_stage: Optional[str] = None
    progress: int = 0
    uploaded_at: datetime
    updated_at: datetime
    extracted_data: Optional[ExtractionData] = None
    logs: List[ProcessingEvent] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    source_available: bool = True


class JobResponse(BaseModel):
    id: str
    document_id: str
    status: JobStatus
    stage: Optional[str] = None
    progress: int = 0
    attempts: int = 0
    max_attempts: int = 2
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None


class ExtractionTriggerResponse(BaseModel):
    job_id: str
    document_id: str
    status: JobStatus
    message: str
