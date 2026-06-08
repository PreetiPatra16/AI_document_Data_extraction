import { create } from 'zustand';
import { BatchItem } from '../types';

const STORAGE_KEY = 'docuextract-active-batch';

interface AppState {
  items: BatchItem[];
  darkMode: boolean;
  stageFiles: (files: File[]) => void;
  removeItem: (localId: string) => void;
  clearTerminalItems: () => void;
  updateItem: (localId: string, updates: Partial<BatchItem>) => void;
  recoverItems: () => void;
  toggleDarkMode: () => void;
  initializeTheme: () => void;
}

function persist(items: BatchItem[]) {
  const recoverable = items
    .filter((item) => item.documentId)
    .map((item) => ({
      localId: item.localId,
      filename: item.filename,
      size: item.size,
      mimeType: item.mimeType,
      documentId: item.documentId,
      jobId: item.jobId,
      status: item.status,
      stage: item.stage,
      progress: item.progress,
      previewLost: true,
    }));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(recoverable));
}

export const useDocumentStore = create<AppState>((set) => ({
  items: [],
  darkMode: false,
  stageFiles: (files) => set((state) => ({
    items: [
      ...state.items,
      ...files.map((file) => ({
        localId: crypto.randomUUID(),
        filename: file.name,
        size: file.size,
        mimeType: file.type,
        file,
        previewUrl: URL.createObjectURL(file),
        status: 'STAGED' as const,
        progress: 0,
      })),
    ],
  })),
  removeItem: (localId) => set((state) => {
    const target = state.items.find((item) => item.localId === localId);
    if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
    const items = state.items.filter((item) => item.localId !== localId);
    persist(items);
    return { items };
  }),
  clearTerminalItems: () => set((state) => {
    state.items
      .filter((item) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status))
      .forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
    const items = state.items.filter((item) => !['COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status));
    persist(items);
    return { items };
  }),
  updateItem: (localId, updates) => set((state) => {
    const items = state.items.map((item) => item.localId === localId ? { ...item, ...updates } : item);
    persist(items);
    return { items };
  }),
  recoverItems: () => set((state) => {
    if (state.items.length) return state;
    try {
      const items = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as BatchItem[];
      return { items: items.map((item) => ({ ...item, previewLost: true })) };
    } catch {
      return { items: [] };
    }
  }),
  toggleDarkMode: () => set((state) => {
    const darkMode = !state.darkMode;
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
    return { darkMode };
  }),
  initializeTheme: () => {
    const saved = localStorage.getItem('theme');
    const darkMode = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', darkMode);
    set({ darkMode });
  },
}));
