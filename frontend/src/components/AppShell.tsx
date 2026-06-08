import { useState } from 'react';
import { Activity, FileClock, Menu, Moon, Sun, UploadCloud, X } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import { useDocumentStore } from '../store/documentStore';

const links = [
  { to: '/', label: 'Workspace', icon: UploadCloud },
  { to: '/history', label: 'History', icon: FileClock },
  { to: '/diagnostics', label: 'Diagnostics', icon: Activity },
];

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { darkMode, toggleDarkMode } = useDocumentStore();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between px-4 sm:px-6">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-500 text-white shadow-lg shadow-brand-500/20">
              <UploadCloud className="h-5 w-5" />
            </span>
            <span>
              <strong className="block text-sm font-extrabold tracking-tight">DocuExtract</strong>
              <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400">Local operator workspace</span>
            </span>
          </NavLink>

          <nav className="hidden items-center gap-1 md:flex">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) =>
                `flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold transition ${
                  isActive ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900'
                }`
              }>
                <Icon className="h-4 w-4" /> {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <button onClick={toggleDarkMode} className="rounded-xl border border-slate-200 p-2 text-slate-500 dark:border-slate-800" aria-label="Toggle theme">
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <button onClick={() => setMenuOpen((open) => !open)} className="rounded-xl border border-slate-200 p-2 text-slate-500 dark:border-slate-800 md:hidden" aria-label="Toggle navigation">
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav className="space-y-1 border-t border-slate-200 p-3 dark:border-slate-800 md:hidden">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} onClick={() => setMenuOpen(false)} className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900">
                <Icon className="h-4 w-4" /> {label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}
