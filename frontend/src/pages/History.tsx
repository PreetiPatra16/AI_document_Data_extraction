import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Search, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { apiService, parseApiError } from '../services/api';
import { documentDownloadPayload, downloadJson, formatBytes } from '../utils/files';

export function History() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('ALL');
  const [selected, setSelected] = useState<string[]>([]);
  const documents = useQuery({ queryKey: ['documents'], queryFn: apiService.listDocuments, refetchInterval: 5000 });
  const deletion = useMutation({
    mutationFn: async (ids: string[]) => {
      if (!window.confirm(`Delete ${ids.length} retained document record${ids.length === 1 ? '' : 's'}?`)) return;
      await Promise.all(ids.map(apiService.deleteDocument));
    },
    onSuccess: () => {
      setSelected([]);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const filtered = useMemo(() => (documents.data ?? []).filter((document) =>
    document.filename.toLowerCase().includes(query.toLowerCase()) && (status === 'ALL' || document.status === status)
  ), [documents.data, query, status]);

  return (
    <div>
      <PageHeader title="Result history" description="Inspect and manage retained metadata and extraction results. Original source files are not retained." actions={
        selected.length ? <button className="button-danger" onClick={() => deletion.mutate(selected)}><Trash2 className="h-4 w-4" /> Delete selected ({selected.length})</button> : undefined
      } />
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_200px]">
        <label className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename" className="input pl-10" /></label>
        <select value={status} onChange={(event) => setStatus(event.target.value)} className="input">
          {['ALL', 'UPLOADED', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'].map((value) => <option key={value}>{value}</option>)}
        </select>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[850px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950">
            <tr><th className="p-4"><span className="sr-only">Select</span></th><th className="p-4">Document</th><th className="p-4">Status</th><th className="p-4">Uploaded</th><th className="p-4">Pages / size</th><th className="p-4">Processing</th><th className="p-4 text-right">Actions</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {filtered.map((document) => (
              <tr key={document.id} className="hover:bg-slate-50 dark:hover:bg-slate-950">
                <td className="p-4"><input type="checkbox" checked={selected.includes(document.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, document.id] : current.filter((id) => id !== document.id))} /></td>
                <td className="max-w-[260px] p-4"><Link to={`/documents/${document.id}`} className="block truncate font-extrabold hover:text-brand-600">{document.filename}</Link><span className="text-[10px] text-slate-400">{document.id}</span></td>
                <td className="p-4"><StatusBadge status={document.status} /></td>
                <td className="p-4 text-xs text-slate-500">{new Date(document.uploaded_at).toLocaleString()}</td>
                <td className="p-4 text-xs text-slate-500">{document.page_count} · {formatBytes(document.file_size)}</td>
                <td className="p-4 text-xs font-bold">{document.processing_time_ms ? `${(document.processing_time_ms / 1000).toFixed(1)}s` : `${document.progress}%`}</td>
                <td className="p-4"><div className="flex justify-end gap-1">{document.extracted_data && <button onClick={() => downloadJson(`${document.filename}.json`, documentDownloadPayload(document))} className="icon-button" aria-label={`Download ${document.filename}`}><Download className="h-4 w-4" /></button>}<button onClick={() => deletion.mutate([document.id])} className="icon-button text-rose-500" aria-label={`Delete ${document.filename}`}><Trash2 className="h-4 w-4" /></button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!documents.isLoading && !filtered.length && <p className="p-12 text-center text-sm text-slate-500">No matching retained documents.</p>}
      </div>
      {documents.error && <p className="mt-4 rounded-xl bg-rose-50 p-4 text-sm font-bold text-rose-700">{parseApiError(documents.error).message}</p>}
    </div>
  );
}
