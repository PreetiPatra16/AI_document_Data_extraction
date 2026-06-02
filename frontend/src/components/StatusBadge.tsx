import React from 'react';

interface StatusBadgeProps {
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const styles = {
    PENDING: {
      bg: 'bg-indigo-50 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-400 border-indigo-200/50 dark:border-indigo-900/30',
      label: 'Queued',
      dot: 'bg-indigo-400'
    },
    PROCESSING: {
      bg: 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-200/50 dark:border-amber-900/30 animate-pulse',
      label: 'Extracting',
      dot: 'bg-amber-400 animate-ping'
    },
    COMPLETED: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-900/30',
      label: 'Success',
      dot: 'bg-emerald-400'
    },
    FAILED: {
      bg: 'bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-200/50 dark:border-rose-900/30',
      label: 'Failed',
      dot: 'bg-rose-400'
    }
  };

  const currentStyle = styles[status] || styles.PENDING;

  return (
    <span className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${currentStyle.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${currentStyle.dot}`} />
      <span>{currentStyle.label}</span>
    </span>
  );
};
