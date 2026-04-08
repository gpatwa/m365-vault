/**
 * Auth Context — Enterprise BFF Pattern
 *
 * Authentication state derived from server session (httpOnly cookie).
 * No tokens in browser. No sessionStorage. No localStorage.
 *
 * On app load: calls /auth/session → if 200, user is authenticated.
 * Login: calls /auth/login → backend sets httpOnly cookie → re-check session.
 * Logout: calls /auth/logout → backend clears cookie + Redis session.
 */
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
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
  login: (username: string, password: string) => Promise<any>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);  // Loading until session check completes
  const [user, setUser] = useState<UserInfo | null>(null);

  // Check session on app load — httpOnly cookie sent automatically
  useEffect(() => {
    api.checkSession()
      .then((session) => {
        if (session) {
          setIsAuthenticated(true);
          setUser(session.user || session);
        } else {
          setIsAuthenticated(false);
          setUser(null);
        }
      })
      .catch(() => {
        setIsAuthenticated(false);
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    // Backend sets httpOnly cookie — we just update React state
    setIsAuthenticated(true);
    if (data.user) setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    await api.logout();  // Backend clears cookie + destroys Redis session
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
