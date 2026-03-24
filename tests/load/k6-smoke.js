/**
 * M365 Vault — k6 Smoke Test
 *
 * Quick validation that core endpoints respond correctly under light load.
 * Usage: k6 run tests/load/k6-smoke.js
 * Options: k6 run --env BASE_URL=https://your-prod.azurecontainerapps.io tests/load/k6-smoke.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp up to 5 users
    { duration: '1m', target: 5 },     // Hold at 5 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],     // Less than 1% failures
  },
};

let authToken = null;

export function setup() {
  // Login and get token
  const loginRes = http.post(`${BASE_URL}/api/auth/login`,
    'username=admin&password=admin123',
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
  check(loginRes, { 'login succeeded': (r) => r.status === 200 });
  return { token: loginRes.json('access_token') };
}

export default function (data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // 1. Health check (unauthenticated)
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health: status 200': (r) => r.status === 200,
    'health: is healthy': (r) => r.json('status') === 'healthy',
  });

  // 2. Dashboard summary
  const dashRes = http.get(`${BASE_URL}/api/dashboard/summary`, { headers });
  check(dashRes, {
    'dashboard: status 200': (r) => r.status === 200,
    'dashboard: has workloads': (r) => r.json('workloads') !== null,
  });

  // 3. Backup jobs list
  const jobsRes = http.get(`${BASE_URL}/api/jobs/backup?page_size=20`, { headers });
  check(jobsRes, {
    'jobs: status 200': (r) => r.status === 200,
    'jobs: has total': (r) => r.json('total') >= 0,
  });

  // 4. Health score
  const scoreRes = http.get(`${BASE_URL}/api/health/score?tenant_id=2`, { headers });
  check(scoreRes, {
    'health score: status 200': (r) => r.status === 200,
    'health score: valid': (r) => r.json('score') >= 0 && r.json('score') <= 100,
  });

  // 5. Reports
  const reportsRes = http.get(`${BASE_URL}/api/reports/backup-performance?period=7d&tenant_id=2`, { headers });
  check(reportsRes, {
    'reports: status 200': (r) => r.status === 200,
  });

  sleep(1);
}
