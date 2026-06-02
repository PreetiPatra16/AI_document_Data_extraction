import React from 'react';
import { useDocumentStore } from '../store/documentStore';
import { StatusBadge } from '../components/StatusBadge';
import { Header } from '../components/Header';
import { FileText, Cpu, CheckCircle2, ChevronRight, Activity, Calendar } from 'lucide-react';

interface DashboardProps {
  setCurrentPage: (page: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ setCurrentPage }) => {
  const { documents, setActiveDocument } = useDocumentStore();

  const handleViewDetails = (doc: any) => {
    setActiveDocument(doc);
    setCurrentPage('results');
  };

  // Compute analytics
  const total = documents.length;
  const processed = documents.filter((d) => d.status === 'COMPLETED').length;
  const processing = documents.filter((d) => d.status === 'PROCESSING').length;
  const failed = documents.filter((d) => d.status === 'FAILED').length;
  
  const successRate = total > 0 ? Math.round((processed / total) * 100) : 0;
  const avgTime = processed > 0 
    ? Math.round(documents.filter((d) => d.status === 'COMPLETED').reduce((acc, curr) => acc + (curr.processing_time_ms || 0), 0) / processed) 
    : 0;

  const stats = [
    { label: 'Total Ingested', value: total, icon: FileText, color: 'text-brand-500 bg-brand-50 dark:bg-brand-950/40 border-brand-200/50' },
    { label: 'Average Speed', value: `${avgTime}ms`, icon: Cpu, color: 'text-amber-500 bg-amber-50 dark:bg-amber-950/40 border-amber-200/50' },
    { label: 'Process Accuracy', value: `${successRate}%`, icon: CheckCircle2, color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200/50' },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      <Header
        title="Extraction Workspace"
        description="Local intelligence dashboard for high-volume document ingestion."
      />

      {/* Analytics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className={`p-6 border rounded-2xl flex items-center justify-between bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800/80 shadow-sm transition-all duration-300 hover:scale-[1.02]`}>
              <div className="space-y-1">
                <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                  {stat.label}
                </span>
                <span className="text-2xl font-extrabold text-slate-900 dark:text-white font-display">
                  {stat.value}
                </span>
              </div>
              <div className={`p-3.5 rounded-xl border ${stat.color}`}>
                <Icon className="h-6 w-6" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Document List */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 dark:border-slate-800/60 flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div className="space-y-0.5">
            <h3 className="font-extrabold text-slate-900 dark:text-white text-base">
              Recent Documents
            </h3>
            <p className="text-xs font-medium text-slate-500">
              Audit log listing all uploads processed locally by the engine.
            </p>
          </div>
          <button 
            onClick={() => setCurrentPage('upload')}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white font-bold text-xs rounded-xl shadow-lg shadow-brand-500/25 transition-all self-start sm:self-auto"
          >
            Upload Workspace
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="p-16 text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-slate-50 dark:bg-slate-850/60 flex items-center justify-center text-slate-450 border border-slate-200/40">
              <FileText className="h-7 w-7" />
            </div>
            <div className="space-y-1 max-w-sm mx-auto">
              <h4 className="font-bold text-slate-700 dark:text-slate-350 text-sm">No documents found</h4>
              <p className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                You haven't uploaded any documents to this workspace yet. Get started by uploading a scanned image or form.
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto select-none">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider bg-slate-50/50 dark:bg-slate-900/60">
                  <th className="px-6 py-4">Filename</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Uploaded At</th>
                  <th className="px-6 py-4">Processing Time</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-150/40 dark:divide-slate-800/40 text-xs">
                {documents.map((doc) => (
                  <tr 
                    key={doc.id}
                    className="hover:bg-slate-50/30 dark:hover:bg-slate-850/10 transition-colors"
                  >
                    <td className="px-6 py-4 font-bold text-slate-800 dark:text-slate-200 truncate max-w-[220px]">
                      {doc.filename}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-500 dark:text-slate-400">
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>{new Date(doc.uploaded_at).toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">
                      {doc.status === 'COMPLETED' ? `${doc.processing_time_ms}ms` : '--'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleViewDetails(doc)}
                        className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-350 transition-colors inline-flex items-center"
                      >
                        <span className="text-[11px] font-bold mr-1">Inspect</span>
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
