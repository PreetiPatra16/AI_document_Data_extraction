import React from 'react';
import { Eye, ExternalLink } from 'lucide-react';

interface PdfViewerProps {
  url: string;
  filename: string;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({ url, filename }) => {
  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-inner relative group">
      {/* Top action bar */}
      <div className="bg-slate-950 px-4 py-3 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center space-x-2 text-slate-350">
          <Eye className="h-4 w-4 text-brand-500" />
          <span className="text-xs font-bold truncate max-w-[200px]">{filename}</span>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-slate-400 hover:text-white transition-colors text-xs font-semibold flex items-center space-x-1"
        >
          <span>Open Direct</span>
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
      
      {/* File Embed */}
      <div className="flex-1 w-full h-[500px]">
        <embed
          src={`${url}#toolbar=0&navpanes=0&scrollbar=0`}
          type="application/pdf"
          className="w-full h-full border-none"
        />
      </div>
    </div>
  );
};
