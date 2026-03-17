import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export function useGet<T>(key: string[], path: string, enabled = true) {
  return useQuery({ queryKey: key, queryFn: () => api.get<T>(path), enabled });
}

export function usePost<T>(key: string[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => api.post<T>(path, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export function usePut<T>(key: string[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => api.put<T>(path, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export function useDelete(key: string[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) => api.del(path),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}
