/**
 * Shieldio — k6 Stress Test
 *
 * Tests system behavior under increasing load to find breaking point.
 * Usage: k6 run tests/load/k6-stress.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp to 10 users
    { duration: '2m', target: 25 },   // Ramp to 25 users
    { duration: '2m', target: 50 },   // Ramp to 50 users
    { duration: '2m', target: 100 },  // Ramp to 100 users (stress)
    { duration: '1m', target: 0 },    // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% under 2s even under stress
    http_req_failed: ['rate<0.05'],      // Less than 5% failures
  },
};

export function setup() {
  const loginRes = http.post(`${BASE_URL}/api/auth/login`,
    'username=admin&password=admin123',
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
  return { token: loginRes.json('access_token') };
}

export default function (data) {
  const headers = { 'Authorization': `Bearer ${data.token}` };

  // Mix of endpoints simulating real usage
  const endpoints = [
    '/health',
    '/api/dashboard/summary',
    '/api/jobs/backup?page_size=20',
    '/api/health/score?tenant_id=2',
    '/api/reports/backup-performance?period=7d&tenant_id=2',
    '/api/reports/storage-analytics?tenant_id=2',
    '/api/usage/platform',
    '/api/audit/logs?page_size=10',
    '/api/failed-items?page_size=10',
    '/api/alerts/config',
  ];

  const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
  const needsAuth = !endpoint.startsWith('/health');

  const res = http.get(`${BASE_URL}${endpoint}`, needsAuth ? { headers } : {});
  check(res, {
    [`${endpoint}: not 5xx`]: (r) => r.status < 500,
  });

  sleep(0.5 + Math.random());
}
