import React from 'react';
import { LayoutDashboard, UploadCloud, FileText, Terminal, Settings as SettingsIcon } from 'lucide-react';

interface SidebarProps {
  currentPage: string;
  setCurrentPage: (page: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, setCurrentPage }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Workspace', icon: UploadCloud },
    { id: 'results', label: 'Extraction Results', icon: FileText },
    { id: 'logs', label: 'Processing Logs', icon: Terminal },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 border-r border-slate-200/80 dark:border-slate-800/80 bg-white/50 dark:bg-slate-900/50 p-4 space-y-2 flex flex-col h-[calc(100vh-73px)]">
      <div className="flex-1 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 group ${
                isActive
                  ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/25 dark:shadow-none'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Icon className={`h-4.5 w-4.5 transition-transform group-hover:scale-110 ${
                isActive ? 'text-white' : 'text-slate-400 dark:text-slate-500 group-hover:text-brand-500 dark:group-hover:text-brand-400'
              }`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
      
      <div className="p-4 border-t border-slate-200/80 dark:border-slate-800/80 rounded-xl bg-slate-50/50 dark:bg-slate-900/40 text-center">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">Local Model Cache</span>
        <div className="w-full bg-slate-200 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
          <div className="bg-brand-500 h-full rounded-full w-[85%]" />
        </div>
        <span className="text-[10px] font-bold text-brand-600 dark:text-brand-400 mt-1 block">85% Loaded</span>
      </div>
    </aside>
  );
};
