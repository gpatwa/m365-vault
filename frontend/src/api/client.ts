// API base URL resolution order:
// 1. Runtime config (injected by nginx config.js in Docker/Azure)
// 2. Vite build-time env (VITE_API_BASE)
// 3. Dev fallback (localhost)
declare global {
  interface Window {
    __RUNTIME_CONFIG__?: { API_BASE: string };
  }
}
const API_BASE =
  window.__RUNTIME_CONFIG__?.API_BASE
  ? `${window.__RUNTIME_CONFIG__.API_BASE}/api`
  : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

/**
 * Structured API error with error code, message, fix suggestion, and correlation ID.
 * Matches the backend Shieldio error response format.
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
  private token: string | null = null;

  constructor() {
    // Try sessionStorage first, fall back to localStorage for migration
    this.token = sessionStorage.getItem('token') || localStorage.getItem('token');
    // Migrate from localStorage to sessionStorage
    if (!sessionStorage.getItem('token') && localStorage.getItem('token')) {
      sessionStorage.setItem('token', localStorage.getItem('token')!);
      localStorage.removeItem('token');
    }
  }

  setToken(token: string) {
    this.token = token;
    sessionStorage.setItem('token', token);
    localStorage.removeItem('token'); // Clean up legacy
  }

  clearToken() {
    this.token = null;
    sessionStorage.removeItem('token');
    localStorage.removeItem('token');
  }

  getToken() {
    return this.token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new ApiError({ message: 'Unauthorized', status: 401 });
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      // Parse structured error (new format) or legacy format
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

  get<T>(path: string) { return this.request<T>(path); }
  post<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }); }
  put<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }); }
  del<T>(path: string) { return this.request<T>(path, { method: 'DELETE' }); }

  // Auth
  async login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
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
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  }

  register(data: { username: string; email: string; password: string; full_name?: string; role?: string }) {
    return this.post('/auth/register', data);
  }
}

export const api = new ApiClient();
