import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Templates } from './pages/Templates';
import { AdminTemplates } from './pages/AdminTemplates';
import { AdminDashboard } from './pages/AdminDashboard';
import { LaunchTemplate } from './pages/LaunchTemplate';
import { History } from './pages/History';
import { OpenAPI } from './api/generated';
import { ToastProvider } from './components/ui/Toast';
import { initAnalytics, trackPageView } from './utils/analytics';
import './index.css';

// window.__ORCHESTRA_CONFIG__ is declared (and documented) in utils/analytics.ts.
OpenAPI.BASE = window.__ORCHESTRA_CONFIG__?.apiUrl || import.meta.env.VITE_API_URL || '';
OpenAPI.WITH_CREDENTIALS = true;

// GA4 — inert unless a measurement ID is configured (see utils/analytics.ts).
initAnalytics();

// gtag is configured with send_page_view: false, so every page view (including
// the first) is sent here on route change.
function PageTracker() {
  const location = useLocation();
  React.useEffect(() => {
    trackPageView(location.pathname);
  }, [location.pathname]);
  return null;
}

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
    <ToastProvider>
    <QueryClientProvider client={queryClient}>
      <Router>
        <PageTracker />
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/admin/templates" element={<AdminTemplates />} />
            <Route path="/admin/sessions" element={<AdminDashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/launch/:templateId" element={<LaunchTemplate />} />
          </Routes>
        </Layout>
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
    </ToastProvider>
  );
}

export default App;
