import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { api } from '../api/client';

interface UserInfo {
  username: string;
  role: string;
  email: string;
  full_name: string | null;
}

interface AuthState {
  isAuthenticated: boolean;
  user: UserInfo | null;
  login: (username: string, password: string) => Promise<any>;
  logout: () => void;
  setAuthenticated: (value: boolean) => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  user: null,
  login: async () => {},
  logout: () => {},
  setAuthenticated: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!api.getToken());
  const [user, setUser] = useState<UserInfo | null>(null);

  // Validate token on app load — auto-logout if expired or invalid
  useEffect(() => {
    if (!api.getToken()) return;
    api.get<UserInfo>('/auth/me')
      .then((u) => { setUser(u); setIsAuthenticated(true); })
      .catch(() => {
        api.clearToken();
        setUser(null);
        setIsAuthenticated(false);
      });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    setIsAuthenticated(true);
    if (data.user) setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(() => {
    api.clearToken();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, setAuthenticated: setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
