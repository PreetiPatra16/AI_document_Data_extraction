import React from 'react';
import { ExtractionData } from '../types';
import { ShieldCheck, ShieldAlert, Award, FileSpreadsheet } from 'lucide-react';

interface ExtractionPanelProps {
  data: ExtractionData;
}

export const ExtractionPanel: React.FC<ExtractionPanelProps> = ({ data }) => {
  const getConfidenceLevel = (score: number) => {
    if (score >= 0.85) return { color: 'text-emerald-500 bg-emerald-500/10', bar: 'bg-emerald-500', text: 'High Confidence' };
    if (score >= 0.70) return { color: 'text-amber-500 bg-amber-500/10', bar: 'bg-amber-500', text: 'Medium Confidence' };
    return { color: 'text-rose-500 bg-rose-500/10', bar: 'bg-rose-500', text: 'Low Confidence / Review Required' };
  };

  const getCleanLabel = (str: string) => {
    return str
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const summaryLevel = getConfidenceLevel(data.confidence_summary);

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl p-6 shadow-sm space-y-6">
      {/* Title & Overall Score */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800/60">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <FileSpreadsheet className="h-5 w-5 text-brand-500" />
            <h3 className="font-extrabold text-slate-900 dark:text-white text-base">
              Extraction Audit
            </h3>
          </div>
          <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
            Classification: {data.document_type.toUpperCase()}
          </span>
        </div>
        
        <div className="text-right">
          <div className={`inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl text-xs font-bold ${summaryLevel.color}`}>
            <Award className="h-4 w-4" />
            <span>Score: {Math.round(data.confidence_summary * 100)}%</span>
          </div>
          <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 mt-1 uppercase">
            {summaryLevel.text}
          </span>
        </div>
      </div>

      {/* Field List */}
      <div className="space-y-4">
        {Object.entries(data.fields).map(([fieldName, field]) => {
          const fieldLevel = getConfidenceLevel(field.confidence);
          const isLow = field.confidence < 0.7;

          return (
            <div 
              key={fieldName} 
              className={`p-4 rounded-xl border transition-all duration-200 ${
                isLow 
                  ? 'border-rose-200/60 bg-rose-50/10 dark:border-rose-950/20' 
                  : 'border-slate-100 bg-slate-50/30 dark:border-slate-850/20 dark:border-slate-800/40 hover:bg-slate-50/50 dark:hover:bg-slate-850/40'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wider">
                    {getCleanLabel(fieldName)}
                  </span>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
                      {field.value !== null ? String(field.value) : <span className="text-slate-400 italic font-medium">Not detected</span>}
                    </span>
                    {field.page && (
                      <span className="text-[10px] font-bold bg-slate-200/50 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-500 dark:text-slate-400">
                        P.{field.page}
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-right">
                  <div className="flex items-center justify-end space-x-1 text-xs font-extrabold text-slate-700 dark:text-slate-350">
                    {isLow ? (
                      <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                    ) : (
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                    )}
                    <span>{Math.round(field.confidence * 100)}%</span>
                  </div>
                </div>
              </div>

              {/* Progress Slider */}
              <div className="w-full bg-slate-200/80 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden mb-2">
                <div 
                  className={`h-full rounded-full transition-all duration-300 ${fieldLevel.bar}`}
                  style={{ width: `${field.confidence * 100}%` }}
                />
              </div>

              {/* Debug raw text snippet if low confidence */}
              {isLow && field.raw_text && (
                <div className="mt-2 text-[10px] font-medium bg-rose-50 dark:bg-rose-950/20 text-rose-800 dark:text-rose-455 p-2 rounded-lg border border-rose-250/20">
                  <span className="font-bold block uppercase mb-0.5">Raw Text Bounding Anchor</span>
                  "{field.raw_text}"
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
