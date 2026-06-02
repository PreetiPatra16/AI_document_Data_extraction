from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

class ExtractedField(BaseModel):
    value: Any
    confidence: float = Field(..., description="Calculated confidence score between 0.0 and 1.0")
    bounding_box: Optional[BoundingBox] = None
    page: int = 1
    raw_text: Optional[str] = None

class DocumentBase(BaseModel):
    filename: str
    file_type: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    logs: Optional[List[Dict[str, Any]]] = None
    processing_time_ms: Optional[int] = None

class DocumentResponse(DocumentBase):
    id: str
    status: str
    uploaded_at: datetime
    extracted_data: Optional[Dict[str, Any]] = None
    logs: Optional[List[Dict[str, Any]]] = None
    processing_time_ms: Optional[int] = None

    class Config:
        from_attributes = True

class ExtractionTriggerResponse(BaseModel):
    document_id: str
    status: str
    message: str
