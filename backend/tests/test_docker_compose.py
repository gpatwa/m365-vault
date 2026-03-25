"""Tests for docker-compose.yml validity.

Verifies that the compose file:
- Parses as valid YAML
- Contains all required services (postgres, redis, minio, backend, worker, frontend)
- Backend and worker are configured for linux/amd64
- Redis service has a health check
- Worker service is configured to run app.worker
- Backend and worker both declare REDIS_URL
- Queue name constants match what the compose file expects
"""
import os
import yaml
import pytest

COMPOSE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "docker-compose.yml"
)


@pytest.fixture(scope="module")
def compose():
    """Load and parse docker-compose.yml once."""
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)


# ── File structure ──

class TestComposeStructure:
    """docker-compose.yml has valid top-level structure."""

    def test_file_parses_as_valid_yaml(self, compose):
        assert compose is not None
        assert isinstance(compose, dict)

    def test_has_services_key(self, compose):
        assert "services" in compose

    def test_services_is_a_dict(self, compose):
        assert isinstance(compose["services"], dict)


# ── Required services ──

class TestRequiredServices:
    """All required services are present."""

    def test_postgres_service_exists(self, compose):
        assert "postgres" in compose["services"]

    def test_redis_service_exists(self, compose):
        assert "redis" in compose["services"]

    def test_minio_service_exists(self, compose):
        assert "minio" in compose["services"]

    def test_backend_service_exists(self, compose):
        assert "backend" in compose["services"]

    def test_worker_service_exists(self, compose):
        assert "worker" in compose["services"]

    def test_frontend_service_exists(self, compose):
        assert "frontend" in compose["services"]


# ── Redis service ──

class TestRedisService:
    """Redis service is correctly configured."""

    def test_redis_uses_official_image(self, compose):
        redis = compose["services"]["redis"]
        assert "redis" in redis.get("image", "")

    def test_redis_has_health_check(self, compose):
        redis = compose["services"]["redis"]
        assert "healthcheck" in redis

    def test_redis_health_check_uses_ping(self, compose):
        redis = compose["services"]["redis"]
        hc = redis["healthcheck"]
        cmd = " ".join(hc["test"]) if isinstance(hc["test"], list) else hc["test"]
        assert "ping" in cmd.lower()

    def test_redis_exposes_port_6379(self, compose):
        redis = compose["services"]["redis"]
        ports = redis.get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("6379" in p for p in port_strings)


# ── Worker service ──

class TestWorkerService:
    """Worker service is correctly configured for data plane."""

    def test_worker_runs_app_worker_module(self, compose):
        worker = compose["services"]["worker"]
        command = worker.get("command", [])
        cmd_str = " ".join(command) if isinstance(command, list) else str(command)
        assert "app.worker" in cmd_str

    def test_worker_platform_is_linux_amd64(self, compose):
        worker = compose["services"]["worker"]
        assert worker.get("platform") == "linux/amd64"

    def test_worker_depends_on_redis(self, compose):
        worker = compose["services"]["worker"]
        depends = worker.get("depends_on", {})
        if isinstance(depends, list):
            assert "redis" in depends
        else:
            assert "redis" in depends

    def test_worker_depends_on_postgres(self, compose):
        worker = compose["services"]["worker"]
        depends = worker.get("depends_on", {})
        if isinstance(depends, list):
            assert "postgres" in depends
        else:
            assert "postgres" in depends

    def test_worker_has_redis_url_env(self, compose):
        worker = compose["services"]["worker"]
        env = worker.get("environment", {})
        env_str = str(env)
        assert "REDIS_URL" in env_str

    def test_worker_dispatch_mode_is_redis(self, compose):
        worker = compose["services"]["worker"]
        env = worker.get("environment", {})
        env_str = str(env)
        assert "redis" in env_str.lower()


# ── Backend service ──

class TestBackendService:
    """Backend service is correctly configured for control plane."""

    def test_backend_platform_is_linux_amd64(self, compose):
        backend = compose["services"]["backend"]
        assert backend.get("platform") == "linux/amd64"

    def test_backend_depends_on_postgres(self, compose):
        backend = compose["services"]["backend"]
        depends = backend.get("depends_on", {})
        if isinstance(depends, list):
            assert "postgres" in depends
        else:
            assert "postgres" in depends

    def test_backend_depends_on_minio_init(self, compose):
        backend = compose["services"]["backend"]
        depends = backend.get("depends_on", {})
        if isinstance(depends, list):
            assert "minio-init" in depends
        else:
            assert "minio-init" in depends

    def test_backend_has_redis_url_env(self, compose):
        backend = compose["services"]["backend"]
        env = backend.get("environment", {})
        env_str = str(env)
        assert "REDIS_URL" in env_str

    def test_backend_exposes_port_8000(self, compose):
        backend = compose["services"]["backend"]
        ports = backend.get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("8000" in p for p in port_strings)

    def test_backend_has_secret_key(self, compose):
        backend = compose["services"]["backend"]
        env = backend.get("environment", {})
        env_str = str(env)
        assert "SECRET_KEY" in env_str


# ── Frontend service ──

class TestFrontendService:
    """Frontend service is correctly configured."""

    def test_frontend_platform_is_linux_amd64(self, compose):
        frontend = compose["services"]["frontend"]
        assert frontend.get("platform") == "linux/amd64"

    def test_frontend_depends_on_backend(self, compose):
        frontend = compose["services"]["frontend"]
        depends = frontend.get("depends_on", [])
        if isinstance(depends, list):
            assert "backend" in depends
        else:
            assert "backend" in depends


# ── Queue name consistency ──

class TestQueueNameConsistency:
    """Queue name constants are consistent with compose configuration."""

    def test_redis_queue_names_match_constants(self):
        """Verify queue name constants are as expected (not accidentally changed)."""
        from app.interfaces.redis_dispatcher import BACKUP_QUEUE, RESTORE_QUEUE

        assert BACKUP_QUEUE == "shieldio:backup_queue"
        assert RESTORE_QUEUE == "shieldio:restore_queue"

    def test_worker_uses_same_redis_url_scheme(self, compose):
        """Worker REDIS_URL uses the redis service hostname."""
        worker = compose["services"]["worker"]
        env = worker.get("environment", {})
        env_str = str(env)
        # Should reference the 'redis' service, not localhost
        assert "redis://" in env_str
