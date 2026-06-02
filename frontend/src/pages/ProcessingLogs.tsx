import React from 'react';
import { useDocumentStore } from '../store/documentStore';
import { Header } from '../components/Header';
import { Terminal, Code, CheckCircle, AlertTriangle } from 'lucide-react';

export const ProcessingLogs: React.FC = () => {
  const { documents } = useDocumentStore();

  // Consolidate logs from all documents
  const allLogs = documents.flatMap((doc) =>
    doc.logs.map((log) => ({
      ...log,
      docId: doc.id,
      filename: doc.filename
    }))
  ).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl mx-auto">
      <Header
        title="Processing Terminal"
        description="Unified logging stream aggregated from active worker processes."
      />

      <div className="bg-slate-950 border border-slate-900 rounded-3xl overflow-hidden shadow-2xl flex flex-col font-mono text-xs text-slate-350">
        {/* Terminal Header */}
        <div className="bg-slate-900 px-6 py-4 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400">
            <Terminal className="h-4.5 w-4.5 text-brand-500 animate-pulse" />
            <span className="font-bold uppercase tracking-wider text-[11px]">System Event Stream</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-500 text-[10px] font-bold">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Listening</span>
          </div>
        </div>

        {/* Terminal Output */}
        <div className="p-6 overflow-auto max-h-[550px] space-y-4 select-text leading-relaxed">
          {allLogs.length === 0 ? (
            <div className="text-center py-16 text-slate-500 space-y-2">
              <Code className="h-8 w-8 mx-auto text-slate-650" />
              <p className="font-semibold text-xs">Terminal is empty.</p>
              <p className="text-[10px] font-medium text-slate-600">Trigger extraction on files to populate logging streams.</p>
            </div>
          ) : (
            allLogs.map((log, index) => {
              const dateStr = new Date(log.timestamp).toISOString();

              let levelColor = 'text-brand-400';
              let statusSymbol = '[INFO]';

              if (log.status === 'COMPLETED') {
                levelColor = 'text-emerald-400';
                statusSymbol = '[SUCCESS]';
              } else if (log.status === 'FAILED') {
                levelColor = 'text-rose-455';
                statusSymbol = '[ERROR]';
              } else if (log.status === 'PROCESSING') {
                levelColor = 'text-amber-400';
                statusSymbol = '[EXEC]';
              }

              return (
                <div key={index} className="space-y-0.5 border-b border-slate-900/60 pb-3 last:border-b-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-500 font-bold">{dateStr}</span>
                    <span className={`font-extrabold ${levelColor}`}>{statusSymbol}</span>
                    <span className="text-slate-400 font-extrabold underline truncate max-w-[150px] cursor-pointer" title={log.filename}>
                      {log.filename}
                    </span>
                  </div>
                  <div className="pl-4 text-slate-300 font-semibold">
                    {log.stage}: {log.details}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
