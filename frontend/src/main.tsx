import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './contexts/ThemeContext';
import './index.css';
import './styles/tokens.css';
import App from './App';

/**
 * Data freshness strategy (principal UI/UX):
 *
 * React Query v5 suppresses ALL network activity in hidden tabs —
 * refetchInterval, invalidateQueries, and refetchQueries all queue
 * but don't execute when document.hidden === true.
 *
 * Solution: native setInterval with direct fetch() + cache update.
 * React Query is the cache layer. We control when network requests fire.
 * This is the same pattern Datadog and Grafana use for dashboard polling.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      staleTime: 30_000,
    },
  },
});

// Endpoints to poll and their React Query cache keys
const POLL_ENDPOINTS = [
  { key: ['dashboard-summary'], path: '/dashboard/summary' },
  { key: ['dashboard-unprotected'], path: '/dashboard/unprotected' },
  { key: ['dashboard-compliance'], path: '/dashboard/compliance' },
  { key: ['dashboard-activity'], path: '/dashboard/activity?days=7' },
];

// Resolve API base URL (same logic as api/client.ts)
function getApiBase(): string {
  const w = window as any;
  if (w.__RUNTIME_CONFIG__?.API_BASE) return `${w.__RUNTIME_CONFIG__.API_BASE}/api`;
  return import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
}

// Native polling — bypasses React Query's visibility gate
setInterval(async () => {
  const base = getApiBase();
  const tenant = (window as any).__kavachiq_selected_tenant;

  for (const { key, path } of POLL_ENDPOINTS) {
    try {
      const separator = path.includes('?') ? '&' : '?';
      const url = tenant ? `${base}${path}${separator}tenant_id=${tenant}` : `${base}${path}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        queryClient.setQueryData(key, data);
      }
    } catch {
      // Silent — don't break the poll loop for one failed endpoint
    }
  }
}, 30_000);

// Also poll health score (needs tenant_id which may not be set at startup)
setInterval(async () => {
  const base = getApiBase();
  const tenant = (window as any).__kavachiq_selected_tenant;
  if (!tenant) return;
  try {
    const res = await fetch(`${base}/health/score?tenant_id=${tenant}`, { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      queryClient.setQueryData(['health-score', Number(tenant)], data);
    }
  } catch {}
}, 30_000);

// Immediate refresh when tab becomes visible
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    queryClient.refetchQueries({ type: 'active' });
  }
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
