from pydantic import BaseModel

from app.core.domain import DocumentStatus


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody
