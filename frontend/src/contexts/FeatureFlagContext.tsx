import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

interface FeatureFlags {
  [key: string]: { enabled: boolean; source: string };
}

interface FeatureFlagState {
  tier: string;
  flags: FeatureFlags;
  limits: Record<string, any>;
  loaded: boolean;
  isEnabled: (feature: string) => boolean;
  refresh: () => void;
}

const DEFAULTS: FeatureFlagState = {
  tier: 'community',
  flags: {},
  limits: {},
  loaded: false,
  isEnabled: () => false,
  refresh: () => {},
};

const FeatureFlagContext = createContext<FeatureFlagState>(DEFAULTS);

const API_BASE =
  (window as any).__RUNTIME_CONFIG__?.API_BASE
    ? `${(window as any).__RUNTIME_CONFIG__.API_BASE}/api`
    : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export function FeatureFlagProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<FeatureFlagState>(DEFAULTS);

  const fetchFlags = useCallback(() => {
    fetch(`${API_BASE}/features`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          const flags = data.features || {};
          setState({
            tier: data.tier || 'community',
            flags,
            limits: data.limits || {},
            loaded: true,
            isEnabled: (feature: string) => flags[feature]?.enabled === true,
            refresh: fetchFlags,
          });
        } else {
          setState(prev => ({ ...prev, loaded: true, refresh: fetchFlags }));
        }
      })
      .catch(() => setState(prev => ({ ...prev, loaded: true, refresh: fetchFlags })));
  }, []);

  useEffect(() => { fetchFlags(); }, [fetchFlags]);

  return (
    <FeatureFlagContext.Provider value={state}>
      {children}
    </FeatureFlagContext.Provider>
  );
}

export function useFeatureFlags() {
  return useContext(FeatureFlagContext);
}

/**
 * Gate component — only renders children if feature is enabled.
 * Shows nothing (or fallback) when feature is disabled.
 */
export function FeatureGate({ feature, children, fallback = null }: {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { isEnabled, loaded } = useFeatureFlags();
  if (!loaded) return null;
  return isEnabled(feature) ? <>{children}</> : <>{fallback}</>;
}
