"""Unit tests for Yudiaz Sentinel API.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001
Auditor: Viktor Moreau (Lead QA)
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.routes import stream_metrics


@pytest.fixture(scope="module")
def client():
    """Create test client with app lifecycle."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/health returns HTTP 200 and valid health envelope."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]
    assert data["status"] == "healthy"
    assert data["service"] == "yudiaz-sentinel"
    assert data["version"] == "1.0.0"
    assert isinstance(data["uptime_seconds"], (int, float))
    assert isinstance(data["daemon_pid"], int)
    assert isinstance(data["memory_rss_mb"], (int, float))


def test_metrics_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/metrics returns HTTP 200 and full system telemetry."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]

    # 1. Uptime
    uptime = data["uptime"]
    assert "system_uptime_seconds" in uptime
    assert "system_uptime_human" in uptime
    assert "boot_time" in uptime

    # 2. CPU
    cpu = data["cpu"]
    assert isinstance(cpu["overall_usage_percent"], (int, float))
    assert len(cpu["per_core_percent"]) == 4
    assert cpu["cores_count"] == 4
    assert "load_1m" in cpu["load_average"]

    # 3. Memory
    memory = data["memory"]
    assert memory["total_gb"] > 0
    assert memory["used_gb"] >= 0
    assert memory["free_gb"] >= 0
    assert "swap" in memory

    # 4. Disks
    disks = data["disks"]
    assert len(disks) >= 1
    root_disk = disks[0]
    assert root_disk["mountpoint"] == "/"
    assert root_disk["total_gb"] > 0

    # 5. IO
    assert "io" in data
    assert "disk" in data["io"]
    assert "network" in data["io"]


def test_specs_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/specs returns HTTP 200 and hardware baseline."""
    response = client.get("/api/v1/specs")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]
    assert "server" in data
    assert "Daniilham-PC" in data["server"]["hostname"]
    assert data["cpu"]["cores_physical"] == 4
    assert data["cpu"]["cores_logical"] == 4
    assert "Xeon" in data["cpu"]["model"]
    assert data["memory"]["total_physical_ram_gb"] == 54.0
    assert data["network"]["public_ip"] == "20.200.220.190"
    assert data["network"]["primary_subdomain"] == "vps.daniandraaa.my.id"


def test_projects_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/projects probes attached services and returns HTTP 200."""
    response = client.get("/api/v1/projects")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]
    services = data["services"]
    service_ids = [s["id"] for s in services]

    # Verify all 5 core monitored services exist
    assert "hermes-agent" in service_ids
    assert "9router" in service_ids
    assert "caddy" in service_ids
    assert "yudiaz-sentinel" in service_ids
    assert "yudiaz-assets" in service_ids
    assert "yudiaz-latex" in service_ids

    # Verify Docker daemon inspect
    assert "docker" in data
    assert data["docker"]["status"] in ("online", "offline")

    # Verify deployed_projects catalog
    assert "deployed_projects" in data
    deployed = data["deployed_projects"]
    assert isinstance(deployed, list)
    assert len(deployed) >= 3
    deployed_ids = [p["id"] for p in deployed]
    assert "vps-sentinel" in deployed_ids
    assert "yudiaz-finance" in deployed_ids

    deployed_map = {p["id"]: p for p in deployed}
    expected_ids = ["vps-sentinel", "9router-api", "hermes-core"]
    for pid in expected_ids:
        assert pid in deployed_map
        proj = deployed_map[pid]
        # Validate all required fields
        for field in [
            "id",
            "name",
            "domain",
            "url",
            "category",
            "description",
            "status",
            "ssl",
            "badge",
            "internal_port",
        ]:
            assert field in proj, f"Missing field {field} in deployed project {pid}"

        assert proj["status"] in ("online", "offline")
        assert proj["ssl"] == "TLS 1.3 Active"
        assert proj["badge"] in ("LIVE PRODUCTION", "CORE PLATFORM")
        assert proj["url"].startswith("https://")
        assert isinstance(proj["internal_port"], int)

    # Validate specific deployed project attributes
    sentinel = deployed_map["vps-sentinel"]
    assert sentinel["name"] == "Yudiaz Sentinel"
    assert sentinel["domain"] == "vps.daniandraaa.my.id"
    assert sentinel["url"] == "https://vps.daniandraaa.my.id"
    assert sentinel["internal_port"] == 9229
    assert sentinel["badge"] == "LIVE PRODUCTION"

    router = deployed_map["9router-api"]
    assert router["name"] == "9Router AI Gateway"
    assert router["domain"] == "api.daniandraaa.my.id"
    assert router["url"] == "https://api.daniandraaa.my.id"
    assert router["internal_port"] == 20128
    assert router["badge"] == "LIVE PRODUCTION"

    hermes = deployed_map["hermes-core"]
    assert hermes["name"] == "Hermes Agent Core"
    assert hermes["domain"] == "hermes.20.200.220.190.sslip.io"
    assert hermes["url"] == "https://hermes.20.200.220.190.sslip.io"
    assert hermes["internal_port"] == 9119
    assert hermes["badge"] == "CORE PLATFORM"


@pytest.mark.asyncio
async def test_probe_deployed_projects() -> None:
    """Verify probe_deployed_projects returns complete status catalog."""
    from backend.probes import probe_deployed_projects

    projects = await probe_deployed_projects()
    assert len(projects) >= 3
    ids = [p["id"] for p in projects]
    assert "yudiaz-finance" in ids
    for p in projects:
        assert p["status"] in ("online", "offline")
        assert p["ssl"] == "TLS 1.3 Active"


def test_team_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/team returns HTTP 200 and all 9 AI agents."""
    response = client.get("/api/v1/team")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]
    assert data["organization"] == "Yudiaz Creative Studio"
    assert data["total_agents"] == 11

    agents = data["agents"]
    assert len(agents) == 9
    agent_ids = [a["id"] for a in agents]

    required_agents = [
        "raziel-hendrix",
        "kael-ashford",
        "nara-vasquez",
        "senna-louviere",
        "idris-nakamura",
        "mika-stellan",
        "viktor-moreau",
        "elara-sinclair",
        "jovan-aritza",
    ]
    for required in required_agents:
        assert required in agent_ids


@pytest.mark.asyncio
async def test_metrics_stream_endpoint() -> None:
    """Verify GET /api/v1/metrics/stream emits SSE metric_tick and 1st event is valid JSON."""
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    response = await stream_metrics(mock_request)
    assert response.status_code == 200
    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"

    # Consume single initial tick from stream generator and verify payload
    body_iterator = response.body_iterator
    first_chunk: str = await anext(body_iterator)

    assert "event: metric_tick" in first_chunk
    assert "data: " in first_chunk

    data_line = [line for line in first_chunk.strip().split("\n") if line.startswith("data: ")][0]
    json_str = data_line[len("data: ") :].strip()
    tick_payload = json.loads(json_str)

    assert "timestamp" in tick_payload
    assert "cpu_percent" in tick_payload
    assert "per_core" in tick_payload
    assert len(tick_payload["per_core"]) == 4
    assert "ram_used_gb" in tick_payload
    assert "disk_root_percent" in tick_payload


def test_static_root_endpoint(client: TestClient) -> None:
    """Verify GET / serves frontend index.html with HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
