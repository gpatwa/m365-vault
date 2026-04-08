/**
 * Auth Context — Enterprise BFF Pattern
 *
 * Authentication state derived from server session (httpOnly cookie).
 * No tokens in browser. No sessionStorage. No localStorage.
 *
 * PERFORMANCE: Uses React Query with queryKey ['session'] and staleTime=60s.
 * This is the SINGLE shared session query — TenantGate, useTenantSwitcher,
 * and Layout all use the same ['session'] queryKey. React Query deduplicates
 * concurrent requests and caches the result, eliminating duplicate API calls.
 *
 * On app load: calls /auth/session → if 200, user is authenticated.
 * Login: calls /auth/login → backend sets httpOnly cookie → invalidate session query.
 * Logout: calls /auth/logout → backend clears cookie + Redis session.
 */
import { createContext, useContext, useCallback, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

interface UserInfo {
  username: string;
  role: string;
  email: string;
  full_name: string | null;
  is_platform_admin?: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;  // True during initial session check
  user: UserInfo | null;
  session: any;        // Full session data (used by TenantGate, useTenantSwitcher)
  login: (username: string, password: string) => Promise<any>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  session: null,
  login: async () => {},
  logout: () => {},
});

/**
 * Shared session query key — used by AuthContext, TenantGate, useTenantSwitcher.
 * All read from the same React Query cache entry. ONE network request, shared result.
 */
export const SESSION_QUERY_KEY = ['session'];
export const SESSION_STALE_TIME = 60_000; // 1 min — balances freshness vs performance

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  // SINGLE session query — shared by AuthContext + TenantGate + useTenantSwitcher + Layout
  const { data: session, isLoading } = useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: async () => {
      try {
        return await api.get<any>('/auth/session');
      } catch {
        return null; // Not authenticated
      }
    },
    staleTime: SESSION_STALE_TIME,
    retry: false,
  });

  const isAuthenticated = !!session?.user || !!session?.username;
  const user = session?.user || (session?.username ? session : null);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    // Invalidate session cache so it re-fetches with new auth cookie
    queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    return data;
  }, [queryClient]);

  const logout = useCallback(async () => {
    await api.logout();  // Backend clears cookie + destroys Redis session
    // Clear session cache immediately
    queryClient.setQueryData(SESSION_QUERY_KEY, null);
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
