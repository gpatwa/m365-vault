"""Tests for Worker Registry — central worker class resolution.

Verifies lazy-loading, caching, and error handling for the worker registry.
"""
import pytest
from app.models.protected_object import WorkloadType


@pytest.mark.asyncio
async def test_registry_has_all_workloads():
    """All 5 M365 workload types are registered."""
    from app.workers import WORKER_REGISTRY
    expected = {WorkloadType.EXCHANGE, WorkloadType.ONEDRIVE, WorkloadType.SHAREPOINT,
                WorkloadType.TEAMS, WorkloadType.ENTRA_ID}
    assert set(WORKER_REGISTRY.keys()) == expected


@pytest.mark.asyncio
async def test_get_worker_class_loads_exchange():
    """get_worker_class returns ExchangeWorker for EXCHANGE type."""
    from app.workers import get_worker_class
    cls = get_worker_class(WorkloadType.EXCHANGE)
    assert cls.__name__ == "ExchangeWorker"


@pytest.mark.asyncio
async def test_get_worker_class_loads_entra_id():
    """get_worker_class returns EntraIDWorker for ENTRA_ID type."""
    from app.workers import get_worker_class
    cls = get_worker_class(WorkloadType.ENTRA_ID)
    assert cls.__name__ == "EntraIDWorker"


@pytest.mark.asyncio
async def test_get_worker_class_caches():
    """Subsequent calls return the same class object (cached)."""
    from app.workers import get_worker_class
    cls1 = get_worker_class(WorkloadType.ONEDRIVE)
    cls2 = get_worker_class(WorkloadType.ONEDRIVE)
    assert cls1 is cls2


@pytest.mark.asyncio
async def test_get_worker_class_invalid_raises():
    """Invalid workload type raises ValueError."""
    from app.workers import get_worker_class, WORKER_REGISTRY
    # Use a type that's definitely not registered
    from enum import Enum
    class FakeType(str, Enum):
        FAKE = "fake"
    with pytest.raises((ValueError, KeyError)):
        get_worker_class(FakeType.FAKE)


@pytest.mark.asyncio
async def test_list_registered_workloads():
    """list_registered_workloads returns string values for all 5 workloads."""
    from app.workers import list_registered_workloads
    workloads = list_registered_workloads()
    assert len(workloads) == 5
    # Check workload values are present (case-insensitive)
    lower = [w.lower() for w in workloads]
    assert "exchange" in lower
    assert "entra_id" in lower


@pytest.mark.asyncio
async def test_is_workload_registered():
    """is_workload_registered returns correct boolean."""
    from app.workers import is_workload_registered
    assert is_workload_registered(WorkloadType.EXCHANGE) is True
    assert is_workload_registered(WorkloadType.TEAMS) is True


@pytest.mark.asyncio
async def test_all_workers_inherit_base():
    """All registered workers should inherit from BaseWorker."""
    from app.workers import get_worker_class, WORKER_REGISTRY
    from app.workers.base_worker import BaseWorker

    for wt in WORKER_REGISTRY:
        cls = get_worker_class(wt)
        assert issubclass(cls, BaseWorker), f"{cls.__name__} does not inherit from BaseWorker"
