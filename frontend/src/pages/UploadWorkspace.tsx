import React, { useState } from 'react';
import { UploadZone } from '../components/UploadZone';
import { Header } from '../components/Header';
import { apiService } from '../services/api';
import { useDocumentStore } from '../store/documentStore';
import { FileCode, AlertCircle, ArrowRight, Play } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadWorkspaceProps {
  setCurrentPage: (page: string) => void;
}

export const UploadWorkspace: React.FC<UploadWorkspaceProps> = ({ setCurrentPage }) => {
  const { addDocument, setActiveDocument } = useDocumentStore();
  const [uploadedDoc, setUploadedDoc] = useState<{ id: string; filename: string } | null>(null);
  const [triggering, setTriggering] = useState(false);

  const handleUploadSuccess = async (docId: string, filename: string) => {
    // 1. Fetch newly created doc record from DB to update local state
    try {
      const docRecord = await apiService.getDocument(docId);
      addDocument(docRecord);
      setUploadedDoc({ id: docId, filename });
    } catch (err) {
      console.error("Failed to load uploaded document metadata", err);
    }
  };

  const handleTriggerExtraction = async () => {
    if (!uploadedDoc) return;
    setTriggering(true);
    try {
      // Trigger the background worker pipeline
      await apiService.triggerExtraction(uploadedDoc.id);
      
      // Fetch latest document status
      const updatedDoc = await apiService.getDocument(uploadedDoc.id);
      setActiveDocument(updatedDoc);
      
      // Navigate to results page to watch extraction live
      setCurrentPage('results');
    } catch (err) {
      console.error("Extraction start failed", err);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl mx-auto">
      <Header
        title="Ingestion Workspace"
        description="Drag-and-drop form documents to stage them onto local storage."
      />

      <div className="bg-white/50 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800/60 p-8 rounded-3xl backdrop-blur-md">
        {!uploadedDoc ? (
          <div className="space-y-6">
            <div className="text-center space-y-1">
              <h3 className="font-extrabold text-slate-850 dark:text-slate-200 text-lg">
                Upload Scanned Target
              </h3>
              <p className="text-xs font-semibold text-slate-450 dark:text-slate-500">
                Staged files are kept securely inside the local host container context.
              </p>
            </div>
            <UploadZone
              uploadFile={apiService.uploadDocument}
              onUploadSuccess={handleUploadSuccess}
            />
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center p-8 space-y-6"
          >
            <div className="mx-auto w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-500 flex items-center justify-center border border-emerald-200/50">
              <FileCode className="h-8 w-8" />
            </div>
            
            <div className="space-y-1">
              <h3 className="text-lg font-extrabold text-slate-800 dark:text-slate-200">
                Document Uploaded & Verified
              </h3>
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 font-mono">
                {uploadedDoc.filename} ({uploadedDoc.id})
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <button
                onClick={() => setUploadedDoc(null)}
                className="px-5 py-3 border border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-850 text-slate-655 font-bold text-xs rounded-xl transition-all w-full sm:w-auto"
              >
                Reset Upload
              </button>
              
              <button
                onClick={handleTriggerExtraction}
                disabled={triggering}
                className="px-6 py-3 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-brand-500/25 transition-all inline-flex items-center justify-center space-x-2 w-full sm:w-auto"
              >
                {triggering ? (
                  <span>Booting Pipeline...</span>
                ) : (
                  <>
                    <span>Trigger AI Pipeline</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};
