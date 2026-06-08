import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { useDocumentStore } from './store/documentStore';
import { Diagnostics } from './pages/Diagnostics';
import { DocumentDetail } from './pages/DocumentDetail';
import { History } from './pages/History';
import { Workspace } from './pages/Workspace';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 2_000 } },
});

function Application() {
  const initializeTheme = useDocumentStore((state) => state.initializeTheme);
  const recoverItems = useDocumentStore((state) => state.recoverItems);

  useEffect(() => {
    initializeTheme();
    recoverItems();
  }, [initializeTheme, recoverItems]);

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Workspace />} />
        <Route path="/history" element={<History />} />
        <Route path="/documents/:documentId" element={<DocumentDetail />} />
        <Route path="/diagnostics" element={<Diagnostics />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Application />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
