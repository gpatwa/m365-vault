import { useQuery } from '@tanstack/react-query';
import { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import type { Tenant } from '../types';

/**
 * Returns the preferred active tenant ID.
 * Reads from server session, not localStorage.
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
 * Reads selected tenant from server session. Saves preference via API.
 * No localStorage dependency.
 */
export function useTenantSwitcher() {
  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
    staleTime: 60000,
  });

  // Read saved selection from server (via session query or local cache)
  const { data: sessionData } = useQuery({
    queryKey: ['session'],
    queryFn: () => api.get<any>('/auth/session'),
    staleTime: 300000, // 5 min cache
  });

  const serverSelectedId = sessionData?.preferences?.selected_tenant
    ? parseInt(sessionData.preferences.selected_tenant)
    : undefined;

  const [selectedId, setSelectedId] = useState<number | undefined>(serverSelectedId);

  // Sync from server when session loads
  useEffect(() => {
    if (serverSelectedId && serverSelectedId !== selectedId) {
      setSelectedId(serverSelectedId);
    }
  }, [serverSelectedId]);

  const activeTenants = (tenants || []).filter(t => t.status === 'active');
  const savedTenant = activeTenants.find(t => t.id === selectedId);
  const defaultTenant = activeTenants.find(t => t.ms_tenant_id && !t.ms_tenant_id.startsWith('demo-')) || activeTenants[0];
  const selectedTenant = savedTenant || defaultTenant;

  // Auto-set default if nothing selected + update in-memory cache for API client
  useEffect(() => {
    if (tenants && tenants.length > 0 && !savedTenant && defaultTenant) {
      setSelectedId(defaultTenant.id);
      (window as any).__kavachiq_selected_tenant = String(defaultTenant.id);
      api.put(`/auth/preferences/selected_tenant`, { value: String(defaultTenant.id) }).catch(() => {});
    }
    // Always keep in-memory cache in sync
    if (selectedTenant?.id) {
      (window as any).__kavachiq_selected_tenant = String(selectedTenant.id);
    }
  }, [tenants, savedTenant, defaultTenant, selectedTenant]);

  const switchTenant = useCallback((tenantId: number) => {
    setSelectedId(tenantId);
    // Save to server (preference persists across devices)
    api.put(`/auth/preferences/selected_tenant`, { value: String(tenantId) }).catch(() => {});
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
