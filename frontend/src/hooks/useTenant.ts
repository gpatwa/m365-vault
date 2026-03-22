import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Tenant } from '../types';

/**
 * Returns the first active tenant ID. Used across all workload pages
 * instead of hardcoding tenantId = 1.
 *
 * TODO: When multi-tenant UI is added, this should use a tenant selector context.
 */
export function useTenantId(): number | undefined {
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
    staleTime: 60000, // cache for 1 min to avoid refetching on every page
  });

  // Prefer active tenant, fall back to any tenant
  const active = tenants?.find(t => t.status === 'active');
  return active?.id ?? tenants?.[0]?.id;
}
