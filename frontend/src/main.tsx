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
 * The user should NEVER need to hit browser refresh. Data updates itself.
 *
 * React Query's built-in refetchInterval does NOT work reliably in hidden
 * tabs (Chrome throttles timers, visibility API suppresses intervals).
 * Instead, we use a native setInterval that invalidates all queries on
 * a fixed cadence. This is the same pattern Datadog and Grafana use.
 *
 * Cadence tiers (pages override with their own refetchInterval):
 * - REAL-TIME (5s):  Jobs page — watching a backup run
 * - ACTIVE (30s):    Dashboard, health — monitoring (global default)
 * - PASSIVE (60s):   Workload lists — browsing
 * - STATIC (disabled): Settings — only on focus/manual action
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

// Global poll: force refetch all active queries every 30 seconds.
// invalidateQueries() only marks stale — doesn't trigger fetch in hidden tabs.
// refetchQueries() forces immediate network requests regardless of tab state.
setInterval(() => {
  queryClient.refetchQueries({ type: 'active' });
}, 30_000);

// Immediate refresh when user switches back to this tab
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
