import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Download, Eye, FilePlus2, Play, Trash2, X } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { Link } from 'react-router-dom';
import { LocalPreview } from '../components/LocalPreview';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { apiService, parseApiError } from '../services/api';
import { useDocumentStore } from '../store/documentStore';
import { BatchItem, DocumentRecord } from '../types';
import { runWithConcurrency } from '../utils/batch';
import { buildBatchExport, downloadJson, formatBytes, validateFile } from '../utils/files';

const sleep = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const activeStatuses = ['UPLOADING', 'UPLOADED', 'QUEUED', 'PROCESSING'];

async function pollJob(jobId: string, onProgress: (stage: string | null, progress: number, status: BatchItem['status']) => void) {
  let failures = 0;
  while (true) {
    try {
      const job = await apiService.getJob(jobId);
      failures = 0;
      onProgress(job.stage, job.progress, job.status === 'CANCELLED' ? 'CANCELLED' : job.status);
      if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status)) return job;
      await sleep(1500);
    } catch (error) {
      failures += 1;
      if (failures >= 5) throw error;
      await sleep(Math.min(1000 * 2 ** failures, 8000));
    }
  }
}

async function pollDocument(documentId: string, onProgress: (document: DocumentRecord) => void) {
  let failures = 0;
  while (true) {
    try {
      const document = await apiService.getDocument(documentId);
      failures = 0;
      onProgress(document);
      if (['COMPLETED', 'FAILED'].includes(document.status)) return document;
      await sleep(1500);
    } catch (error) {
      failures += 1;
      if (failures >= 5) throw error;
      await sleep(Math.min(1000 * 2 ** failures, 8000));
    }
  }
}

export function Workspace() {
  const { items, stageFiles, removeItem, updateItem, clearTerminalItems, recoverItems } = useDocumentStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const selected = items.find((item) => item.localId === selectedId) ?? items[0];

  const onDrop = (files: File[]) => {
    const errors = files.map(validateFile).filter(Boolean).map((error) => error!.message);
    const valid = files.filter((file) => !validateFile(file));
    setValidationErrors(errors);
    stageFiles(valid);
    if (!selectedId && valid.length) {
      setTimeout(() => {
        const current = useDocumentStore.getState().items;
        setSelectedId(current[current.length - valid.length]?.localId ?? null);
      });
    }
  };

  const dropzone = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    multiple: true,
  });

  const processItem = async (item: BatchItem) => {
    let documentId = item.documentId;
    try {
      if (!documentId) {
        if (!item.file) return;
        updateItem(item.localId, { status: 'UPLOADING', progress: 0, error: undefined });
        const upload = await apiService.uploadDocument(item.file, (progress) => updateItem(item.localId, { progress }));
        documentId = upload.document_id;
        updateItem(item.localId, { documentId, status: 'UPLOADED', progress: 100 });
      }
      const trigger = await apiService.triggerExtraction(documentId);
      updateItem(item.localId, { jobId: trigger.job_id, status: 'QUEUED', progress: 0 });
      await pollJob(trigger.job_id, (stage, progress, status) => updateItem(item.localId, { stage, progress, status }));
      const document = await apiService.getDocument(documentId);
      updateItem(item.localId, { document, status: document.status, stage: document.current_stage, progress: document.progress });
    } catch (error) {
      const appError = parseApiError(error);
      if (documentId) {
        try {
          const current = await apiService.getDocument(documentId);
          if (current.status === 'UPLOADED') {
            updateItem(item.localId, { document: current, status: current.status, stage: current.current_stage, progress: current.progress, error: appError });
            return;
          }
          const document = await pollDocument(documentId, (record) => updateItem(item.localId, { document: record, status: record.status, stage: record.current_stage, progress: record.progress, error: appError }));
          updateItem(item.localId, { document, status: document.status, stage: document.current_stage, progress: document.progress, error: appError });
          return;
        } catch {
          // Preserve the original actionable request error.
        }
      }
      updateItem(item.localId, { status: 'FAILED', error: appError });
    }
  };

  const startBatch = async () => {
    const pending = items.filter((item) => (item.status === 'STAGED' && item.file) || (item.status === 'UPLOADED' && item.documentId));
    if (!pending.length) return;
    setRunning(true);
    await runWithConcurrency(pending, 3, processItem);
    setRunning(false);
  };

  useEffect(() => {
    recoverItems();
    useDocumentStore.getState().items.filter((item) => item.documentId && activeStatuses.includes(item.status) && !item.file).forEach(async (item) => {
      try {
        let jobId = item.jobId;
        if (!jobId && item.status === 'UPLOADED') {
          const trigger = await apiService.triggerExtraction(item.documentId!);
          jobId = trigger.job_id;
          updateItem(item.localId, { jobId, status: 'QUEUED', progress: 0 });
        }
        if (jobId) {
          await pollJob(jobId, (stage, progress, status) => updateItem(item.localId, { stage, progress, status }));
        } else {
          await pollDocument(item.documentId!, (document) => updateItem(item.localId, { document, status: document.status, stage: document.current_stage, progress: document.progress, previewLost: true }));
        }
        const document = await apiService.getDocument(item.documentId!);
        updateItem(item.localId, { document, status: document.status, stage: document.current_stage, progress: document.progress, previewLost: true });
      } catch (error) {
        updateItem(item.localId, { error: parseApiError(error) });
      }
    });
  }, [recoverItems, updateItem]);

  const stats = useMemo(() => ({
    total: items.length,
    completed: items.filter((item) => item.status === 'COMPLETED').length,
    failed: items.filter((item) => item.status === 'FAILED').length,
    progress: items.length ? Math.round(items.reduce((sum, item) => sum + item.progress, 0) / items.length) : 0,
  }), [items]);

  return (
    <div>
      <PageHeader title="Extraction workspace" description="Stage a batch, inspect local previews, then process up to three documents at a time." actions={
        <>
          {items.some((item) => item.document || item.error) && <button onClick={() => downloadJson('extraction-batch.json', buildBatchExport(items))} className="button-secondary"><Download className="h-4 w-4" /> Export batch</button>}
          {items.some((item) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status)) && <button onClick={clearTerminalItems} className="button-secondary"><Trash2 className="h-4 w-4" /> Clear finished</button>}
          <button onClick={startBatch} disabled={running || !items.some((item) => item.status === 'STAGED' || item.status === 'UPLOADED')} className="button-primary"><Play className="h-4 w-4" /> {running ? 'Processing batch' : 'Start batch'}</button>
        </>
      } />

      {items.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[['Batch files', stats.total], ['Completed', stats.completed], ['Failed', stats.failed], ['Aggregate progress', `${stats.progress}%`]].map(([label, value]) => (
            <div key={label} className="card p-4"><p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-1 text-2xl font-extrabold">{value}</p></div>
          ))}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(420px,0.9fr)_minmax(520px,1.1fr)]">
        <section className="space-y-4">
          <div {...dropzone.getRootProps()} className={`cursor-pointer rounded-2xl border-2 border-dashed p-7 text-center transition ${dropzone.isDragActive ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20' : 'border-slate-300 bg-white hover:border-brand-400 dark:border-slate-700 dark:bg-slate-900'}`}>
            <input {...dropzone.getInputProps()} />
            <FilePlus2 className="mx-auto h-8 w-8 text-brand-500" />
            <p className="mt-3 font-extrabold">Add PDF, JPG, JPEG, or PNG files</p>
            <p className="mt-1 text-xs text-slate-500">Multiple files supported · 50 MB maximum per file</p>
          </div>
          {validationErrors.map((error) => <p key={error} className="flex gap-2 rounded-xl bg-rose-50 p-3 text-xs font-bold text-rose-700 dark:bg-rose-950/20 dark:text-rose-300"><AlertCircle className="h-4 w-4 shrink-0" />{error}</p>)}

          <div className="card overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800"><h2 className="font-extrabold">Batch queue</h2><p className="text-xs text-slate-500">Failures do not stop the remaining queue.</p></div>
            <div className="max-h-[600px] divide-y divide-slate-100 overflow-auto dark:divide-slate-800">
              {items.map((item) => (
                <button key={item.localId} onClick={() => setSelectedId(item.localId)} className={`block w-full p-4 text-left transition hover:bg-slate-50 dark:hover:bg-slate-950 ${selected?.localId === item.localId ? 'bg-brand-50/70 dark:bg-brand-950/20' : ''}`}>
                  <div className="flex items-start gap-3">
                    <Eye className="mt-1 h-4 w-4 shrink-0 text-slate-400" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3"><p className="truncate text-sm font-extrabold">{item.filename}</p><StatusBadge status={item.status} /></div>
                      <p className="mt-1 text-[11px] text-slate-500">{formatBytes(item.size)}{item.stage ? ` · ${item.stage}` : ''}</p>
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className={`h-full ${item.status === 'FAILED' ? 'bg-rose-500' : 'bg-brand-500'}`} style={{ width: `${item.progress}%` }} /></div>
                      {(item.document?.failure_message || item.error) && <p className="mt-2 text-xs font-bold text-rose-600">{item.document?.failure_message ?? item.error?.message}{item.error?.requestId ? ` · Request ${item.error.requestId}` : ''}</p>}
                    </div>
                    {item.status === 'STAGED' && <span onClick={(event) => { event.stopPropagation(); removeItem(item.localId); }} className="rounded-lg p-1 text-slate-400 hover:bg-slate-200" role="button" aria-label={`Remove ${item.filename}`}><X className="h-4 w-4" /></span>}
                  </div>
                </button>
              ))}
              {!items.length && <p className="p-10 text-center text-sm text-slate-500">Your batch queue is empty.</p>}
            </div>
          </div>
        </section>

        <section>
          {selected ? (
            <div className="space-y-4">
              <LocalPreview url={selected.previewUrl} mimeType={selected.mimeType} filename={selected.filename} />
              {selected.documentId && <Link to={`/documents/${selected.documentId}`} className="button-secondary w-full justify-center">Inspect retained result and events</Link>}
            </div>
          ) : <div className="grid min-h-[520px] place-items-center rounded-2xl border border-dashed border-slate-300 text-sm text-slate-500 dark:border-slate-700">Add a file to inspect its session preview.</div>}
        </section>
      </div>
    </div>
  );
}
