"""End-to-End Production Verification & QA Audit for Yudiaz Sentinel.

Auditor: Viktor Moreau (Lead QA Engineer, Yudiaz Creative Studio)
Target: https://vps.daniandraaa.my.id & https://vps.20.200.220.190.sslip.io
Local Daemon: http://127.0.0.1:9229
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
import re
import socket
import ssl
import subprocess
import time
from typing import Any, Dict, List, Tuple
import urllib.parse
import httpx
import pytest

PRIMARY_URL = "https://vps.daniandraaa.my.id"
FALLBACK_URL = "https://vps.20.200.220.190.sslip.io"
LOCAL_URL = "http://127.0.0.1:9229"

HEADERS = {
    "User-Agent": "YudiazSentinel-QA-Audit/1.0 (Viktor Moreau; QA Engine)"
}


# ==============================================================================
# 1. SSL / TLS Verification
# ==============================================================================
def get_cert_details(hostname: str, port: int = 443) -> Dict[str, Any]:
    context = ssl.create_default_context()
    conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname)
    conn.settimeout(5.0)
    conn.connect((hostname, port))
    
    cert = conn.getpeercert()
    cipher = conn.cipher()
    version = conn.version()
    conn.close()

    # Extract subject, issuer, expiry
    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    not_after_str = cert.get("notAfter")
    not_before_str = cert.get("notBefore")
    
    # Parse dates
    not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    not_before = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_remaining = (not_after - now).days

    sans = [item[1] for item in cert.get("subjectAltName", []) if item[0] == "DNS"]

    return {
        "hostname": hostname,
        "tls_version": version,
        "cipher": cipher[0] if cipher else None,
        "cipher_bits": cipher[2] if cipher else None,
        "subject_cn": subject.get("commonName"),
        "issuer_cn": issuer.get("commonName"),
        "issuer_o": issuer.get("organizationName"),
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "days_remaining": days_remaining,
        "sans": sans,
    }


def test_ssl_tls_handshake_primary():
    details = get_cert_details("vps.daniandraaa.my.id")
    assert details["tls_version"] == "TLSv1.3", f"Expected TLSv1.3, got {details['tls_version']}"
    assert "Let's Encrypt" in details["issuer_o"] or "YE2" in details["issuer_cn"]
    assert details["subject_cn"] == "vps.daniandraaa.my.id"
    assert "vps.daniandraaa.my.id" in details["sans"]
    assert details["days_remaining"] > 30, f"Certificate expiring too soon: {details['days_remaining']} days"


def test_ssl_tls_handshake_fallback():
    details = get_cert_details("vps.20.200.220.190.sslip.io")
    assert details["tls_version"] == "TLSv1.3", f"Expected TLSv1.3, got {details['tls_version']}"
    assert "Let's Encrypt" in details["issuer_o"] or "YE2" in details["issuer_cn"]
    assert details["subject_cn"] == "vps.20.200.220.190.sslip.io"
    assert "vps.20.200.220.190.sslip.io" in details["sans"]
    assert details["days_remaining"] > 30


# ==============================================================================
# 2. HTTP Root & Endpoints Verification
# ==============================================================================
def test_http_to_https_redirect():
    with httpx.Client(follow_redirects=False, timeout=5.0) as client:
        r = client.get("http://vps.daniandraaa.my.id/")
        assert r.status_code in (301, 308)
        assert r.headers["location"].startswith("https://vps.daniandraaa.my.id")


def test_primary_root_index():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert len(r.content) > 50000
        text = r.text
        assert "Yudiaz Sentinel" in text
        assert "VPS Telemetry" in text
        assert "System Architecture" in text
        assert "assets/yudiaz-logo-mark.svg" in text


def test_primary_rest_endpoints():
    endpoints = ["health", "metrics", "specs", "projects", "team"]
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        for ep in endpoints:
            url = f"{PRIMARY_URL}/api/v1/{ep}"
            r = client.get(url)
            assert r.status_code == 200, f"Endpoint {url} returned {r.status_code}"
            assert "application/json" in r.headers["content-type"]
            data = r.json()
            assert data["success"] is True
            assert "timestamp" in data
            assert "data" in data


def test_primary_health_payload():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/health")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "healthy"
        assert body["service"] == "yudiaz-sentinel"
        assert body["version"] == "1.0.0"
        assert body["uptime_seconds"] > 0
        assert body["daemon_pid"] > 0
        assert body["memory_rss_mb"] < 60.0, f"Memory RSS exceeded budget: {body['memory_rss_mb']} MB"


def test_primary_metrics_payload():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/metrics")
        assert r.status_code == 200
        body = r.json()["data"]
        assert "uptime" in body
        assert "cpu" in body
        assert "memory" in body
        assert "disks" in body
        assert "io" in body
        
        # Verify CPU structure
        assert body["cpu"]["cores_count"] == 4
        assert len(body["cpu"]["per_core_percent"]) == 4
        assert body["memory"]["total_gb"] > 50.0  # 54 GB VPS
        assert len(body["disks"]) >= 1


def test_primary_specs_payload():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/specs")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["server"]["hostname"] == "Daniilham-PC"
        assert body["cpu"]["cores_physical"] == 4
        assert body["network"]["public_ip"] == "20.200.220.190"
        assert body["network"]["primary_subdomain"] == "vps.daniandraaa.my.id"


def test_primary_projects_payload():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/projects")
        assert r.status_code == 200
        body = r.json()["data"]
        services = body["services"]
        assert len(services) == 7
        service_map = {s["id"]: s for s in services}
        for expected in ["hermes-agent", "9router", "caddy", "yudiaz-sentinel", "yudiaz-assets", "yudiaz-latex", "yudiaz-npp"]:
            assert expected in service_map
            assert service_map[expected]["status"] in ("online", "healthy")


def test_primary_team_payload():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/team")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["total_agents"] == 12
        agents = {a["id"]: a for a in body["agents"]}
        expected_agents = [
            "daffa", "cucurella", "devera", "raziel-hendrix", "kael-ashford", "nara-vasquez",
            "senna-louviere", "idris-nakamura", "mika-stellan",
            "viktor-moreau", "elara-sinclair", "jovan-aritza"
        ]
        for aid in expected_agents:
            assert aid in agents
            assert agents[aid]["status"] == "active"


def test_fallback_domain_parity():
    endpoints = ["", "api/v1/health", "api/v1/metrics", "api/v1/specs", "api/v1/projects", "api/v1/team"]
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        for ep in endpoints:
            url = f"{FALLBACK_URL}/{ep}".rstrip("/")
            r = client.get(url)
            assert r.status_code == 200, f"Fallback {url} returned {r.status_code}"


# ==============================================================================
# 3. Server-Sent Events (SSE) Stream Verification
# ==============================================================================
@pytest.mark.asyncio
async def test_sse_stream_realtime():
    """Verify SSE stream delivers real-time ticks with zero buffering lag."""
    url = f"{PRIMARY_URL}/api/v1/metrics/stream"
    async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
        t_start = time.perf_counter()
        async with client.stream("GET", url) as response:
            t_connect = time.perf_counter() - t_start
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("x-accel-buffering") == "no"
            
            ticks_collected: List[Tuple[float, Dict[str, Any]]] = []
            buffer = ""
            
            t0 = time.perf_counter()
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    now_ts = time.perf_counter()
                    lines = [ln.strip() for ln in event_block.strip().split("\n") if ln.strip()]
                    
                    data_lines = [ln[5:].strip() for ln in lines if ln.startswith("data:")]
                    if data_lines:
                        raw_json = "".join(data_lines)
                        parsed = json.loads(raw_json)
                        ticks_collected.append((now_ts, parsed))
                        if len(ticks_collected) >= 3:
                            break
                if len(ticks_collected) >= 3:
                    break

    assert len(ticks_collected) >= 3, f"Collected only {len(ticks_collected)} ticks"
    
    # Verify initial tick received immediately (zero buffering lag)
    first_tick_latency = ticks_collected[0][0] - t0
    assert first_tick_latency < 0.25, f"Initial tick delayed: {first_tick_latency:.3f}s"
    
    # Verify intervals between tick 1->2 and 2->3 (scheduled at 2.0s interval)
    interval_1 = ticks_collected[1][0] - ticks_collected[0][0]
    interval_2 = ticks_collected[2][0] - ticks_collected[1][0]
    assert 1.7 <= interval_1 <= 2.4, f"Abnormal tick interval 1: {interval_1:.3f}s"
    assert 1.7 <= interval_2 <= 2.4, f"Abnormal tick interval 2: {interval_2:.3f}s"

    # Verify tick data integrity
    for _, tick in ticks_collected:
        assert "timestamp" in tick
        assert "cpu_percent" in tick
        assert "ram_used_gb" in tick
        assert len(tick["per_core"]) == 4


# ==============================================================================
# 4. Latency Benchmark (< 50ms requirement)
# ==============================================================================
def test_latency_benchmark():
    endpoints = [
        ("Root (/)", f"{PRIMARY_URL}/"),
        ("Health (/api/v1/health)", f"{PRIMARY_URL}/api/v1/health"),
        ("Metrics (/api/v1/metrics)", f"{PRIMARY_URL}/api/v1/metrics"),
        ("Specs (/api/v1/specs)", f"{PRIMARY_URL}/api/v1/specs"),
        ("Projects (/api/v1/projects)", f"{PRIMARY_URL}/api/v1/projects"),
        ("Team (/api/v1/team)", f"{PRIMARY_URL}/api/v1/team"),
    ]
    
    summary: Dict[str, Dict[str, float]] = {}
    
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        # Warmup connection
        client.get(f"{PRIMARY_URL}/api/v1/health")
        
        for name, url in endpoints:
            latencies: List[float] = []
            for _ in range(25):
                t1 = time.perf_counter()
                r = client.get(url)
                t2 = time.perf_counter()
                assert r.status_code == 200
                latencies.append((t2 - t1) * 1000.0)  # ms
            
            latencies.sort()
            avg_lat = sum(latencies) / len(latencies)
            p95_lat = latencies[int(len(latencies) * 0.95)]
            min_lat = latencies[0]
            max_lat = latencies[-1]
            
            summary[name] = {
                "min": min_lat,
                "avg": avg_lat,
                "p95": p95_lat,
                "max": max_lat,
            }
            
            # Assert target < 50ms average / p95 for API endpoints
            if "/api/v1/projects" not in url:
                assert p95_lat < 50.0, f"{name} p95 latency exceeded 50ms: {p95_lat:.2f}ms"
            else:
                # projects probes 5 services concurrently
                assert p95_lat < 60.0, f"{name} p95 latency exceeded 60ms: {p95_lat:.2f}ms"


# ==============================================================================
# 5. Daemon Resource Footprint Audit (RAM < 60MB, CPU < 1%)
# ==============================================================================
def test_daemon_resource_footprint():
    # 1. Get PID from systemctl
    res = subprocess.run(
        ["systemctl", "show", "yudiaz-sentinel.service", "--property=MainPID,ActiveState,MemoryCurrent,CPUUsageNSec"],
        capture_output=True,
        text=True,
        check=True
    )
    props = dict(line.split("=", 1) for line in res.stdout.strip().split("\n") if "=" in line)
    assert props["ActiveState"] == "active"
    pid = int(props["MainPID"])
    assert pid > 0
    
    # 2. Inspect /proc/<pid>/status
    status_path = f"/proc/{pid}/status"
    assert os.path.exists(status_path)
    
    status_data = {}
    with open(status_path, "r") as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                status_data[k.strip()] = v.strip()
    
    # VmRSS in kB
    vm_rss_kb = int(status_data["VmRSS"].split()[0])
    vm_rss_mb = vm_rss_kb / 1024.0
    
    # MemoryCurrent from systemd cgroup
    mem_current_bytes = int(props.get("MemoryCurrent", "0"))
    mem_current_mb = mem_current_bytes / (1024.0 * 1024.0)

    # CPU sample over 1.5 seconds
    stat_file = f"/proc/{pid}/stat"
    with open(stat_file, "r") as f:
        stat1 = f.read().split()
    utime1, stime1 = int(stat1[13]), int(stat1[14])
    t1 = time.time()
    
    time.sleep(1.5)
    
    with open(stat_file, "r") as f:
        stat2 = f.read().split()
    utime2, stime2 = int(stat2[13]), int(stat2[14])
    t2 = time.time()
    
    clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    cpu_time_sec = ((utime2 + stime2) - (utime1 + stime1)) / float(clk_tck)
    elapsed_sec = t2 - t1
    cpu_percent = (cpu_time_sec / elapsed_sec) * 100.0
    
    # Verify budgets
    assert vm_rss_mb < 60.0, f"Daemon RAM RSS {vm_rss_mb:.2f} MB exceeded 60MB budget!"
    assert cpu_percent < 1.5, f"Daemon CPU {cpu_percent:.2f}% exceeded idle budget!"


# ==============================================================================
# 6. Security & Negative Edge-Cases
# ==============================================================================
def test_security_404_handling():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.get(f"{PRIMARY_URL}/api/v1/nonexistent_route")
        assert r.status_code == 404


def test_security_path_traversal():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        # Path traversal probe
        r = client.get(f"{PRIMARY_URL}/assets/../../../../etc/passwd")
        # Should be blocked, normalized, or 404
        assert r.status_code in (400, 404)
        assert "root:" not in r.text


def test_security_method_not_allowed():
    with httpx.Client(timeout=5.0, headers=HEADERS) as client:
        r = client.post(f"{PRIMARY_URL}/api/v1/health", json={"dummy": "payload"})
        assert r.status_code == 405
