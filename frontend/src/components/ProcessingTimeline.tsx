import { CheckCircle2, Circle, XCircle } from 'lucide-react';
import { ProcessingEvent } from '../types';

export function ProcessingTimeline({ logs }: { logs: ProcessingEvent[] }) {
  if (!logs.length) return <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-950">No processing events have been recorded yet.</p>;
  return (
    <ol className="space-y-4">
      {logs.map((log, index) => (
        <li key={`${log.timestamp}-${index}`} className="flex gap-3">
          {log.status === 'FAILED' ? <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" /> : log.status === 'COMPLETED' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-extrabold capitalize">{log.stage}</p>
              <span className="text-[10px] font-bold text-slate-400">{log.progress}% · {new Date(log.timestamp).toLocaleString()}</span>
            </div>
            {log.details && <p className="mt-1 text-xs text-slate-500">{log.details}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
