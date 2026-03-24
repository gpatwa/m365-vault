import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { api } from '../api/client';

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<any>;
  logout: () => void;
  setAuthenticated: (value: boolean) => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  login: async () => {},
  logout: () => {},
  setAuthenticated: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!api.getToken());

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    setIsAuthenticated(true);
    return data;
  }, []);

  const logout = useCallback(() => {
    api.clearToken();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, setAuthenticated: setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
