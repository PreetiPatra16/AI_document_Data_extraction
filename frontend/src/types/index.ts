export type DocumentStatus = 'UPLOADED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type BatchItemStatus = 'STAGED' | 'UPLOADING' | DocumentStatus | 'CANCELLED';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExtractedField {
  value: unknown;
  normalized_value: unknown;
  confidence: number;
  bounding_box: BoundingBox | null;
  page: number | null;
  raw_text: string | null;
  source_engine: string | null;
  review_required: boolean;
}

export interface ExtractedTable {
  name: string;
  page: number;
  rows: Record<string, unknown>[];
  confidence: number;
}

export interface ExtractionData {
  schema_version: string;
  document_type: string;
  confidence_summary: number;
  review_required: boolean;
  fields: Record<string, ExtractedField>;
  tables: ExtractedTable[];
  warnings: string[];
  raw_text?: string;
  paragraphs?: string[];
}

export interface ProcessingEvent {
  stage: string;
  status: string;
  progress: number;
  timestamp: string;
  details: string;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  status: DocumentStatus;
  current_stage: string | null;
  progress: number;
  uploaded_at: string;
  updated_at: string;
  extracted_data: ExtractionData | null;
  logs: ProcessingEvent[];
  processing_time_ms: number | null;
  failure_code: string | null;
  failure_message: string | null;
  source_available: boolean;
}

export interface JobRecord {
  id: string;
  document_id: string;
  status: JobStatus;
  stage: string | null;
  progress: number;
  attempts: number;
  max_attempts: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  failure_code: string | null;
  failure_message: string | null;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  message: string;
}

export interface ExtractionTriggerResponse {
  job_id: string;
  document_id: string;
  status: JobStatus;
  message: string;
}

export interface HealthResponse {
  status: string;
  uptime_seconds: number;
  database_connected: boolean;
  storage_writable: boolean;
  dependencies: Record<string, boolean>;
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready';
  dependencies: Record<string, boolean>;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export interface AppError {
  status: number | null;
  code: string;
  message: string;
  details: Record<string, unknown>;
  requestId: string | null;
}

export interface BatchItem {
  localId: string;
  filename: string;
  size: number;
  mimeType: string;
  file?: File;
  previewUrl?: string;
  documentId?: string;
  jobId?: string;
  status: BatchItemStatus;
  stage?: string | null;
  progress: number;
  document?: DocumentRecord;
  error?: AppError;
  previewLost?: boolean;
}
