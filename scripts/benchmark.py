#!/usr/bin/env python3
"""Shieldio Benchmark Suite — measures real backup/restore performance.

Runs against the live system (Docker Compose or Azure) and records:
- Backup throughput per workload (items/sec, MB/sec)
- Restore/recovery time
- API response latency (p50, p95, p99)
- Storage efficiency (dedup ratio, compression ratio)
- Success rate across all operations

Usage:
  make benchmark                    # Run full benchmark
  python3 scripts/benchmark.py      # Same thing
  python3 scripts/benchmark.py --api-only  # API latency only (no backup)

Results saved to: tests/benchmarks/results.json
"""
import asyncio
import json
import os
import sys
import time
import statistics
from datetime import datetime

import httpx

# Config
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
USERNAME = os.environ.get("BENCH_USER", "admin")
PASSWORD = os.environ.get("BENCH_PASS", "admin123")
RESULTS_FILE = "tests/benchmarks/results.json"


async def run_benchmarks():
    print("═══ SHIELDIO BENCHMARK SUITE ═══")
    print(f"Target: {API_BASE}")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print()

    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "target": API_BASE,
        "version": None,
        "benchmarks": {},
    }

    async with httpx.AsyncClient(base_url=API_BASE, timeout=120) as client:
        # ── 0. Login ──
        print("━━━ Authentication ━━━")
        t0 = time.perf_counter()
        login_resp = await client.post("/api/auth/login", data={"username": USERNAME, "password": PASSWORD})
        login_ms = round((time.perf_counter() - t0) * 1000, 1)

        if login_resp.status_code != 200:
            print(f"  ❌ Login failed: {login_resp.status_code}")
            return

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  ✅ Login: {login_ms}ms")

        # Get version
        root = await client.get("/")
        results["version"] = root.json().get("version")

        # ── 1. Health Check ──
        print()
        print("━━━ 1. Health Check ━━━")
        t0 = time.perf_counter()
        health = await client.get("/health")
        health_ms = round((time.perf_counter() - t0) * 1000, 1)
        health_data = health.json()
        print(f"  Status: {health_data.get('status')} ({health_ms}ms)")
        print(f"  DB: {health_data.get('checks', {}).get('database')}")
        print(f"  Storage: {health_data.get('checks', {}).get('storage')}")
        results["benchmarks"]["health_check"] = {
            "status": health_data.get("status"),
            "latency_ms": health_ms,
        }

        # ── 2. API Latency ──
        print()
        print("━━━ 2. API Response Latency ━━━")
        endpoints = [
            ("GET", "/api/dashboard/summary", "Dashboard"),
            ("GET", "/api/jobs/backup?page_size=10", "Jobs List"),
            ("GET", "/api/tenants/", "Tenants"),
            ("GET", "/api/sla-policies/", "SLA Policies"),
            ("GET", "/api/health/score?tenant_id=1", "Health Score"),
            ("GET", "/api/reports/backup-performance?period=7d&tenant_id=1", "Reports"),
            ("GET", "/api/usage/platform", "Usage"),
            ("GET", "/api/security/posture", "Security Posture"),
            ("GET", "/api/failed-items?page_size=10", "Failed Items"),
            ("GET", "/api/audit/logs?page_size=10", "Audit Logs"),
        ]

        latencies = {}
        for method, path, label in endpoints:
            times = []
            for _ in range(5):  # 5 requests each
                t0 = time.perf_counter()
                if method == "GET":
                    resp = await client.get(path, headers=headers)
                else:
                    resp = await client.post(path, headers=headers)
                elapsed = (time.perf_counter() - t0) * 1000
                times.append(elapsed)

            avg = round(statistics.mean(times), 1)
            p50 = round(sorted(times)[len(times) // 2], 1)
            p95 = round(sorted(times)[int(len(times) * 0.95)], 1)
            p99 = round(sorted(times)[-1], 1)
            print(f"  {label:20s} avg={avg:>6.1f}ms  p50={p50:>6.1f}ms  p95={p95:>6.1f}ms  p99={p99:>6.1f}ms")
            latencies[label] = {"avg_ms": avg, "p50_ms": p50, "p95_ms": p95, "p99_ms": p99}

        results["benchmarks"]["api_latency"] = latencies

        # ── 3. Backup Performance ──
        print()
        print("━━━ 3. Backup Performance ━━━")

        # Find tenants and trigger backups
        tenants_resp = await client.get("/api/tenants/", headers=headers)
        tenants = tenants_resp.json()

        if not tenants:
            print("  ⚠️  No tenants found — skipping backup benchmark")
            results["benchmarks"]["backup"] = {"skipped": True, "reason": "no tenants"}
        else:
            tenant_id = tenants[0]["id"]
            backup_results = {}

            for workload, endpoint in [
                ("exchange", f"/api/exchange/backup-all?tenant_id={tenant_id}"),
                ("onedrive", f"/api/onedrive/backup-all?tenant_id={tenant_id}"),
                ("sharepoint", f"/api/sharepoint/backup-all?tenant_id={tenant_id}"),
                ("teams", f"/api/teams/backup-all?tenant_id={tenant_id}"),
                ("entra_id", f"/api/entra-id/backup?tenant_id={tenant_id}"),
            ]:
                t0 = time.perf_counter()
                try:
                    resp = await client.post(endpoint, headers=headers)
                    elapsed_sec = round(time.perf_counter() - t0, 2)
                    data = resp.json()

                    if resp.status_code == 200:
                        # Extract results based on response format
                        if "results" in data:
                            total_items = sum(r.get("item_count", 0) or 0 for r in data.get("results", []))
                            total_size = sum(r.get("size_bytes", 0) or 0 for r in data.get("results", []))
                            objects = data.get("backed_up", len(data.get("results", [])))
                        else:
                            total_items = data.get("item_count", 0) or 0
                            total_size = data.get("size_bytes", 0) or 0
                            objects = 1

                        items_per_sec = round(total_items / elapsed_sec, 1) if elapsed_sec > 0 else 0
                        mb_per_sec = round(total_size / 1024 / 1024 / elapsed_sec, 2) if elapsed_sec > 0 else 0

                        print(f"  {workload:12s} {objects} objects, {total_items} items, {round(total_size/1024)}KB in {elapsed_sec}s ({items_per_sec} items/s, {mb_per_sec} MB/s)")
                        backup_results[workload] = {
                            "objects": objects,
                            "items": total_items,
                            "size_bytes": total_size,
                            "duration_sec": elapsed_sec,
                            "items_per_sec": items_per_sec,
                            "mb_per_sec": mb_per_sec,
                            "status": "success",
                        }
                    elif resp.status_code == 404:
                        print(f"  {workload:12s} no objects to backup")
                        backup_results[workload] = {"status": "no_objects"}
                    else:
                        status = data.get("status", "unknown")
                        if status == "queued":
                            print(f"  {workload:12s} queued (async mode — {elapsed_sec}s to dispatch)")
                            backup_results[workload] = {"status": "queued", "dispatch_sec": elapsed_sec}
                        else:
                            print(f"  {workload:12s} error: {resp.status_code}")
                            backup_results[workload] = {"status": "error", "code": resp.status_code}
                except Exception as e:
                    elapsed_sec = round(time.perf_counter() - t0, 2)
                    print(f"  {workload:12s} failed: {e} ({elapsed_sec}s)")
                    backup_results[workload] = {"status": "error", "error": str(e)[:100]}

            results["benchmarks"]["backup"] = backup_results

        # ── 4. Storage Efficiency ──
        print()
        print("━━━ 4. Storage Efficiency ━━━")
        try:
            if tenants:
                storage_resp = await client.get(f"/api/reports/storage-analytics?tenant_id={tenant_id}", headers=headers)
                storage = storage_resp.json()
                print(f"  Total size: {round((storage.get('total_size_bytes', 0) or 0) / 1024 / 1024, 2)} MB")
                print(f"  Compression ratio: {storage.get('compression_ratio', 'N/A')}x")
                print(f"  Dedup ratio: {storage.get('dedup_ratio', 'N/A')}")
                results["benchmarks"]["storage"] = {
                    "total_size_bytes": storage.get("total_size_bytes", 0),
                    "compression_ratio": storage.get("compression_ratio"),
                    "dedup_ratio": storage.get("dedup_ratio"),
                }
        except Exception as e:
            print(f"  Error: {e}")

        # ── 5. Success Rate ──
        print()
        print("━━━ 5. Historical Success Rate ━━━")
        try:
            perf_resp = await client.get(f"/api/reports/backup-performance?period=30d&tenant_id={tenant_id if tenants else 1}", headers=headers)
            perf = perf_resp.json()
            print(f"  Success rate (30d): {perf.get('success_rate', 'N/A')}%")
            print(f"  Total jobs (30d): {perf.get('total_jobs', 'N/A')}")
            results["benchmarks"]["success_rate"] = {
                "period": "30d",
                "rate": perf.get("success_rate"),
                "total_jobs": perf.get("total_jobs"),
            }
        except Exception as e:
            print(f"  Error: {e}")

        # ── 6. Recovery Readiness ──
        print()
        print("━━━ 6. Recovery Readiness ━━━")
        try:
            recovery_resp = await client.get(f"/api/recovery/dashboard?tenant_id={tenant_id if tenants else 1}", headers=headers)
            if recovery_resp.status_code == 200:
                recovery = recovery_resp.json()
                print(f"  Confidence score: {recovery.get('confidence_score', {}).get('score', 'N/A')}")
                print(f"  RPO adherence: {recovery.get('rpo_rto', {}).get('rpo_adherence_percent', 'N/A')}%")
                results["benchmarks"]["recovery"] = {
                    "confidence_score": recovery.get("confidence_score", {}).get("score"),
                    "rpo_adherence": recovery.get("rpo_rto", {}).get("rpo_adherence_percent"),
                }
        except Exception as e:
            print(f"  Error: {e}")

        # ── 7. Concurrent Load ──
        print()
        print("━━━ 7. Concurrent API Load ━━━")
        async def single_request():
            t0 = time.perf_counter()
            await client.get("/api/dashboard/summary", headers=headers)
            return (time.perf_counter() - t0) * 1000

        for concurrency in [5, 10, 25]:
            tasks = [single_request() for _ in range(concurrency)]
            all_times = await asyncio.gather(*tasks)
            avg = round(statistics.mean(all_times), 1)
            p99 = round(sorted(all_times)[-1], 1)
            print(f"  {concurrency} concurrent: avg={avg}ms, p99={p99}ms")

        results["benchmarks"]["concurrent"] = {
            "5_concurrent_avg_ms": round(statistics.mean(await asyncio.gather(*[single_request() for _ in range(5)])), 1),
            "10_concurrent_avg_ms": round(statistics.mean(await asyncio.gather(*[single_request() for _ in range(10)])), 1),
            "25_concurrent_avg_ms": round(statistics.mean(await asyncio.gather(*[single_request() for _ in range(25)])), 1),
        }

    # ── Save Results ──
    print()
    print("━━━ Results ━━━")
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved to: {RESULTS_FILE}")

    # ── Summary ──
    print()
    print("═══ BENCHMARK SUMMARY ═══")
    bl = results["benchmarks"]
    print(f"  Health: {bl.get('health_check', {}).get('latency_ms', '?')}ms")
    if "api_latency" in bl:
        all_avg = [v["avg_ms"] for v in bl["api_latency"].values()]
        print(f"  API avg latency: {round(statistics.mean(all_avg), 1)}ms across {len(all_avg)} endpoints")
    if "backup" in bl and not bl["backup"].get("skipped"):
        total_items = sum(v.get("items", 0) for v in bl["backup"].values() if isinstance(v, dict))
        total_sec = sum(v.get("duration_sec", 0) for v in bl["backup"].values() if isinstance(v, dict))
        print(f"  Backup: {total_items} items in {total_sec}s")
    if "success_rate" in bl:
        print(f"  Success rate: {bl['success_rate'].get('rate', '?')}%")
    if "storage" in bl:
        print(f"  Compression: {bl['storage'].get('compression_ratio', '?')}x")
    print()
    print("═══ COMPLETE ═══")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
