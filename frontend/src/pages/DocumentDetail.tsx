import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, Download, FileJson, ListTree, ScrollText } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { ExtractionPanel } from '../components/ExtractionPanel';
import { PageHeader } from '../components/PageHeader';
import { ProcessingTimeline } from '../components/ProcessingTimeline';
import { StatusBadge } from '../components/StatusBadge';
import { apiService, parseApiError } from '../services/api';
import { documentDownloadPayload, downloadJson, formatBytes } from '../utils/files';
import { ExtractionData } from '../types';

function FullTextPanel({ data }: { data: ExtractionData }) {
  const paragraphs = data.paragraphs ?? (data.raw_text ? data.raw_text.split('\n\n') : []);
  const confidence = Math.round(data.confidence_summary * 100);

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-900/60 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-wider text-slate-500">Document type</p>
          <p className="mt-1 font-extrabold text-slate-900 dark:text-white capitalize">{data.document_type.replace(/_/g, ' ')}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-extrabold">{confidence}%</p>
          <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500">OCR confidence</p>
        </div>
      </section>

      {data.review_required && (
        <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-800 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          OCR of handwritten text may contain errors — verify against the original document.
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h3 className="font-extrabold">Transcribed text</h3>
          <p className="text-xs text-slate-500">{paragraphs.length} paragraph{paragraphs.length !== 1 ? 's' : ''} detected</p>
        </div>
        <div className="px-6 py-6 space-y-5">
          {paragraphs.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No text could be extracted.</p>
          ) : (
            paragraphs.map((para, i) => (
              <p key={i} className="text-sm leading-7 text-slate-800 dark:text-slate-200 font-serif">
                {para}
              </p>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export function DocumentDetail() {
  const { documentId = '' } = useParams();
  const [tab, setTab] = useState<'fields' | 'text' | 'json' | 'events'>('fields');
  const documentQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => apiService.getDocument(documentId),
    refetchInterval: (query) => ['UPLOADED', 'QUEUED', 'PROCESSING'].includes(query.state.data?.status ?? '') ? 1500 : false,
  });
  const documentType = documentQuery.data?.extracted_data?.document_type;

  useEffect(() => {
    setTab(documentType === 'free_text_document' ? 'text' : 'fields');
  }, [documentId, documentType]);

  if (documentQuery.isLoading) return <p className="p-12 text-center text-sm text-slate-500">Loading document...</p>;
  if (!documentQuery.data) {
    const error = parseApiError(documentQuery.error);
    return <div className="rounded-2xl bg-rose-50 p-6 text-rose-700"><p className="font-extrabold">{error.message}</p>{error.requestId && <p className="mt-1 text-xs">Request ID: {error.requestId}</p>}</div>;
  }
  const record = documentQuery.data;

  return (
    <div>
      <PageHeader title={record.filename} description={`Retained extraction record · ${formatBytes(record.file_size)} · ${record.page_count} page${record.page_count === 1 ? '' : 's'}`} actions={
        <>
          <StatusBadge status={record.status} />
          {record.extracted_data && <button className="button-primary" onClick={() => downloadJson(`${record.filename}.json`, documentDownloadPayload(record))}><Download className="h-4 w-4" /> Download JSON</button>}
        </>
      } />
      <Link to="/history" className="mb-5 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 hover:text-brand-600"><ArrowLeft className="h-4 w-4" /> Back to history</Link>

      {record.status === 'FAILED' && <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-5 dark:border-rose-900 dark:bg-rose-950/20"><p className="font-extrabold text-rose-800 dark:text-rose-300">{record.failure_message ?? 'Extraction failed.'}</p><p className="mt-1 text-xs font-bold text-rose-600">{record.failure_code} · Upload the source again to retry.</p></div>}
      {['UPLOADED', 'QUEUED', 'PROCESSING'].includes(record.status) && <div className="mb-5 rounded-2xl border border-brand-200 bg-brand-50 p-5 dark:border-brand-900 dark:bg-brand-950/20"><div className="flex justify-between text-sm font-extrabold"><span className="capitalize">{record.current_stage ?? record.status.toLowerCase()}</span><span>{record.progress}%</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-white dark:bg-slate-900"><div className="h-full bg-brand-500" style={{ width: `${record.progress}%` }} /></div></div>}

      <div className="mb-5 flex flex-wrap gap-2">
        {record.extracted_data?.document_type !== 'free_text_document' && (
          <button className={tab === 'fields' ? 'button-primary' : 'button-secondary'} onClick={() => setTab('fields')}>Extracted fields</button>
        )}
        {record.extracted_data?.raw_text && (
          <button className={tab === 'text' ? 'button-primary' : 'button-secondary'} onClick={() => setTab('text')}><ScrollText className="h-4 w-4" /> Full text</button>
        )}
        <button className={tab === 'json' ? 'button-primary' : 'button-secondary'} onClick={() => setTab('json')}><FileJson className="h-4 w-4" /> JSON</button>
        <button className={tab === 'events' ? 'button-primary' : 'button-secondary'} onClick={() => setTab('events')}><ListTree className="h-4 w-4" /> Processing events</button>
      </div>

      {tab === 'fields' && (record.extracted_data ? <ExtractionPanel data={record.extracted_data} /> : <div className="card p-10 text-center text-sm text-slate-500">Extraction results are not available yet.</div>)}
      {tab === 'text' && record.extracted_data && <FullTextPanel data={record.extracted_data} />}
      {tab === 'json' && <pre className="max-h-[700px] overflow-auto rounded-2xl bg-slate-950 p-5 text-xs text-slate-200">{JSON.stringify(record.extracted_data, null, 2)}</pre>}
      {tab === 'events' && <div className="card p-5"><ProcessingTimeline logs={record.logs} /></div>}
    </div>
  );
}
