import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { api } from '../api/client';

type Theme = 'dark' | 'light';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Default to dark, server session overrides on load
  const [theme, setThemeState] = useState<Theme>('dark');

  // Load theme from server session on mount
  useEffect(() => {
    api.get<any>('/auth/session')
      .then(session => {
        const serverTheme = session?.preferences?.theme as Theme;
        if (serverTheme && (serverTheme === 'dark' || serverTheme === 'light')) {
          setThemeState(serverTheme);
        }
      })
      .catch(() => {}); // Not logged in yet — use default
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    // Save to server (persists across devices)
    api.put(`/auth/preferences/theme`, { value: t }).catch(() => {});
  };
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
