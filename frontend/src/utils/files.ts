import { AppError, BatchItem, DocumentRecord } from '../types';

export const MAX_FILE_SIZE = 50 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png'];
const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];

export function validateFile(file: File): AppError | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!ACCEPTED_EXTENSIONS.includes(extension) || !ACCEPTED_TYPES.includes(file.type)) {
    return {
      status: 400,
      code: 'unsupported_file_type',
      message: 'Use a PDF, JPG, JPEG, or PNG file.',
      details: {},
      requestId: null,
    };
  }
  if (file.size > MAX_FILE_SIZE) {
    return {
      status: 413,
      code: 'file_too_large',
      message: 'File exceeds the 50 MB upload limit.',
      details: {},
      requestId: null,
    };
  }
  return null;
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function downloadJson(filename: string, data: unknown): void {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function buildBatchExport(items: BatchItem[]) {
  const documents = items
    .filter((item) => item.document || item.error)
    .map((item) => ({
      document_id: item.documentId ?? null,
      filename: item.filename,
      status: item.document?.status ?? item.status,
      failure_code: item.document?.failure_code ?? item.error?.code ?? null,
      failure_message: item.document?.failure_message ?? item.error?.message ?? null,
      extraction: item.document?.extracted_data ?? null,
    }));
  return {
    exported_at: new Date().toISOString(),
    summary: {
      total: documents.length,
      completed: documents.filter((doc) => doc.status === 'COMPLETED').length,
      failed: documents.filter((doc) => doc.status === 'FAILED').length,
    },
    documents,
  };
}

export function documentDownloadPayload(document: DocumentRecord) {
  return {
    document_id: document.id,
    filename: document.filename,
    status: document.status,
    extraction: document.extracted_data,
  };
}
