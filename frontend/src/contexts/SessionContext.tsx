/**
 * SessionContext — server-driven state for the entire app.
 *
 * Enterprise pattern: ONE call to /auth/session on app load.
 * Returns user, routing, tenant, preferences, feature flags.
 * No localStorage, no sessionStorage (except JWT token).
 *
 * Usage:
 *   const { session, setPreference } = useSession();
 *   session.preferences.theme   // "dark"
 *   session.routing.redirect    // null (dashboard) or "/onboard"
 *   setPreference("theme", "light")  // saves to server
 */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { api } from '../api/client';

export interface Session {
  user: {
    id: number;
    username: string;
    email: string;
    full_name: string;
    role: string;
    is_platform_admin: boolean;
  };
  routing: {
    onboarding_status: 'complete' | 'pending' | 'demo';
    redirect: string | null;
  };
  tenant: {
    id: number;
    name: string;
    ms_tenant_id: string;
  } | null;
  tenant_count: number;
  preferences: {
    theme: string;
    selected_tenant: string | null;
    tour_completed: boolean;
    checklist_dismissed: boolean;
    recent_commands: string;
  };
  feature_flags: Record<string, string[]>;
}

interface SessionContextType {
  session: Session | null;
  loading: boolean;
  setPreference: (key: string, value: string) => Promise<void>;
  refreshSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType>({
  session: null,
  loading: true,
  setPreference: async () => {},
  refreshSession: async () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    try {
      const data = await api.get<Session>('/auth/session');
      setSession(data);
    } catch (err) {
      console.error('[SessionContext] Failed to load session:', err);
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (api.getToken()) {
      loadSession();
    } else {
      setLoading(false);
    }
  }, [loadSession]);

  const setPreference = useCallback(async (key: string, value: string) => {
    try {
      await api.put(`/auth/preferences/${key}`, { value });
      // Update local session state immediately (optimistic)
      setSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          preferences: {
            ...prev.preferences,
            [key]: value === 'true' ? true : value === 'false' ? false : value,
          },
        };
      });
    } catch (err) {
      console.error(`[SessionContext] Failed to save preference ${key}:`, err);
    }
  }, []);

  return (
    <SessionContext.Provider value={{ session, loading, setPreference, refreshSession: loadSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
