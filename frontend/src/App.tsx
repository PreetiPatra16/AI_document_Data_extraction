import React, { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { useDocumentStore } from './store/documentStore';
import { apiService } from './services/api';

// Pages
import { Dashboard } from './pages/Dashboard';
import { UploadWorkspace } from './pages/UploadWorkspace';
import { ExtractionResults } from './pages/ExtractionResults';
import { ProcessingLogs } from './pages/ProcessingLogs';
import { Settings } from './pages/Settings';

const queryClient = new QueryClient();

const AppContent: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<string>('dashboard');
  const { setDocuments, initializeTheme } = useDocumentStore();

  // Load theme preference on boot
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);

  // Periodically fetch documents list to update state dashboard metrics
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await apiService.listDocuments();
        setDocuments(docs);
      } catch (err) {
        console.error("Failed to connect to Local Engine API:", err);
      }
    };

    fetchDocs();
    const interval = setInterval(fetchDocs, 4000);
    return () => clearInterval(interval);
  }, [setDocuments]);

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard setCurrentPage={setCurrentPage} />;
      case 'upload':
        return <UploadWorkspace setCurrentPage={setCurrentPage} />;
      case 'results':
        return <ExtractionResults />;
      case 'logs':
        return <ProcessingLogs />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard setCurrentPage={setCurrentPage} />;
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
        <main className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full">
          {renderPage()}
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
