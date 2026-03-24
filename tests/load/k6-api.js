/**
 * M365 Vault — k6 Load Test Suite
 *
 * Tests API performance under load for scale readiness.
 *
 * Usage:
 *   k6 run tests/load/k6-api.js                    # default (10 VUs, 30s)
 *   k6 run --vus 50 --duration 60s tests/load/k6-api.js  # medium load
 *   k6 run --vus 200 --duration 300s tests/load/k6-api.js # stress test
 *
 * Environment:
 *   BASE_URL  - API base URL (default: http://localhost:8000)
 *   USERNAME  - Login username (default: admin)
 *   PASSWORD  - Login password (default: admin123)
 *   TENANT_ID - Tenant ID to test (default: 2)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const dashboardDuration = new Trend('dashboard_duration');
const listDuration = new Trend('list_duration');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const USERNAME = __ENV.USERNAME || 'admin';
const PASSWORD = __ENV.PASSWORD || 'admin123';
const TENANT_ID = __ENV.TENANT_ID || '2';

export const options = {
  stages: [
    { duration: '10s', target: 10 },   // Ramp up
    { duration: '30s', target: 10 },   // Hold
    { duration: '10s', target: 50 },   // Spike
    { duration: '20s', target: 50 },   // Hold spike
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],   // 95% of requests < 2s
    http_req_failed: ['rate<0.05'],      // <5% error rate
    errors: ['rate<0.1'],                // Custom error rate
    login_duration: ['p(95)<1000'],      // Login < 1s
    dashboard_duration: ['p(95)<1500'],  // Dashboard < 1.5s
    list_duration: ['p(95)<1000'],       // List APIs < 1s
  },
};

// Get auth token
function login() {
  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/auth/login`, `username=${USERNAME}&password=${PASSWORD}`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  loginDuration.add(Date.now() - start);

  check(res, { 'login success': (r) => r.status === 200 });
  if (res.status !== 200) {
    errorRate.add(1);
    return null;
  }
  errorRate.add(0);
  return JSON.parse(res.body).access_token;
}

export default function () {
  const token = login();
  if (!token) return;

  const headers = { Authorization: `Bearer ${token}` };

  // ── Health Check ──
  group('Health Check', function () {
    const res = http.get(`${BASE_URL}/health`);
    check(res, { 'health ok': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Dashboard ──
  group('Dashboard', function () {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/dashboard/summary`, { headers });
    dashboardDuration.add(Date.now() - start);
    check(res, {
      'dashboard 200': (r) => r.status === 200,
      'has workloads': (r) => JSON.parse(r.body).workloads !== undefined,
    });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Workload List APIs (paginated, sorted) ──
  group('Exchange Mailboxes', function () {
    const start = Date.now();
    const res = http.get(
      `${BASE_URL}/api/exchange/mailboxes?tenant_id=${TENANT_ID}&page=1&page_size=25&sort_by=display_name&sort_order=asc`,
      { headers }
    );
    listDuration.add(Date.now() - start);
    check(res, { 'exchange 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  group('OneDrive Accounts', function () {
    const start = Date.now();
    const res = http.get(
      `${BASE_URL}/api/onedrive/accounts?tenant_id=${TENANT_ID}&page=1&page_size=25`,
      { headers }
    );
    listDuration.add(Date.now() - start);
    check(res, { 'onedrive 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  group('SharePoint Sites', function () {
    const start = Date.now();
    const res = http.get(
      `${BASE_URL}/api/sharepoint/sites?tenant_id=${TENANT_ID}&page=1&page_size=25`,
      { headers }
    );
    listDuration.add(Date.now() - start);
    check(res, { 'sharepoint 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Jobs ──
  group('Backup Jobs', function () {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/jobs/backup?page_size=25`, { headers });
    listDuration.add(Date.now() - start);
    check(res, { 'jobs 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Health Score ──
  group('Health Score', function () {
    const res = http.get(`${BASE_URL}/api/health/score?tenant_id=${TENANT_ID}`, { headers });
    check(res, { 'health score 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Failed Items ──
  group('Failed Items', function () {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/failed-items?page=1&page_size=25`, { headers });
    listDuration.add(Date.now() - start);
    check(res, { 'failed items 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Reports ──
  group('Reports - Backup Performance', function () {
    const res = http.get(
      `${BASE_URL}/api/reports/backup-performance?tenant_id=${TENANT_ID}&period=30d`,
      { headers }
    );
    check(res, { 'report 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  // ── Search ──
  group('Global Search', function () {
    const res = http.get(`${BASE_URL}/api/search/global?q=Alex&page_size=10`, { headers });
    check(res, { 'search 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200 ? 1 : 0);
  });

  sleep(1); // Think time between iterations
}

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  const errorPct = data.metrics.http_req_failed.values.rate * 100;
  const totalReqs = data.metrics.http_reqs.values.count;
  const rps = data.metrics.http_reqs.values.rate;

  console.log('\n═══ M365 VAULT LOAD TEST RESULTS ═══');
  console.log(`Total Requests: ${totalReqs}`);
  console.log(`Requests/sec:   ${rps.toFixed(1)}`);
  console.log(`P95 Latency:    ${p95.toFixed(0)}ms`);
  console.log(`Error Rate:     ${errorPct.toFixed(2)}%`);
  console.log('');
  console.log('Thresholds:');
  Object.entries(data.metrics).forEach(([name, metric]) => {
    if (metric.thresholds) {
      Object.entries(metric.thresholds).forEach(([threshold, passed]) => {
        console.log(`  ${passed.ok ? '✅' : '❌'} ${name}: ${threshold}`);
      });
    }
  });

  return {
    'stdout': '',
    'tests/load/results.json': JSON.stringify(data, null, 2),
  };
}
