"""Benchmark results API — serves latest performance data."""
import json
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/benchmarks", tags=["Benchmarks"])

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "benchmarks", "results.json")
# Also check project root
RESULTS_FILE_ALT = "tests/benchmarks/results.json"


@router.get("/latest")
async def latest_benchmarks():
    """Return latest benchmark results (public — no auth required for landing page)."""
    for path in [RESULTS_FILE, RESULTS_FILE_ALT, "/app/tests/benchmarks/results.json"]:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception:
            continue

    return {
        "status": "no_results",
        "message": "No benchmark results available. Run: make benchmark",
    }
