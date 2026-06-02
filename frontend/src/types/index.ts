export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExtractedField {
  value: any;
  confidence: number;
  bounding_box: BoundingBox | null;
  page: number;
  raw_text: string | null;
}

export interface ExtractionData {
  document_type: string;
  fields: Record<string, ExtractedField>;
  confidence_summary: number;
}

export interface ProcessingLog {
  stage: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  timestamp: string;
  details: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  uploaded_at: string;
  extracted_data: ExtractionData | null;
  logs: ProcessingLog[];
  processing_time_ms: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ExtractionTriggerResponse {
  document_id: string;
  status: string;
  message: string;
}

export interface HealthResponse {
  status: string;
  uptime_seconds: number;
  database_connected: boolean;
  storage_writable: boolean;
}
