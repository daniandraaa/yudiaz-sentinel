"""Unit and Integration Tests for Yudiaz Sentinel Alerting Gateway & Security Sentinel.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001
Auditor: Viktor Moreau (Lead QA Engineer)
"""

from __future__ import annotations

import asyncio
import datetime
import os
from pathlib import Path
import tempfile
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import httpx
import pytest

from backend.main import app
from backend import notifier
from backend.notifier import AlertDeduplicator
from backend.security_sentinel import SecuritySentinel, security_sentinel


# ==============================================================================
# Fixtures
# ==============================================================================
@pytest.fixture(scope="module")
def client():
    """Create test client with FastAPI application lifespan."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_deduplicator():
    """Reset deduplicator state before each test."""
    notifier.deduplicator.clear()
    yield
    notifier.deduplicator.clear()


@pytest.fixture
def temp_fail2ban_log(tmp_path: Path) -> Path:
    """Create a temporary fail2ban.log with realistic ban events."""
    log_file = tmp_path / "fail2ban.log"
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    content = f"""2026-09-25 10:00:00,123 fail2ban.server [1000]: INFO Starting Fail2ban v1.0.2
{yesterday} 11:00:00,456 fail2ban.actions [1000]: NOTICE [sshd] Ban 192.0.2.1
{today_str} 08:15:20,111 fail2ban.actions [1000]: NOTICE [sshd] Ban 198.51.100.10
{today_str} 08:25:20,222 fail2ban.actions [1000]: NOTICE [sshd] Unban 198.51.100.10
{today_str} 09:30:45,333 fail2ban.actions [1000]: NOTICE [sshd] Ban 198.51.100.10
{today_str} 10:12:00,444 fail2ban.actions [1000]: NOTICE [sshd] Ban 203.0.113.5
{today_str} 11:05:12,555 fail2ban.actions [1000]: NOTICE [sshd] Ban 198.51.100.10
"""
    log_file.write_text(content, encoding="utf-8")
    return log_file


# ==============================================================================
# 1. Notifier & Deduplication Unit Tests
# ==============================================================================
def test_alert_deduplicator_cooldown() -> None:
    """Verify AlertDeduplicator enforces cooldown and tracks remaining time."""
    dedup = AlertDeduplicator(default_cooldown_seconds=10.0)
    key = "sec:sshd:192.0.2.1:ban"

    # Initially not rate limited
    assert not dedup.is_rate_limited(key)
    assert dedup.get_cooldown_remaining(key) == 0.0

    # Record dispatch
    dedup.record_alert(key)
    assert dedup.is_rate_limited(key)
    assert dedup.get_cooldown_remaining(key) > 5.0

    # Different key is independent
    other_key = "sec:sshd:192.0.2.2:ban"
    assert not dedup.is_rate_limited(other_key)

    # Custom cooldown override
    assert not dedup.is_rate_limited(key, cooldown=0.0)

    # Purge
    dedup.clear()
    assert not dedup.is_rate_limited(key)


@pytest.mark.asyncio
async def test_send_telegram_message_success() -> None:
    """Verify send_telegram_message returns True on HTTP 200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "12345"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            success = await notifier.send_telegram_message("Hello from Yudiaz Sentinel")

            assert success is True
            assert mock_post.called
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["chat_id"] == "12345"
            assert call_kwargs["json"]["text"] == "Hello from Yudiaz Sentinel"


@pytest.mark.asyncio
async def test_send_telegram_message_api_failure() -> None:
    """Verify send_telegram_message returns False when Telegram returns error status."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request: chat not found"

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "12345"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            success = await notifier.send_telegram_message("Invalid chat test")

            assert success is False


@pytest.mark.asyncio
async def test_send_telegram_message_missing_token() -> None:
    """Verify send_telegram_message returns False safely without credentials."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
        success = await notifier.send_telegram_message("No token")
        assert success is False


@pytest.mark.asyncio
async def test_send_telegram_message_network_exception() -> None:
    """Verify send_telegram_message catches network errors gracefully."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "12345"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectTimeout("Connection timed out")
            success = await notifier.send_telegram_message("Timeout test")
            assert success is False


@pytest.mark.asyncio
async def test_send_security_alert_deduplication() -> None:
    """Verify send_security_alert blocks duplicate alerts within cooldown window."""
    with patch("backend.notifier.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # First alert: dispatches successfully
        res1 = await notifier.send_security_alert("192.0.2.1", "sshd", "Ban", "Strike #1", cooldown=60.0)
        assert res1 is True
        assert mock_send.call_count == 1

        # Second alert: throttled by deduplicator
        res2 = await notifier.send_security_alert("192.0.2.1", "sshd", "Ban", "Strike #2", cooldown=60.0)
        assert res2 is False
        assert mock_send.call_count == 1

        # Forced alert: bypasses deduplicator
        res3 = await notifier.send_security_alert("192.0.2.1", "sshd", "Ban", "Strike #3", force=True)
        assert res3 is True
        assert mock_send.call_count == 2


@pytest.mark.asyncio
async def test_send_resource_alert_deduplication() -> None:
    """Verify send_resource_alert handles formatting and rate limiting."""
    with patch("backend.notifier.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        res1 = await notifier.send_resource_alert("CPU", 92.5, 85.0, cooldown=60.0)
        assert res1 is True
        assert mock_send.call_count == 1

        # Duplicate alert throttled
        res2 = await notifier.send_resource_alert("CPU", 94.1, 85.0, cooldown=60.0)
        assert res2 is False
        assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_send_service_alert_dispatch() -> None:
    """Verify send_service_alert formats and delivers service degradation notice."""
    with patch("backend.notifier.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        res = await notifier.send_service_alert("hermes-agent", "degraded", "TCP probe 9119 failed", force=True)
        assert res is True
        assert mock_send.call_count == 1
        sent_text = mock_send.call_args[0][0]
        assert "hermes-agent" in sent_text
        assert "DEGRADED" in sent_text


@pytest.mark.asyncio
async def test_send_daily_digest_dispatch() -> None:
    """Verify send_daily_digest formats full telemetry and delivers successfully."""
    with patch("backend.notifier.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        stats = {
            "date": "2026-09-26 13:00:00 UTC",
            "cpu_load": "12.4% (1m load: 0.15)",
            "ram_usage": "18.2 GB / 54.0 GB (33.7%)",
            "disk_usage": "24.5% used (180.2 GB free)",
            "uptime": "14 days, 2 hours",
            "bans_today": 37,
            "active_jails": "sshd",
            "firewall_status": "Active (UFW)",
            "services_online": "5/5 services operational",
        }
        res = await notifier.send_daily_digest(stats)
        assert res is True
        assert mock_send.call_count == 1
        sent_text = mock_send.call_args[0][0]
        assert "DAILY TELEMETRY & SECURITY DIGEST" in sent_text
        assert "37" in sent_text


# ==============================================================================
# 2. SecuritySentinel Log Parser & Defense Audit Tests
# ==============================================================================
def test_parse_log_file_with_temp_log(temp_fail2ban_log: Path) -> None:
    """Verify SecuritySentinel correctly parses fail2ban log and computes recidivism."""
    sentinel = SecuritySentinel(log_path=str(temp_fail2ban_log))
    metrics = sentinel.parse_log_file()

    # Total bans today should be 4 (three for 198.51.100.10, one for 203.0.113.5)
    assert metrics["total_bans_today"] == 4
    assert metrics["unique_ips_banned_today"] == 2
    assert metrics["active_jails"] == ["sshd"]
    assert len(metrics["recent_events"]) == 5

    # Check recidivism calculation for 198.51.100.10
    # In recent_events (newest first):
    newest_event = metrics["recent_events"][0]
    assert newest_event["ip"] == "198.51.100.10"
    assert newest_event["recidive_count"] == 3
    assert "Strike #3" in newest_event["recidive_info"]


def test_parse_log_file_missing_file(tmp_path: Path) -> None:
    """Verify SecuritySentinel handles missing log file without crashing."""
    missing = tmp_path / "non_existent.log"
    sentinel = SecuritySentinel(log_path=str(missing))
    metrics = sentinel.parse_log_file()

    assert metrics["total_bans_today"] == 0
    assert metrics["recent_events"] == []
    assert metrics["status"] == "log_not_found"


def test_four_layer_defense_structure() -> None:
    """Verify 4-layer defense audit returns all required architectural layers."""
    sentinel = SecuritySentinel()
    defense = sentinel.get_four_layer_defense_status()

    assert "layer_1_firewall" in defense
    assert "layer_2_intrusion_prevention" in defense
    assert "layer_3_kernel_hardening" in defense
    assert "layer_4_ssh_hardening" in defense

    assert defense["layer_1_firewall"]["status"] in ("active", "standby")
    assert defense["layer_2_intrusion_prevention"]["status"] in ("active", "inactive")
    assert defense["layer_3_kernel_hardening"]["status"] in ("active", "nominal")
    assert defense["layer_4_ssh_hardening"]["status"] in ("active", "inactive")


def test_get_security_status_envelope() -> None:
    """Verify get_security_status returns complete structured telemetry payload."""
    sentinel = SecuritySentinel()
    status = sentinel.get_security_status()

    assert "total_bans_today" in status
    assert "recent_events" in status
    assert "firewall_status" in status
    assert "four_layer_defense" in status
    assert "active_jails" in status
    assert "summary" in status
    assert isinstance(status["summary"]["total_bans_today"], int)


# ==============================================================================
# 3. SecuritySentinel Background Worker & Watcher Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_watcher_detects_new_ban(tmp_path: Path) -> None:
    """Verify SecuritySentinel log watcher detects newly appended ban and dispatches alert."""
    log_file = tmp_path / "fail2ban.log"
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    initial_content = f"{today_str} 10:00:00,100 fail2ban.actions [1000]: NOTICE [sshd] Ban 192.0.2.1\n"
    log_file.write_text(initial_content, encoding="utf-8")

    sentinel = SecuritySentinel(log_path=str(log_file), poll_interval=0.1)

    with patch("backend.notifier.send_security_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True

        # Prime position at EOF
        await sentinel._init_file_position()

        # Append new ban
        new_ban = f"{today_str} 10:05:00,200 fail2ban.actions [1000]: NOTICE [sshd] Ban 203.0.113.88\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(new_ban)

        # Trigger watcher check
        await sentinel._check_new_bans()

        assert mock_alert.called
        call_kwargs = mock_alert.call_args.kwargs
        assert call_kwargs["ip"] == "203.0.113.88"
        assert call_kwargs["jail"] == "sshd"
        assert call_kwargs["action"] == "Ban"


@pytest.mark.asyncio
async def test_watcher_handles_rotation(tmp_path: Path) -> None:
    """Verify SecuritySentinel resets offset when log file is truncated/rotated."""
    log_file = tmp_path / "fail2ban.log"
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    log_file.write_text(f"{today_str} 10:00:00,100 fail2ban.actions [1000]: NOTICE [sshd] Ban 192.0.2.1\n" * 10)
    sentinel = SecuritySentinel(log_path=str(log_file))
    await sentinel._init_file_position()

    # Simulate rotation (smaller file size)
    log_file.write_text(f"{today_str} 12:00:00,200 fail2ban.actions [1000]: NOTICE [sshd] Ban 198.51.100.99\n")

    with patch("backend.notifier.send_security_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True
        await sentinel._check_new_bans()

        # Should detect truncation, reset offset, and parse the new ban
        assert mock_alert.called
        assert mock_alert.call_args.kwargs["ip"] == "198.51.100.99"


@pytest.mark.asyncio
async def test_resource_watchdog_threshold_breach() -> None:
    """Verify _check_resource_utilization fires resource alerts when thresholds exceeded."""
    sentinel = SecuritySentinel(alert_threshold_cpu=50.0, alert_threshold_ram=50.0, alert_threshold_disk=50.0)

    with patch("psutil.cpu_percent", return_value=88.5):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.percent = 40.0  # Under threshold
            with patch("psutil.disk_usage") as mock_disk:
                mock_disk.return_value.percent = 30.0  # Under threshold
                with patch("backend.notifier.send_resource_alert", new_callable=AsyncMock) as mock_alert:
                    mock_alert.return_value = True
                    await sentinel._check_resource_utilization()

                    assert mock_alert.called
                    assert mock_alert.call_args[0][0] == "CPU"
                    assert mock_alert.call_args[0][1] == 88.5


@pytest.mark.asyncio
async def test_trigger_daily_digest() -> None:
    """Verify trigger_daily_digest compiles metrics and calls send_daily_digest."""
    sentinel = SecuritySentinel()

    with patch("backend.notifier.send_daily_digest", new_callable=AsyncMock) as mock_digest:
        mock_digest.return_value = True
        success = await sentinel.trigger_daily_digest()

        assert success is True
        assert mock_digest.called
        stats_arg = mock_digest.call_args[0][0]
        assert "cpu_load" in stats_arg
        assert "ram_usage" in stats_arg
        assert "bans_today" in stats_arg


@pytest.mark.asyncio
async def test_sentinel_start_and_stop_lifecycle() -> None:
    """Verify start() and stop() manage background worker task cleanly."""
    sentinel = SecuritySentinel(poll_interval=0.05)
    await sentinel.start()
    assert sentinel._running is True
    assert sentinel._worker_task is not None
    assert not sentinel._worker_task.done()

    # Redundant start is no-op
    await sentinel.start()
    assert sentinel._running is True

    await sentinel.stop()
    assert sentinel._running is False
    assert sentinel._worker_task is None


# ==============================================================================
# 4. API Endpoints Integration Tests
# ==============================================================================
def test_get_security_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/security returns HTTP 200 with standard envelope."""
    response = client.get("/api/v1/security")
    assert response.status_code == 200

    payload: Dict[str, Any] = response.json()
    assert payload["success"] is True
    assert "timestamp" in payload

    data = payload["data"]
    assert "total_bans_today" in data
    assert "recent_events" in data
    assert isinstance(data["recent_events"], list)
    assert "firewall_status" in data
    assert "four_layer_defense" in data
    assert "active_jails" in data
    assert "summary" in data


def test_post_security_alert_test_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/security/alert/test accepts payload and dispatches test alert."""
    with patch("backend.notifier.send_security_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True

        response = client.post(
            "/api/v1/security/alert/test",
            json={
                "type": "security",
                "ip": "203.0.113.99",
                "jail": "sshd",
                "action": "Ban",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["delivered"] is True
        assert payload["data"]["status"] == "delivered"


def test_post_security_alert_test_resource_type(client: TestClient) -> None:
    """Verify POST /api/v1/security/alert/test dispatches resource alert when requested."""
    with patch("backend.notifier.send_resource_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True

        response = client.post(
            "/api/v1/security/alert/test",
            json={
                "type": "resource",
                "resource": "RAM",
                "current_val": 91.2,
                "threshold": 85.0,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["alert_type"] == "resource"
        assert payload["data"]["delivered"] is True


def test_post_security_digest_trigger_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/security/digest/trigger manually triggers ops digest."""
    with patch("backend.security_sentinel.security_sentinel.trigger_daily_digest", new_callable=AsyncMock) as mock_trig:
        mock_trig.return_value = True

        response = client.post("/api/v1/security/digest/trigger")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["delivered"] is True
        assert payload["data"]["status"] == "delivered"


def test_post_security_alert_test_service_type(client: TestClient) -> None:
    """Verify POST /api/v1/security/alert/test dispatches service alert."""
    with patch("backend.notifier.send_service_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = True

        response = client.post(
            "/api/v1/security/alert/test",
            json={
                "type": "service",
                "service": "caddy",
                "status": "degraded",
                "details": "High HTTP 502 error rate",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["alert_type"] == "service"
        assert payload["data"]["delivered"] is True


def test_post_security_alert_test_custom_type(client: TestClient) -> None:
    """Verify POST /api/v1/security/alert/test dispatches custom message."""
    with patch("backend.notifier.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        response = client.post(
            "/api/v1/security/alert/test",
            json={
                "type": "custom",
                "message": "Deployment v1.1.0 completed successfully",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["alert_type"] == "custom"
        assert payload["data"]["delivered"] is True


def test_get_security_endpoint_error_handling(client: TestClient) -> None:
    """Verify GET /api/v1/security returns HTTP 500 error envelope when exception occurs."""
    with patch("backend.security_sentinel.security_sentinel.get_security_status", side_effect=RuntimeError("Kernel fault")):
        response = client.get("/api/v1/security")
        assert response.status_code == 500
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "SECURITY_TELEMETRY_ERROR"


def test_post_security_digest_trigger_error_handling(client: TestClient) -> None:
    """Verify POST /api/v1/security/digest/trigger returns 500 on unexpected exception."""
    with patch("backend.security_sentinel.security_sentinel.trigger_daily_digest", side_effect=Exception("Scheduler crashed")):
        response = client.post("/api/v1/security/digest/trigger")
        assert response.status_code == 500
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "DIGEST_TRIGGER_ERROR"

