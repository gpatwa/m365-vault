/**
 * Shieldio Load Test Suite — k6
 *
 * Tests API performance under load with 3 scenarios:
 *
 * 1. Smoke Test: 1 user, 30s — verify basic functionality
 * 2. Load Test: 50 users ramping up over 5 min — normal traffic
 * 3. Stress Test: 200 users — find breaking point
 *
 * Usage:
 *   k6 run tests/load/k6-load-test.js                        # smoke test (default)
 *   k6 run tests/load/k6-load-test.js --env SCENARIO=load    # load test
 *   k6 run tests/load/k6-load-test.js --env SCENARIO=stress  # stress test
 *
 * Environment:
 *   BASE_URL: API base URL (default: http://localhost:8000)
 *   SCENARIO: smoke | load | stress (default: smoke)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ── Configuration ──
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'smoke';

// ── Custom Metrics ──
const loginDuration = new Trend('login_duration', true);
const dashboardDuration = new Trend('dashboard_duration', true);
const jobsListDuration = new Trend('jobs_list_duration', true);
const healthCheckDuration = new Trend('health_check_duration', true);
const errorRate = new Rate('errors');
const requestCount = new Counter('total_requests');

// ── Scenarios ──
const scenarios = {
  smoke: {
    executor: 'constant-vus',
    vus: 1,
    duration: '30s',
  },
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '1m', target: 10 },   // Ramp up to 10
      { duration: '2m', target: 50 },   // Ramp to 50
      { duration: '2m', target: 50 },   // Stay at 50
      { duration: '1m', target: 0 },    // Ramp down
    ],
  },
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '1m', target: 50 },   // Ramp up
      { duration: '2m', target: 100 },  // Push harder
      { duration: '2m', target: 200 },  // Stress level
      { duration: '1m', target: 0 },    // Ramp down
    ],
  },
};

export const options = {
  scenarios: { default: scenarios[SCENARIO] || scenarios.smoke },
  thresholds: {
    http_req_duration: ['p(95)<2000'],      // 95% of requests < 2s
    http_req_failed: ['rate<0.05'],          // <5% error rate
    login_duration: ['p(95)<1000'],          // Login < 1s at p95
    dashboard_duration: ['p(95)<1500'],      // Dashboard < 1.5s at p95
    jobs_list_duration: ['p(95)<1000'],      // Jobs list < 1s at p95
    health_check_duration: ['p(95)<500'],    // Health < 500ms at p95
    errors: ['rate<0.05'],                   // <5% errors
  },
};

// ── Setup: Login once and share token ──
export function setup() {
  // Register test user if needed
  http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({
    username: `loadtest_${Date.now()}`,
    email: `loadtest_${Date.now()}@test.com`,
    password: 'LoadTest123',
    role: 'admin',
  }), { headers: { 'Content-Type': 'application/json' } });

  // Login
  const loginRes = http.post(`${BASE_URL}/api/auth/login`,
    'username=admin&password=admin123',
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );

  if (loginRes.status !== 200) {
    // Try registering admin first
    http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({
      username: 'admin',
      email: 'admin@test.com',
      password: 'admin123',
      role: 'admin',
    }), { headers: { 'Content-Type': 'application/json' } });

    const retryLogin = http.post(`${BASE_URL}/api/auth/login`,
      'username=admin&password=admin123',
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    return { token: retryLogin.json().access_token };
  }

  return { token: loginRes.json().access_token };
}

// ── Main Test Flow ──
export default function (data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // 1. Health Check (unauthenticated)
  group('Health Check', () => {
    const res = http.get(`${BASE_URL}/health`);
    healthCheckDuration.add(res.timings.duration);
    requestCount.add(1);
    const passed = check(res, {
      'health: status 200': (r) => r.status === 200,
      'health: status healthy': (r) => r.json().status === 'healthy',
      'health: has correlation ID': (r) => r.headers['X-Correlation-Id'] !== undefined,
    });
    errorRate.add(!passed);
  });

  sleep(0.5);

  // 2. Login
  group('Login', () => {
    const res = http.post(`${BASE_URL}/api/auth/login`,
      'username=admin&password=admin123',
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    loginDuration.add(res.timings.duration);
    requestCount.add(1);
    const passed = check(res, {
      'login: status 200': (r) => r.status === 200,
      'login: has access_token': (r) => r.json().access_token !== undefined,
      'login: has refresh_token': (r) => r.json().refresh_token !== undefined,
    });
    errorRate.add(!passed);
  });

  sleep(0.5);

  // 3. Dashboard Summary
  group('Dashboard', () => {
    const res = http.get(`${BASE_URL}/api/dashboard/summary`, { headers });
    dashboardDuration.add(res.timings.duration);
    requestCount.add(1);
    const passed = check(res, {
      'dashboard: status 200': (r) => r.status === 200,
      'dashboard: has workloads': (r) => r.json().workloads !== undefined,
    });
    errorRate.add(!passed);
  });

  sleep(0.3);

  // 4. Backup Jobs List
  group('Jobs List', () => {
    const res = http.get(`${BASE_URL}/api/jobs/backup?page_size=20`, { headers });
    jobsListDuration.add(res.timings.duration);
    requestCount.add(1);
    const passed = check(res, {
      'jobs: status 200': (r) => r.status === 200,
      'jobs: has total': (r) => r.json().total !== undefined,
      'jobs: has items': (r) => r.json().items !== undefined,
    });
    errorRate.add(!passed);
  });

  sleep(0.3);

  // 5. Failed Summary
  group('Failed Summary', () => {
    const res = http.get(`${BASE_URL}/api/jobs/failed-summary`, { headers });
    requestCount.add(1);
    check(res, { 'failed-summary: status 200': (r) => r.status === 200 });
  });

  sleep(0.3);

  // 6. Audit Logs
  group('Audit Logs', () => {
    const res = http.get(`${BASE_URL}/api/audit/logs?page_size=20`, { headers });
    requestCount.add(1);
    check(res, { 'audit: status 200': (r) => r.status === 200 });
  });

  sleep(0.3);

  // 7. Health Score
  group('Health Score', () => {
    const res = http.get(`${BASE_URL}/api/health/score?tenant_id=1`, { headers });
    requestCount.add(1);
    check(res, {
      'health-score: status 200': (r) => r.status === 200,
      'health-score: has score': (r) => r.json().score !== undefined,
    });
  });

  sleep(0.3);

  // 8. Alerts Config
  group('Alerts Config', () => {
    const res = http.get(`${BASE_URL}/api/alerts/config`, { headers });
    requestCount.add(1);
    check(res, { 'alerts: status 200': (r) => r.status === 200 });
  });

  sleep(0.3);

  // 9. License/Usage
  group('License', () => {
    const res = http.get(`${BASE_URL}/api/usage/license`, { headers });
    requestCount.add(1);
    check(res, { 'license: status 200': (r) => r.status === 200 });
  });

  sleep(0.5);
}

// ── Teardown: Summary ──
export function teardown(data) {
  console.log(`\n═══ Load Test Complete (${SCENARIO}) ═══`);
  console.log(`Base URL: ${BASE_URL}`);
}
