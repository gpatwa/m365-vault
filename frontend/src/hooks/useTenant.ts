import { useQuery } from '@tanstack/react-query';
import { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import type { Tenant } from '../types';

const SELECTED_TENANT_KEY = 'kavachiq_selected_tenant';

/**
 * Returns the preferred active tenant ID.
 * Priority: localStorage selection > real M365 tenant > demo tenant > any tenant.
 */
export function useTenantId(): number | undefined {
  const { selectedTenantId } = useTenantSwitcher();
  return selectedTenantId;
}

/**
 * Returns whether the active tenant is a demo tenant + whether any real tenant exists.
 */
export function useTenantInfo(): {
  tenantId: number | undefined;
  isDemoTenant: boolean;
  hasRealTenant: boolean;
  tenantName: string | undefined;
} {
  const { selectedTenant, tenants } = useTenantSwitcher();

  if (!tenants || tenants.length === 0) {
    return { tenantId: undefined, isDemoTenant: false, hasRealTenant: false, tenantName: undefined };
  }

  const real = tenants.find(t => t.ms_tenant_id && !t.ms_tenant_id.startsWith('demo-') && t.status === 'active');
  const isDemoTenant = selectedTenant?.ms_tenant_id?.startsWith('demo-') ?? false;

  return {
    tenantId: selectedTenant?.id,
    isDemoTenant,
    hasRealTenant: !!real,
    tenantName: selectedTenant?.name,
  };
}

/**
 * Full tenant switcher hook — used by Layout header and any component
 * that needs to know/change the active tenant.
 *
 * Persists selection in localStorage. Falls back to first active tenant.
 */
export function useTenantSwitcher() {
  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
    staleTime: 60000,
  });

  // Load saved selection from localStorage
  const [selectedId, setSelectedId] = useState<number | undefined>(() => {
    const saved = localStorage.getItem(SELECTED_TENANT_KEY);
    return saved ? parseInt(saved) : undefined;
  });

  // Resolve the selected tenant — fall back to first active if saved is invalid
  const activeTenants = (tenants || []).filter(t => t.status === 'active');
  const savedTenant = activeTenants.find(t => t.id === selectedId);
  const defaultTenant = activeTenants.find(t => t.ms_tenant_id && !t.ms_tenant_id.startsWith('demo-')) || activeTenants[0];
  const selectedTenant = savedTenant || defaultTenant;

  // Sync selectedId when tenants load and saved ID is invalid
  useEffect(() => {
    if (tenants && tenants.length > 0 && !savedTenant && defaultTenant) {
      setSelectedId(defaultTenant.id);
      localStorage.setItem(SELECTED_TENANT_KEY, String(defaultTenant.id));
    }
  }, [tenants, savedTenant, defaultTenant]);

  const switchTenant = useCallback((tenantId: number) => {
    setSelectedId(tenantId);
    localStorage.setItem(SELECTED_TENANT_KEY, String(tenantId));
    // Reload page to refresh all data for new tenant
    window.location.reload();
  }, []);

  return {
    tenants: activeTenants,
    selectedTenant,
    selectedTenantId: selectedTenant?.id,
    switchTenant,
    isLoading,
    isMultiTenant: activeTenants.length > 1,
  };
}
