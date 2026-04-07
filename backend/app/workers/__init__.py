"""Worker Registry — central registration of all workload workers.

Provides lazy-loaded worker class resolution. Adding a new workload:
1. Create worker class extending BaseWorker
2. Add entry to WORKER_REGISTRY
3. That's it — backup engine, restore engine, discovery, and APIs all use this registry.

No hard-coded imports needed in engines or APIs.
"""
import importlib
import logging
from typing import Type

from app.models.protected_object import WorkloadType

logger = logging.getLogger(__name__)

# Maps WorkloadType → (module_path, class_name)
# Lazy imports — modules loaded only when first requested
WORKER_REGISTRY: dict[WorkloadType, tuple[str, str]] = {
    WorkloadType.EXCHANGE: ("app.workers.exchange_worker", "ExchangeWorker"),
    WorkloadType.ONEDRIVE: ("app.workers.onedrive_worker", "OneDriveWorker"),
    WorkloadType.SHAREPOINT: ("app.workers.sharepoint_worker", "SharePointWorker"),
    WorkloadType.TEAMS: ("app.workers.teams_worker", "TeamsWorker"),
    WorkloadType.ENTRA_ID: ("app.workers.entra_id_worker", "EntraIDWorker"),
}

# Cache loaded classes to avoid repeated importlib calls
_worker_class_cache: dict[WorkloadType, Type] = {}


def get_worker_class(workload_type: WorkloadType) -> Type:
    """Lazy-load and return the worker class for a workload type.

    Caches loaded classes so importlib.import_module is called only once per type.
    Raises ValueError if workload type is not registered.
    """
    if workload_type in _worker_class_cache:
        return _worker_class_cache[workload_type]

    entry = WORKER_REGISTRY.get(workload_type)
    if not entry:
        raise ValueError(
            f"No worker registered for workload type '{workload_type.value}'. "
            f"Available: {[wt.value for wt in WORKER_REGISTRY.keys()]}"
        )

    module_path, class_name = entry
    try:
        module = importlib.import_module(module_path)
        worker_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Failed to load worker {class_name} from {module_path}: {e}"
        ) from e

    _worker_class_cache[workload_type] = worker_class
    logger.debug(f"Loaded worker: {class_name} for {workload_type.value}")
    return worker_class


def list_registered_workloads() -> list[str]:
    """Return list of registered workload type values."""
    return [wt.value for wt in WORKER_REGISTRY.keys()]


def is_workload_registered(workload_type: WorkloadType) -> bool:
    """Check if a workload type has a registered worker."""
    return workload_type in WORKER_REGISTRY
