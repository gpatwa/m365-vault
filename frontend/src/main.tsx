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
 * But not all data needs the same cadence:
 *
 * REAL-TIME (5s):    Jobs page — user is watching a backup run
 * ACTIVE (30s):      Dashboard, health score — user is monitoring
 * PASSIVE (60s):     Workload lists, compliance — user is browsing
 * STATIC (5min):     Settings, organization — user is configuring
 *
 * This default covers ACTIVE cadence. Pages override for their context.
 * Tab focus triggers immediate refresh (user comes back, sees fresh data).
 * Background polling stays ON — when user switches back, data is already current.
 * Cost: ~8 API calls per 30s per open tab. Acceptable for SaaS monitoring dashboard.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      staleTime: 30_000,
      refetchInterval: 30_000,
      refetchIntervalInBackground: true,
    },
  },
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
