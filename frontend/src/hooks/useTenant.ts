import { useQuery } from '@tanstack/react-query';
import { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import type { Tenant } from '../types';

/* ------------------------------------------------------------------ */
/*  Workload lifecycle status types                                    */
/* ------------------------------------------------------------------ */

interface WorkloadStatusEntry {
  workload: string;
  lifecycle_status: 'disabled' | 'enabled' | 'discovered' | 'protected' | 'paused';
  consent_status: string;
  backup_ready: boolean;
  restore_ready: boolean;
  enabled: boolean;
  client_id: string | null;
  error_message: string | null;
  created_at: string;
}

interface WorkloadStatusResponse {
  tenant_id: number;
  workloads: WorkloadStatusEntry[];
}

/* ------------------------------------------------------------------ */
/*  useWorkloadStatuses — shared query for workload lifecycle data      */
/* ------------------------------------------------------------------ */

/**
 * Fetches workload statuses for the selected tenant.
 * Shared across Layout sidebar, workload pages, etc.
 * Uses staleTime: 60s to avoid redundant fetches.
 */
export function useWorkloadStatuses() {
  const tenantId = useTenantId();
  const { data, isLoading } = useQuery({
    queryKey: ['workload-statuses', tenantId],
    queryFn: () => api.get<WorkloadStatusResponse>(`/tenants/${tenantId}/workloads`),
    enabled: !!tenantId,
    staleTime: 60_000,
  });
  return { workloadStatuses: data?.workloads ?? [], isLoading };
}

/* ------------------------------------------------------------------ */
/*  useWorkloadEnabled — check if a specific workload is enabled       */
/* ------------------------------------------------------------------ */

/**
 * Returns whether a specific workload is enabled (lifecycle_status !== 'disabled')
 * for the current tenant. Returns undefined while loading.
 */
export function useWorkloadEnabled(workloadKey: string): boolean | undefined {
  const { workloadStatuses, isLoading } = useWorkloadStatuses();
  if (isLoading && workloadStatuses.length === 0) return undefined; // still loading
  const wl = workloadStatuses.find(w => w.workload === workloadKey);
  return wl ? wl.lifecycle_status !== 'disabled' : false;
}

/**
 * Returns the set of enabled workload keys for the current tenant.
 */
export function useEnabledWorkloadKeys(): Set<string> | undefined {
  const { workloadStatuses, isLoading } = useWorkloadStatuses();
  if (isLoading && workloadStatuses.length === 0) return undefined;
  return new Set(
    workloadStatuses
      .filter(w => w.lifecycle_status !== 'disabled')
      .map(w => w.workload)
  );
}

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

  // Read saved selection from the SHARED session query (same ['session'] queryKey
  // as AuthContext). React Query deduplicates — zero extra API calls.
  const { data: sessionData } = useQuery({
    queryKey: ['session'],
    queryFn: () => api.get<any>('/auth/session'),
    staleTime: 60_000, // Match AuthContext staleTime (single source of truth)
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
