import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Tenant } from '../types';

/**
 * Returns the preferred active tenant ID.
 * Priority: real M365 tenant > demo tenant > any tenant.
 */
export function useTenantId(): number | undefined {
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
    staleTime: 60000,
  });

  if (!tenants || tenants.length === 0) return undefined;

  // Prefer active tenants
  const active = tenants.filter(t => t.status === 'active');
  if (active.length === 0) return tenants[0]?.id;

  // Prefer real M365 tenant (ms_tenant_id is a GUID, not "demo-*")
  const real = active.find(t => t.ms_tenant_id && !t.ms_tenant_id.startsWith('demo-'));
  if (real) return real.id;

  return active[0]?.id;
}
