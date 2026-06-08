import { AlertTriangle, CheckCircle2, Table2 } from 'lucide-react';
import { ExtractionData } from '../types';

function label(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}

export function ExtractionPanel({ data }: { data: ExtractionData }) {
  return (
    <div className="space-y-5">
      <section className={`rounded-2xl border p-5 ${data.review_required ? 'border-amber-300 bg-amber-50/60 dark:border-amber-900 dark:bg-amber-950/20' : 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-900 dark:bg-emerald-950/20'}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-wider text-slate-500">Document type</p>
            <p className="mt-1 font-extrabold text-slate-900 dark:text-white">{label(data.document_type)}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-extrabold">{Math.round(data.confidence_summary * 100)}%</p>
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500">Overall confidence</p>
          </div>
        </div>
        {data.review_required && <p className="mt-4 flex items-center gap-2 text-xs font-bold text-amber-800 dark:text-amber-300"><AlertTriangle className="h-4 w-4" /> Review is recommended before using this result.</p>}
      </section>

      {data.warnings.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-amber-800 dark:text-amber-300">Extraction notices</h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-900 dark:text-amber-200">
            {data.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
          </ul>
        </section>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h3 className="font-extrabold">Extracted fields</h3>
          <p className="text-xs text-slate-500">Read-only values returned by the local extraction service.</p>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {Object.entries(data.fields).map(([name, field]) => {
            const value = field.normalized_value ?? field.value;
            return (
              <div key={name} className={`grid gap-3 px-5 py-4 sm:grid-cols-[minmax(150px,1fr)_2fr_auto] ${field.review_required ? 'bg-amber-50/70 dark:bg-amber-950/10' : ''}`}>
                <div>
                  <p className="text-xs font-extrabold uppercase tracking-wider text-slate-500">{label(name)}</p>
                  {field.page && <p className="mt-1 text-[10px] font-bold text-slate-400">Page {field.page}</p>}
                </div>
                <p className="break-words text-sm font-bold">{value === null || value === '' ? <span className="font-medium italic text-slate-400">Not detected</span> : String(value)}</p>
                <div className="flex items-center gap-2 text-xs font-extrabold">
                  {field.review_required ? <AlertTriangle className="h-4 w-4 text-amber-500" /> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                  {Math.round(field.confidence * 100)}%
                </div>
              </div>
            );
          })}
          {Object.keys(data.fields).length === 0 && <p className="px-5 py-8 text-center text-sm text-slate-500">No fields were extracted.</p>}
        </div>
      </section>

      {data.tables.map((table) => (
        <section key={`${table.name}-${table.page}`} className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <Table2 className="h-4 w-4 text-brand-500" />
            <h3 className="font-extrabold">{label(table.name)}</h3>
            <span className="text-xs text-slate-500">Page {table.page} · {Math.round(table.confidence * 100)}%</span>
          </div>
          <pre className="overflow-auto p-5 text-xs">{JSON.stringify(table.rows, null, 2)}</pre>
        </section>
      ))}
    </div>
  );
}
