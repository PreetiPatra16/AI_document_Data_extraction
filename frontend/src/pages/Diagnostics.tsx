import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { API_BASE_URL, apiService, parseApiError } from '../services/api';

export function Diagnostics() {
  const health = useQuery({ queryKey: ['health'], queryFn: apiService.checkHealth });
  const readiness = useQuery({ queryKey: ['readiness'], queryFn: apiService.checkReadiness });
  const refresh = () => { health.refetch(); readiness.refetch(); };
  const error = health.error ? parseApiError(health.error) : null;

  return (
    <div>
      <PageHeader title="Local service diagnostics" description="Live backend readiness and dependency checks. These values come directly from the local API." actions={<button className="button-secondary" onClick={refresh}><RefreshCw className={`h-4 w-4 ${health.isFetching ? 'animate-spin' : ''}`} /> Refresh</button>} />
      {error && <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-700 dark:border-rose-900 dark:bg-rose-950/20"><p className="font-extrabold">{error.message}</p><p className="mt-1 text-xs">API: {API_BASE_URL}{error.requestId ? ` · Request ID: ${error.requestId}` : ''}</p></div>}
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card p-6">
          <h2 className="font-extrabold">Service status</h2>
          <div className="mt-5 space-y-3 text-sm">
            <DiagnosticRow label="Health" value={health.data?.status ?? 'Unavailable'} ok={health.data?.status === 'ok'} />
            <DiagnosticRow label="Readiness" value={readiness.data?.status ?? 'Unavailable'} ok={readiness.data?.status === 'ready'} />
            <DiagnosticRow label="Database" value={health.data?.database_connected ? 'Connected' : 'Unavailable'} ok={Boolean(health.data?.database_connected)} />
            <DiagnosticRow label="Temporary storage" value={health.data?.storage_writable ? 'Writable' : 'Unavailable'} ok={Boolean(health.data?.storage_writable)} />
            <div className="flex justify-between border-t border-slate-100 pt-3 dark:border-slate-800"><span className="font-bold text-slate-500">Uptime</span><span className="font-extrabold">{health.data ? `${Math.round(health.data.uptime_seconds)}s` : '—'}</span></div>
          </div>
        </section>
        <section className="card p-6">
          <h2 className="font-extrabold">Local dependencies</h2>
          <div className="mt-5 space-y-3 text-sm">
            {Object.entries(readiness.data?.dependencies ?? health.data?.dependencies ?? {}).map(([name, available]) => <DiagnosticRow key={name} label={name} value={available ? 'Available' : 'Unavailable'} ok={available} />)}
            {!readiness.data && !health.data && <p className="text-sm text-slate-500">Dependency status is unavailable.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

function DiagnosticRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3 last:border-0 dark:border-slate-800"><span className="font-bold capitalize text-slate-500">{label.replace(/_/g, ' ')}</span><span className={`flex items-center gap-2 font-extrabold ${ok ? 'text-emerald-600' : 'text-rose-600'}`}>{ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}{value}</span></div>;
}
