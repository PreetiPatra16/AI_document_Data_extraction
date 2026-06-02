import React from 'react';
import { ProcessingLog } from '../types';
import { CheckCircle2, Clock, PlayCircle, XCircle } from 'lucide-react';

interface ProcessingTimelineProps {
  logs: ProcessingLog[];
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
}

export const ProcessingTimeline: React.FC<ProcessingTimelineProps> = ({ logs, status }) => {
  const getIcon = (logStatus: string) => {
    switch (logStatus) {
      case 'COMPLETED':
        return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
      case 'PROCESSING':
        return <PlayCircle className="h-5 w-5 text-amber-500 animate-spin" />;
      case 'FAILED':
        return <XCircle className="h-5 w-5 text-rose-500" />;
      default:
        return <Clock className="h-5 w-5 text-slate-400" />;
    }
  };

  const getLogTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  // If no logs, show a queued placeholder
  if (logs.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl p-6 text-center space-y-3">
        <Clock className="h-8 w-8 text-slate-400 mx-auto animate-pulse" />
        <div>
          <h4 className="font-bold text-slate-700 dark:text-slate-300 text-sm">Pipeline Queued</h4>
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500">Waiting for trigger instruction...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/60">
        <h3 className="font-extrabold text-slate-900 dark:text-white text-base">
          Pipeline Audit Logs
        </h3>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 uppercase">
          Live Tracker
        </span>
      </div>

      <div className="relative border-l border-slate-200 dark:border-slate-800 pl-6 ml-3 space-y-6">
        {logs.map((log, index) => {
          const isLast = index === logs.length - 1;
          const isFailed = log.status === 'FAILED';

          return (
            <div key={index} className="relative group">
              {/* Connector dot */}
              <div className="absolute -left-[37px] top-0.5 bg-white dark:bg-slate-950 p-1 rounded-full border border-slate-100 dark:border-slate-900">
                {getIcon(log.status)}
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-bold ${isFailed ? 'text-rose-600 dark:text-rose-455' : 'text-slate-800 dark:text-slate-200'}`}>
                    {log.stage}
                  </span>
                  <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                    {getLogTime(log.timestamp)}
                  </span>
                </div>
                
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {log.details}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
