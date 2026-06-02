import React from 'react';
import { useDocumentStore } from '../store/documentStore';
import { Sun, Moon, Sparkles, Server } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { darkMode, toggleDarkMode } = useDocumentStore();

  return (
    <nav className="glass sticky top-0 z-40 w-full border-b border-slate-200/80 dark:border-slate-800/80 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="bg-brand-500 text-white p-2 rounded-xl shadow-lg shadow-brand-500/30">
          <Sparkles className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <span className="font-extrabold text-lg bg-gradient-to-r from-brand-600 to-indigo-500 bg-clip-text text-transparent dark:from-brand-400 dark:to-indigo-300 font-display">
            DocuExtract AI
          </span>
          <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800 dark:bg-brand-900/50 dark:text-brand-300">
            v1.0 Local
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* API Status Indicator */}
        <div className="flex items-center space-x-2 text-xs bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 px-3 py-1.5 rounded-lg border border-emerald-200/50 dark:border-emerald-900/30">
          <Server className="h-3.5 w-3.5" />
          <span className="font-medium">Local Engine Online</span>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-500 dark:text-slate-400 transition-colors border border-slate-200/50 dark:border-slate-800/50"
          title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {darkMode ? <Sun className="h-5 w-5 text-yellow-500" /> : <Moon className="h-5 w-5" />}
        </button>
      </div>
    </nav>
  );
};
