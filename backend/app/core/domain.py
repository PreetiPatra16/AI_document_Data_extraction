from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PipelineStage(str, Enum):
    VALIDATION = "validation"
    RENDERING = "rendering"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    CLEANUP = "cleanup"


class FailureCode(str, Enum):
    VALIDATION_FAILED = "validation_failed"
    SOURCE_FILE_MISSING = "source_file_missing"
    RENDERING_FAILED = "rendering_failed"
    OCR_UNAVAILABLE = "ocr_unavailable"
    OCR_FAILED = "ocr_failed"
    CLASSIFICATION_FAILED = "classification_failed"
    EXTRACTION_FAILED = "extraction_failed"
    STORAGE_FAILED = "storage_failed"
    JOB_TIMEOUT = "job_timeout"
    INTERNAL_ERROR = "internal_error"


ACTIVE_JOB_STATUSES = (JobStatus.QUEUED.value, JobStatus.PROCESSING.value)
TERMINAL_JOB_STATUSES = (JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value)

DOCUMENT_TRANSITIONS = {
    DocumentStatus.UPLOADED: {DocumentStatus.QUEUED, DocumentStatus.FAILED},
    DocumentStatus.QUEUED: {DocumentStatus.PROCESSING, DocumentStatus.FAILED},
    DocumentStatus.PROCESSING: {DocumentStatus.COMPLETED, DocumentStatus.FAILED},
    DocumentStatus.COMPLETED: set(),
    DocumentStatus.FAILED: set(),
}

