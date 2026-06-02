import React, { useEffect, useState, useRef } from 'react';
import { useDocumentStore } from '../store/documentStore';
import { apiService } from '../services/api';
import { Header } from '../components/Header';
import { PdfViewer } from '../components/PdfViewer';
import { ImageViewer } from '../components/ImageViewer';
import { ExtractionPanel } from '../components/ExtractionPanel';
import { JsonViewer } from '../components/JsonViewer';
import { ProcessingTimeline } from '../components/ProcessingTimeline';
import { StatusBadge } from '../components/StatusBadge';
import { Play, RotateCw, FileCode, Sliders, Layers, AlertTriangle } from 'lucide-react';

export const ExtractionResults: React.FC = () => {
  const { documents, activeDocument, setActiveDocument, updateDocumentInStore } = useDocumentStore();
  const [activeTab, setActiveTab] = useState<'fields' | 'json'>('fields');
  const [retrying, setRetrying] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Poll active document details if status is PROCESSING
  useEffect(() => {
    if (activeDocument && activeDocument.status === 'PROCESSING') {
      const poll = async () => {
        try {
          const freshDoc = await apiService.getDocument(activeDocument.id);
          updateDocumentInStore(activeDocument.id, freshDoc);
          if (freshDoc.status !== 'PROCESSING') {
            if (pollingRef.current) clearInterval(pollingRef.current);
          }
        } catch (err) {
          console.error("Error polling document status", err);
        }
      };

      // Set up interval for every 1.5 seconds
      pollingRef.current = setInterval(poll, 1500);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [activeDocument, updateDocumentInStore]);

  const handleRetry = async () => {
    if (!activeDocument) return;
    setRetrying(true);
    try {
      await apiService.triggerExtraction(activeDocument.id);
      const freshDoc = await apiService.getDocument(activeDocument.id);
      setActiveDocument(freshDoc);
      updateDocumentInStore(activeDocument.id, freshDoc);
    } catch (err) {
      console.error("Retry trigger failed", err);
    } finally {
      setRetrying(false);
    }
  };

  const handleDocChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = documents.find((doc) => doc.id === e.target.value);
    if (selected) setActiveDocument(selected);
  };

  const isPdf = activeDocument?.filename.toLowerCase().endsWith('.pdf');
  
  // We'll point back to the local backend URL for direct preview.
  // Note: we can mock URLs or serve them if backend mounts files. 
  // For safety, we can point to a mock placeholder if localhost access fails.
  const previewUrl = activeDocument 
    ? `http://localhost:8000/api/v1/document/${activeDocument.id}/raw` 
    : '';

  return (
    <div className="space-y-6 animate-fade-in">
      <Header
        title="Inspection Center"
        description="Verify extracted elements side-by-side with original scanned assets."
        actions={
          <div className="flex items-center space-x-3">
            <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase">Active Record:</span>
            <select
              value={activeDocument?.id || ''}
              onChange={handleDocChange}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-bold focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="" disabled>-- Select Document --</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.status})
                </option>
              ))}
            </select>
          </div>
        }
      />

      {!activeDocument ? (
        <div className="p-16 text-center space-y-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-white/50 dark:bg-slate-900/50">
          <div className="mx-auto w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
            <Layers className="h-6 w-6" />
          </div>
          <div className="max-w-sm mx-auto space-y-1">
            <h4 className="font-bold text-slate-700 dark:text-slate-350 text-sm">Select a Target</h4>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500">
              Pick a document from the dropdown above or upload one in the workspace to view extraction detail.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Left Side: Document Preview */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Original Attachment
              </span>
              <StatusBadge status={activeDocument.status} />
            </div>
            
            <div className="h-[550px]">
              {isPdf ? (
                <PdfViewer url={previewUrl} filename={activeDocument.filename} />
              ) : (
                <ImageViewer url={previewUrl} filename={activeDocument.filename} />
              )}
            </div>
          </div>

          {/* Right Side: Process Info / Tabs */}
          <div className="space-y-4">
            {activeDocument.status === 'PROCESSING' && (
              <div className="space-y-4">
                <span className="text-xs font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                  Pipeline Status
                </span>
                <ProcessingTimeline logs={activeDocument.logs} status={activeDocument.status} />
              </div>
            )}

            {activeDocument.status === 'FAILED' && (
              <div className="bg-rose-50/10 border border-rose-200/50 dark:border-rose-950/20 p-6 rounded-2xl space-y-4">
                <div className="flex items-start space-x-3 text-rose-800 dark:text-rose-455">
                  <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-sm">Pipeline Execution Halted</h4>
                    <p className="text-xs font-medium mt-1">
                      The extraction engine threw an error during execution. Refer to the logs timeline below.
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleRetry}
                  disabled={retrying}
                  className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-lg shadow-rose-600/20 transition-all flex items-center space-x-2"
                >
                  <RotateCw className={`h-4 w-4 ${retrying ? 'animate-spin' : ''}`} />
                  <span>Retry Extraction</span>
                </button>
                
                <ProcessingTimeline logs={activeDocument.logs} status={activeDocument.status} />
              </div>
            )}

            {activeDocument.status === 'PENDING' && (
              <div className="bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 p-8 rounded-2xl text-center space-y-4">
                <h4 className="font-bold text-slate-700 dark:text-slate-350 text-sm">Ready for Processing</h4>
                <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 max-w-xs mx-auto">
                  Document has been stored in temp storage but extraction is not triggered yet.
                </p>
                <button
                  onClick={handleRetry}
                  disabled={retrying}
                  className="px-5 py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-bold text-xs rounded-xl shadow-lg shadow-brand-500/25 transition-all inline-flex items-center space-x-2 mx-auto"
                >
                  <Play className="h-4 w-4" />
                  <span>Run Extraction</span>
                </button>
              </div>
            )}

            {activeDocument.status === 'COMPLETED' && activeDocument.extracted_data && (
              <div className="space-y-4">
                {/* Tab Switchers */}
                <div className="bg-slate-100 dark:bg-slate-900/60 p-1.5 rounded-2xl flex space-x-2 border border-slate-200/40 dark:border-slate-800/40 w-fit">
                  <button
                    onClick={() => setActiveTab('fields')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
                      activeTab === 'fields'
                        ? 'bg-white dark:bg-slate-800 text-slate-800 dark:text-white shadow-sm'
                        : 'text-slate-500 dark:text-slate-450 hover:text-slate-800'
                    }`}
                  >
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Audited Fields</span>
                  </button>
                  
                  <button
                    onClick={() => setActiveTab('json')}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
                      activeTab === 'json'
                        ? 'bg-white dark:bg-slate-800 text-slate-800 dark:text-white shadow-sm'
                        : 'text-slate-500 dark:text-slate-450 hover:text-slate-800'
                    }`}
                  >
                    <FileCode className="h-3.5 w-3.5" />
                    <span>JSON Schema Output</span>
                  </button>
                </div>

                {/* Conditional views */}
                {activeTab === 'fields' ? (
                  <ExtractionPanel data={activeDocument.extracted_data} />
                ) : (
                  <div className="h-[450px]">
                    <JsonViewer data={activeDocument.extracted_data} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
