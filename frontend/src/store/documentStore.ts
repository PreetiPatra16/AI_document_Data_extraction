import { create } from 'zustand';
import { Document } from '../types';

interface DocumentState {
  documents: Document[];
  activeDocument: Document | null;
  darkMode: boolean;
  
  // Actions
  setDocuments: (docs: Document[]) => void;
  setActiveDocument: (doc: Document | null) => void;
  addDocument: (doc: Document) => void;
  updateDocumentInStore: (docId: string, updates: Partial<Document>) => void;
  toggleDarkMode: () => void;
  initializeTheme: () => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  documents: [],
  activeDocument: null,
  darkMode: false,

  setDocuments: (documents) => set({ documents }),
  setActiveDocument: (activeDocument) => set({ activeDocument }),
  addDocument: (doc) => set((state) => ({ documents: [doc, ...state.documents] })),
  
  updateDocumentInStore: (docId, updates) => set((state) => {
    const updatedDocs = state.documents.map((doc) => 
      doc.id === docId ? { ...doc, ...updates } : doc
    );
    const updatedActive = state.activeDocument?.id === docId 
      ? { ...state.activeDocument, ...updates } 
      : state.activeDocument;
      
    return {
      documents: updatedDocs,
      activeDocument: updatedActive
    };
  }),

  toggleDarkMode: () => set((state) => {
    const newMode = !state.darkMode;
    if (newMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
    return { darkMode: newMode };
  }),

  initializeTheme: () => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    
    if (isDark) {
      document.documentElement.classList.add('dark');
      set({ darkMode: true });
    } else {
      document.documentElement.classList.remove('dark');
      set({ darkMode: false });
    }
  }
}));
