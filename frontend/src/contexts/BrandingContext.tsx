import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface BrandingState {
  companyName: string;
  tagline: string;
  logoUrl: string | null;
  faviconUrl: string | null;
  primaryColor: string;
  secondaryColor: string;
  loaded: boolean;
  refresh: () => void;
}

const DEFAULTS: BrandingState = {
  companyName: 'Shieldio',
  tagline: 'SaaS Data Protection',
  logoUrl: null,
  faviconUrl: null,
  primaryColor: '#3b82f6',
  secondaryColor: '#1e293b',
  loaded: false,
  refresh: () => {},
};

const BrandingContext = createContext<BrandingState>(DEFAULTS);

const API_BASE =
  (window as any).__RUNTIME_CONFIG__?.API_BASE
    ? `${(window as any).__RUNTIME_CONFIG__.API_BASE}/api`
    : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<BrandingState>(DEFAULTS);

  const fetchBranding = () => {
    fetch(`${API_BASE}/msp/branding`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          setBranding({
            companyName: data.company_name || 'Shieldio',
            tagline: data.tagline || 'SaaS Data Protection',
            logoUrl: data.logo_url || null,
            faviconUrl: data.favicon_url || null,
            primaryColor: data.primary_color || '#3b82f6',
            secondaryColor: data.secondary_color || '#1e293b',
            loaded: true,
            refresh: fetchBranding,
          });
          // Set CSS custom properties for dynamic theming
          document.documentElement.style.setProperty('--color-primary', data.primary_color || '#3b82f6');
          document.documentElement.style.setProperty('--color-secondary', data.secondary_color || '#1e293b');
          // Update page title
          if (data.company_name && data.company_name !== 'Shieldio') {
            document.title = data.company_name;
          }
        } else {
          setBranding(prev => ({ ...prev, loaded: true, refresh: fetchBranding }));
        }
      })
      .catch(() => setBranding(prev => ({ ...prev, loaded: true, refresh: fetchBranding })));
  };

  useEffect(() => { fetchBranding(); }, []);

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
