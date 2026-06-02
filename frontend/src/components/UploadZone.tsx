import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface UploadZoneProps {
  onUploadSuccess: (docId: string, filename: string) => void;
  onUploadStart?: () => void;
  uploadFile: (file: File) => Promise<any>;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess, onUploadStart, uploadFile }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    
    setIsUploading(true);
    setErrorMsg(null);
    setUploadProgress(10);
    
    if (onUploadStart) onUploadStart();

    // Mock progress update during upload phase
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => (prev < 90 ? prev + 15 : prev));
    }, 150);

    try {
      const response = await uploadFile(file);
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Delay response slightly so the user registers success state
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        onUploadSuccess(response.document_id, response.filename);
      }, 500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setIsUploading(false);
      setUploadProgress(0);
      setErrorMsg(err.response?.data?.detail || 'File upload failed. Ensure the server is online.');
    }
  }, [uploadFile, onUploadSuccess, onUploadStart]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    },
    multiple: false,
    disabled: isUploading
  });

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-3xl p-10 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 ${
          isDragActive 
            ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-950/20 scale-[1.01]' 
            : 'border-slate-300 dark:border-slate-800 hover:border-brand-400 dark:hover:border-brand-600 bg-white/50 dark:bg-slate-900/50'
        } ${isUploading ? 'pointer-events-none opacity-80' : ''}`}
      >
        <input {...getInputProps()} />
        
        <AnimatePresence mode="wait">
          {!isUploading && (
            <motion.div
              key="dropzone-idle"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="text-center space-y-4"
            >
              <div className="mx-auto w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-950/40 flex items-center justify-center text-brand-500 dark:text-brand-400">
                <UploadCloud className="h-8 w-8" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-bold text-slate-700 dark:text-slate-350">
                  {isDragActive ? "Drop the file here!" : "Drag & drop files here, or click to browse"}
                </p>
                <p className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  Supports scanned PDF, PNG, JPG, JPEG, TIFF, BMP (Max 25MB)
                </p>
              </div>
            </motion.div>
          )}

          {isUploading && (
            <motion.div
              key="dropzone-progress"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full text-center space-y-4"
            >
              <div className="mx-auto w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center animate-spin text-brand-500">
                <File className="h-6 w-6" />
              </div>
              <div className="space-y-2 max-w-xs mx-auto">
                <p className="text-sm font-bold text-slate-700 dark:text-slate-300">
                  Securing file on local host...
                </p>
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-brand-500 h-full rounded-full transition-all duration-300 ease-out" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <span className="text-xs font-bold text-brand-600 dark:text-brand-400">{uploadProgress}%</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {errorMsg && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-400 border border-rose-200/50 dark:border-rose-900/30 flex items-start space-x-3"
        >
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <span className="text-sm font-semibold block">Upload Failed</span>
            <span className="text-xs font-medium">{errorMsg}</span>
          </div>
        </motion.div>
      )}
    </div>
  );
};
