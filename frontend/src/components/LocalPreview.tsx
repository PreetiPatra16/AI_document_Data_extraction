import { useState } from 'react';
import { ChevronLeft, ChevronRight, RotateCw, ZoomIn, ZoomOut } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.js', import.meta.url).toString();

export function LocalPreview({ url, mimeType, filename }: { url?: string; mimeType: string; filename: string }) {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);

  if (!url) {
    return (
      <div className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center dark:border-slate-700 dark:bg-slate-900">
        <div>
          <p className="font-bold text-slate-700 dark:text-slate-200">Preview unavailable after refresh</p>
          <p className="mt-1 text-xs text-slate-500">The source file is intentionally not retained. Upload it again to preview or reprocess it.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-3 text-white">
        <span className="max-w-[260px] truncate text-xs font-bold">{filename}</span>
        <div className="flex items-center gap-2">
          {mimeType === 'application/pdf' && (
            <>
              <button onClick={() => setPage((value) => Math.max(1, value - 1))} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></button>
              <span className="text-[11px] font-bold">{page}/{pages}</span>
              <button onClick={() => setPage((value) => Math.min(pages, value + 1))} aria-label="Next page"><ChevronRight className="h-4 w-4" /></button>
            </>
          )}
          <button onClick={() => setScale((value) => Math.max(.5, value - .2))} aria-label="Zoom out"><ZoomOut className="h-4 w-4" /></button>
          <span className="w-10 text-center text-[11px] font-bold">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale((value) => Math.min(2.5, value + .2))} aria-label="Zoom in"><ZoomIn className="h-4 w-4" /></button>
          <button onClick={() => setRotation((value) => (value + 90) % 360)} aria-label="Rotate preview"><RotateCw className="h-4 w-4" /></button>
        </div>
      </div>
      <div className="flex h-[520px] items-start justify-center overflow-auto p-5">
        {mimeType === 'application/pdf' ? (
          <Document file={url} onLoadSuccess={({ numPages }) => setPages(numPages)} loading={<p className="text-sm text-slate-400">Loading PDF preview...</p>}>
            <Page pageNumber={page} scale={scale} rotate={rotation} renderTextLayer={false} renderAnnotationLayer={false} />
          </Document>
        ) : (
          <img src={url} alt={filename} className="max-w-none rounded-lg" style={{ transform: `scale(${scale}) rotate(${rotation}deg)`, transformOrigin: 'top center' }} />
        )}
      </div>
    </div>
  );
}
