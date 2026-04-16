import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Templates } from './pages/Templates';
import { AdminTemplates } from './pages/AdminTemplates';
import { LaunchTemplate } from './pages/LaunchTemplate';
import { History } from './pages/History';
import { OpenAPI } from './api/generated';
import './index.css';

OpenAPI.BASE = import.meta.env.VITE_API_URL ?? '';
OpenAPI.WITH_CREDENTIALS = true;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/admin/templates" element={<AdminTemplates />} />
            <Route path="/history" element={<History />} />
            <Route path="/launch/:templateId" element={<LaunchTemplate />} />
          </Routes>
        </Layout>
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
