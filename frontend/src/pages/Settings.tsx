import React, { useEffect, useState } from 'react';
import { useDocumentStore } from '../store/documentStore';
import { apiService } from '../services/api';
import { Header } from '../components/Header';
import { HealthResponse } from '../types';
import { Sliders, Sun, Moon, Cpu, Database, ServerCrash, RefreshCw } from 'lucide-react';

export const Settings: React.FC = () => {
  const { darkMode, toggleDarkMode } = useDocumentStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    try {
      const h = await apiService.checkHealth();
      setHealth(h);
    } catch {
      setHealth({
        status: 'unhealthy',
        uptime_seconds: 0,
        database_connected: false,
        storage_writable: false,
      });
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl mx-auto">
      <Header
        title="Settings & System Health"
        description="Configure local OCR preferences and monitor background engine status."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Card: Preferences */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 p-6 rounded-3xl space-y-6 shadow-sm">
          <div className="flex items-center space-x-2 pb-3 border-b border-slate-100 dark:border-slate-800/60">
            <Sliders className="h-5 w-5 text-brand-500" />
            <h3 className="font-extrabold text-slate-900 dark:text-white text-base">Preferences</h3>
          </div>

          <div className="space-y-4">
            {/* Dark Mode */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200 block">Theme Scheme</span>
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">Toggle dark mode visual setting.</span>
              </div>
              <button
                onClick={toggleDarkMode}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-850 rounded-xl text-xs font-bold transition-all flex items-center space-x-2"
              >
                {darkMode ? (
                  <>
                    <Sun className="h-4 w-4 text-yellow-500" />
                    <span>Light Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="h-4 w-4 text-slate-500" />
                    <span>Dark Mode</span>
                  </>
                )}
              </button>
            </div>

            {/* OCR Options Info */}
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800/60 space-y-3">
              <span className="text-sm font-bold text-slate-850 dark:text-slate-250 block">Local Engines Info</span>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/40 dark:border-slate-800/40 text-xs space-y-2">
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-slate-400">Primary Engine:</span>
                  <span className="text-brand-500 font-bold">PaddleOCR</span>
                </div>
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-slate-400">Secondary Fallback:</span>
                  <span className="text-slate-655 dark:text-slate-350">Tesseract</span>
                </div>
                <p className="text-[10px] font-medium text-slate-400 dark:text-slate-500 pt-1 leading-normal">
                  * PaddleOCR parses mixed and handwritten elements. If a low-confidence segment is discovered, Tesseract provides optional anchor comparison logic automatically.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Card: System Status */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 p-6 rounded-3xl space-y-6 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/60">
            <div className="flex items-center space-x-2">
              <Cpu className="h-5 w-5 text-brand-500" />
              <h3 className="font-extrabold text-slate-900 dark:text-white text-base">Host Diagnostics</h3>
            </div>
            <button
              onClick={fetchHealth}
              disabled={loadingHealth}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-850 transition-all text-slate-450"
              title="Refresh Diagnostics"
            >
              <RefreshCw className={`h-4.5 w-4.5 ${loadingHealth ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="space-y-4">
            {health ? (
              <div className="space-y-4 text-xs">
                {/* Health Status */}
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/60 pb-3">
                  <span className="font-bold text-slate-500">Service Status</span>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${
                    health.status === 'ok' 
                      ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-400' 
                      : 'bg-rose-50 text-rose-800 dark:bg-rose-950/20 dark:text-rose-455'
                  }`}>
                    {health.status}
                  </span>
                </div>

                {/* Database Connectivity */}
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/60 pb-3">
                  <span className="font-bold text-slate-500 flex items-center space-x-1.5">
                    <Database className="h-4 w-4" />
                    <span>Database Socket</span>
                  </span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {health.database_connected ? 'CONNECTED (SQLite)' : 'FAILED'}
                  </span>
                </div>

                {/* Local Storage status */}
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/60 pb-3">
                  <span className="font-bold text-slate-500">Writable Directories</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {health.storage_writable ? 'GRANTED' : 'DENIED'}
                  </span>
                </div>

                {/* Server Uptime */}
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-500">Uptime</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {Math.round(health.uptime_seconds)}s
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-slate-400">
                <ServerCrash className="h-8 w-8 mx-auto text-slate-350 animate-bounce mb-2" />
                <span className="text-xs font-bold">Failed to load diag status. Is backend port 8000 online?</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
