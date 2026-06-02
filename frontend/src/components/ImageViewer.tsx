import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize, RotateCw } from 'lucide-react';

interface ImageViewerProps {
  url: string;
  filename: string;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({ url, filename }) => {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);

  const handleZoomIn = () => setScale((s) => Math.min(s + 0.25, 3));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.25, 0.5));
  const handleRotate = () => setRotation((r) => (r + 90) % 360);
  const handleReset = () => {
    setScale(1);
    setRotation(0);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-inner relative group">
      {/* Zoom Controls */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-slate-950/90 border border-slate-800 backdrop-blur-md px-4 py-2 rounded-2xl flex items-center space-x-4 z-10 shadow-xl opacity-90 hover:opacity-100 transition-opacity">
        <button
          onClick={handleZoomOut}
          className="text-slate-400 hover:text-white transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="h-4.5 w-4.5" />
        </button>
        <span className="text-xs font-bold text-slate-300 w-12 text-center">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={handleZoomIn}
          className="text-slate-400 hover:text-white transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="h-4.5 w-4.5" />
        </button>
        <div className="w-px h-4 bg-slate-800" />
        <button
          onClick={handleRotate}
          className="text-slate-400 hover:text-white transition-colors"
          title="Rotate"
        >
          <RotateCw className="h-4.5 w-4.5" />
        </button>
        <button
          onClick={handleReset}
          className="text-slate-450 hover:text-white transition-colors text-[10px] font-bold uppercase tracking-wider"
        >
          Reset
        </button>
      </div>

      {/* Title Header */}
      <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex justify-between items-center">
        <span className="text-xs font-bold text-slate-350 truncate">{filename}</span>
        <div className="flex items-center space-x-1 text-slate-500 text-[10px] font-semibold">
          <Maximize className="h-3 w-3" />
          <span>Interactive Preview</span>
        </div>
      </div>

      {/* Image Display */}
      <div className="flex-1 w-full min-h-[400px] flex items-center justify-center overflow-auto p-6 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px]">
        <div
          style={{
            transform: `scale(${scale}) rotate(${rotation}deg)`,
            transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
          className="max-w-full max-h-[450px]"
        >
          <img
            src={url}
            alt={filename}
            className="rounded-lg shadow-2xl border border-slate-850 max-h-[400px] object-contain select-none pointer-events-none"
            onError={(e) => {
              // Graceful mock handling
              (e.target as HTMLImageElement).src = "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?auto=format&fit=crop&w=400&q=80";
            }}
          />
        </div>
      </div>
    </div>
  );
};
