import { BatchItem } from '../types';
import { buildBatchExport, validateFile } from './files';

describe('file validation', () => {
  it('accepts supported files and rejects unsupported or oversized files', () => {
    expect(validateFile(new File(['pdf'], 'claim.pdf', { type: 'application/pdf' }))).toBeNull();
    expect(validateFile(new File(['zip'], 'claim.zip', { type: 'application/zip' }))?.code).toBe('unsupported_file_type');
    const large = new File(['x'], 'large.png', { type: 'image/png' });
    Object.defineProperty(large, 'size', { value: 51 * 1024 * 1024 });
    expect(validateFile(large)?.code).toBe('file_too_large');
  });
});

describe('batch export', () => {
  it('includes completed and failed outcomes', () => {
    const items = [
      { localId: '1', filename: 'one.pdf', size: 1, mimeType: 'application/pdf', status: 'COMPLETED', progress: 100, document: { status: 'COMPLETED', extracted_data: { fields: {} } } },
      { localId: '2', filename: 'two.pdf', size: 1, mimeType: 'application/pdf', status: 'FAILED', progress: 20, error: { status: 500, code: 'ocr_failed', message: 'OCR failed', details: {}, requestId: 'r1' } },
    ] as unknown as BatchItem[];
    const result = buildBatchExport(items);
    expect(result.summary).toMatchObject({ total: 2, completed: 1, failed: 1 });
    expect(result.documents[1].failure_code).toBe('ocr_failed');
  });
});
