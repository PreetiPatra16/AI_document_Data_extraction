import { BatchItemStatus, JobStatus } from '../types';

export function StatusBadge({ status }: { status: BatchItemStatus | JobStatus }) {
  const styles: Record<string, string> = {
    STAGED: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    UPLOADING: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
    UPLOADED: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
    QUEUED: 'bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
    PROCESSING: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    COMPLETED: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    FAILED: 'bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
    CANCELLED: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider ${styles[status] ?? styles.STAGED}`}>{status}</span>;
}
