import React, { useState } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';

interface JsonViewerProps {
  data: any;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);
  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-950 border border-slate-900 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-full font-mono text-xs">
      {/* Title Bar */}
      <div className="bg-slate-900 px-4 py-3 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center space-x-2 text-slate-400">
          <Terminal className="h-4 w-4 text-emerald-500" />
          <span className="font-bold text-[11px] uppercase tracking-wider">output_results.json</span>
        </div>
        
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 text-slate-400 hover:text-white transition-colors py-1 px-2.5 rounded-lg hover:bg-slate-850"
          title="Copy JSON"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-[10px] text-emerald-400 font-bold">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold">Copy API</span>
            </>
          )}
        </button>
      </div>

      {/* Code Area */}
      <div className="flex-1 p-4 overflow-auto text-slate-350 select-text leading-relaxed max-h-[500px]">
        <pre className="whitespace-pre">{jsonString}</pre>
      </div>
    </div>
  );
};
