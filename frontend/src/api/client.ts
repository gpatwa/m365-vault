/**
 * KavachIQ API Client — Enterprise BFF Pattern
 *
 * Auth: httpOnly cookie (set by backend on login, sent automatically by browser).
 * Browser stores NOTHING — no tokens, no sessionStorage, no localStorage for auth.
 * Tenant scoping: in-memory cache from /auth/session (set by useTenantSwitcher).
 *
 * The browser sends the session cookie automatically with `credentials: 'include'`.
 * The backend reads the cookie, looks up the Redis session, and authenticates.
 */

// API base URL resolution order:
// 1. Runtime config (injected by nginx config.js in Docker/Azure)
// 2. Vite build-time env (VITE_API_BASE)
// 3. Dev fallback (localhost)
declare global {
  interface Window {
    __RUNTIME_CONFIG__?: { API_BASE: string };
    __kavachiq_selected_tenant?: string;
  }
}
const API_BASE =
  window.__RUNTIME_CONFIG__?.API_BASE
  ? `${window.__RUNTIME_CONFIG__.API_BASE}/api`
  : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

/**
 * Structured API error matching backend KavachIQ error format.
 */
export class ApiError extends Error {
  code: string;
  detail: string;
  fix: string;
  correlationId: string;
  status: number;

  constructor(opts: { code?: string; message: string; detail?: string; fix?: string; correlationId?: string; status: number }) {
    super(opts.message);
    this.name = 'ApiError';
    this.code = opts.code || '';
    this.detail = opts.detail || opts.message;
    this.fix = opts.fix || '';
    this.correlationId = opts.correlationId || '';
    this.status = opts.status;
  }
}

class ApiClient {
  /**
   * Core request method — sends httpOnly cookie automatically.
   * No token management. No Authorization header. Browser handles cookies.
   */
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    // Auto-inject tenant_id from in-memory cache (set by useTenantSwitcher)
    let finalPath = path;
    const skipTenantPaths = ['/auth/', '/onboard/', '/health', '/tenants/', '/sla-policies', '/billing', '/features'];
    const shouldInject = !skipTenantPaths.some(p => path.startsWith(p)) && !path.includes('tenant_id=');
    if (shouldInject) {
      const selectedTenant = window.__kavachiq_selected_tenant;
      if (selectedTenant) {
        const separator = path.includes('?') ? '&' : '?';
        finalPath = `${path}${separator}tenant_id=${selectedTenant}`;
      }
    }

    const res = await fetch(`${API_BASE}${finalPath}`, {
      ...options,
      headers,
      credentials: 'include', // Send httpOnly cookie automatically
    });

    if (res.status === 401) {
      // Session expired or not authenticated — React Router handles redirect
      throw new ApiError({ message: 'Session expired', status: 401 });
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const err = body.error || {};
      throw new ApiError({
        code: err.code || '',
        message: err.message || body.detail || `HTTP ${res.status}`,
        detail: err.detail || body.detail || res.statusText,
        fix: err.fix || '',
        correlationId: err.correlation_id || res.headers.get('X-Correlation-ID') || '',
        status: res.status,
      });
    }

    return res.json();
  }

  // Backward compatibility stubs — no-ops in BFF mode (cookie handles auth)
  // These exist so components that haven't been fully migrated don't crash.
  // TODO: Remove after all callers are updated.
  getToken(): string | null { return null; }  // Cookie is httpOnly — JS can't read it
  setToken(_token: string) {}  // Cookie set by backend, not JS
  clearToken() {}              // Cookie cleared by backend /auth/logout

  get<T>(path: string) { return this.request<T>(path); }
  post<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }); }
  put<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }); }
  del<T>(path: string) { return this.request<T>(path, { method: 'DELETE' }); }

  /**
   * Login — backend sets httpOnly cookie. Frontend stores nothing.
   * Returns user info for AuthContext state.
   */
  async login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
      credentials: 'include', // Receive + store httpOnly cookie
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const err = body.error || {};
      throw new ApiError({
        code: err.code || 'E2001',
        message: err.message || 'Invalid credentials',
        fix: err.fix || 'Check your username and password',
        correlationId: err.correlation_id || '',
        status: res.status,
      });
    }
    return res.json();
  }

  /**
   * Logout — backend destroys Redis session + clears cookie.
   */
  async logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Logout best-effort
    }
  }

  /**
   * Check if user has an active session (for AuthContext).
   * Calls /auth/session — if 200, user is authenticated.
   */
  async checkSession() {
    try {
      const data = await this.get<any>('/auth/session');
      return data;
    } catch {
      return null;
    }
  }

  register(data: { username: string; email: string; password: string; full_name?: string; role?: string }) {
    return this.post('/auth/register', data);
  }
}

export const api = new ApiClient();
