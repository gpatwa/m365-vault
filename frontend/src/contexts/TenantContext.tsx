import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';

interface TenantState {
  tenantId: number | null;
  tenantName: string | null;
  setTenant: (id: number, name: string) => void;
  clearTenant: () => void;
}

const TenantContext = createContext<TenantState>({
  tenantId: null,
  tenantName: null,
  setTenant: () => {},
  clearTenant: () => {},
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenantId, setTenantId] = useState<number | null>(() => {
    // Restore from sessionStorage on mount
    const stored = sessionStorage.getItem('kavachiq_tenant_id');
    return stored ? parseInt(stored, 10) : null;
  });
  const [tenantName, setTenantName] = useState<string | null>(() => {
    return sessionStorage.getItem('kavachiq_tenant_name');
  });

  // Read from URL query param on initial load
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlTenantId = params.get('tenant_id');
    if (urlTenantId) {
      const id = parseInt(urlTenantId, 10);
      if (!isNaN(id)) {
        setTenantId(id);
        sessionStorage.setItem('kavachiq_tenant_id', String(id));
      }
    }
  }, []);

  const setTenant = useCallback((id: number, name: string) => {
    setTenantId(id);
    setTenantName(name);
    sessionStorage.setItem('kavachiq_tenant_id', String(id));
    sessionStorage.setItem('kavachiq_tenant_name', name);
  }, []);

  const clearTenant = useCallback(() => {
    setTenantId(null);
    setTenantName(null);
    sessionStorage.removeItem('kavachiq_tenant_id');
    sessionStorage.removeItem('kavachiq_tenant_name');
  }, []);

  return (
    <TenantContext.Provider value={{ tenantId, tenantName, setTenant, clearTenant }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenantContext() {
  return useContext(TenantContext);
}
