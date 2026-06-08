import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { apiService } from '../services/api';
import { DocumentRecord } from '../types';
import { DocumentDetail } from './DocumentDetail';

vi.mock('../services/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../services/api')>();
  return {
    ...original,
    apiService: {
      ...original.apiService,
      getDocument: vi.fn(),
    },
  };
});

const freeTextDocument: DocumentRecord = {
  id: 'doc-1',
  filename: 'handwritten.pdf',
  file_type: 'application/pdf',
  file_size: 100,
  page_count: 1,
  status: 'COMPLETED',
  current_stage: 'cleanup',
  progress: 100,
  uploaded_at: '2026-06-06T00:00:00Z',
  updated_at: '2026-06-06T00:00:01Z',
  extracted_data: {
    schema_version: '1.0',
    document_type: 'free_text_document',
    confidence_summary: 0.8,
    review_required: true,
    fields: {},
    tables: [],
    warnings: ['free_text_no_schema'],
    raw_text: 'A handwritten paragraph.',
    paragraphs: ['A handwritten paragraph.'],
  },
  logs: [],
  processing_time_ms: 1000,
  failure_code: null,
  failure_message: null,
  source_available: false,
};

describe('DocumentDetail', () => {
  it('renders completed free-text extraction results', async () => {
    vi.mocked(apiService.getDocument).mockResolvedValue(freeTextDocument);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/documents/doc-1']}>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('A handwritten paragraph.')).toBeInTheDocument();
    expect(screen.getByText('Transcribed text')).toBeInTheDocument();
  });
});
