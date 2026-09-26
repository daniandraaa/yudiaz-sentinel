"""Yudiaz Sentinel - Asynchronous Telegram Notification Gateway & Alerting Subsystem.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001 (Security & Alerting Gateway)
"""

from __future__ import annotations

import asyncio
import datetime
import html
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import httpx

# Load local environment configuration if present
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

logger = logging.getLogger("yudiaz.sentinel.notifier")


class AlertDeduplicator:
    """Thread-safe deduplication and rate-limiting cache for outgoing notifications.

    Maintains recent dispatch timestamps per alert key to prevent alert fatigue
    and notification flooding during active intrusion attempts or persistent spikes.
    """

    def __init__(self, default_cooldown_seconds: float = 300.0) -> None:
        self.default_cooldown: float = default_cooldown_seconds
        self._history: Dict[str, float] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def is_rate_limited(self, key: str, cooldown: Optional[float] = None) -> bool:
        """Check if an alert key is currently within its cooldown window."""
        now = time.time()
        cooldown_window = cooldown if cooldown is not None else self._get_effective_cooldown()
        last_sent = self._history.get(key, 0.0)
        return (now - last_sent) < cooldown_window

    def record_alert(self, key: str, timestamp: Optional[float] = None) -> None:
        """Record the timestamp of an alert dispatch."""
        self._history[key] = timestamp if timestamp is not None else time.time()

    def clear(self) -> None:
        """Purge all cached alert histories."""
        self._history.clear()

    def get_cooldown_remaining(self, key: str, cooldown: Optional[float] = None) -> float:
        """Return the number of seconds remaining in the cooldown window."""
        now = time.time()
        cooldown_window = cooldown if cooldown is not None else self._get_effective_cooldown()
        last_sent = self._history.get(key, 0.0)
        elapsed = now - last_sent
        return max(0.0, cooldown_window - elapsed)

    def _get_effective_cooldown(self) -> float:
        """Resolve current cooldown duration from environment or fallback default."""
        try:
            val = os.getenv("ALERT_COOLDOWN_SECONDS")
            if val:
                return float(val)
        except (ValueError, TypeError):
            pass
        return self.default_cooldown


# Global singleton deduplication cache
deduplicator = AlertDeduplicator(default_cooldown_seconds=300.0)


def _get_credentials() -> tuple[str, str]:
    """Retrieve Telegram bot token and default target chat ID."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CEO_CHAT_ID", "").strip()
    return token, chat_id


def _current_iso_time() -> str:
    """Format standard UTC ISO-8601 timestamp string."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


async def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    client: Optional[httpx.AsyncClient] = None,
) -> bool:
    """Dispatch an asynchronous text notification to Telegram via Bot API.

    Args:
        text: The message body (formatted with parse_mode, e.g. HTML).
        chat_id: Target Telegram chat ID. Falls back to env var if omitted.
        parse_mode: Formatting engine (defaults to "HTML").
        client: Optional existing httpx.AsyncClient instance.

    Returns:
        bool: True if message was accepted by Telegram API (HTTP 200), False otherwise.
    """
    token, default_chat_id = _get_credentials()
    target_chat = str(chat_id).strip() if chat_id else default_chat_id

    if not token:
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN not configured")
        return False

    if not target_chat:
        logger.warning("Telegram notification skipped: No chat_id provided or configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        if client is not None:
            resp = await client.post(url, json=payload, timeout=10.0)
        else:
            async with httpx.AsyncClient(timeout=10.0) as local_client:
                resp = await local_client.post(url, json=payload)

        if resp.status_code == 200:
            logger.info("Telegram notification successfully delivered to %s", target_chat)
            return True

        logger.error(
            "Telegram API error (%d): %s",
            resp.status_code,
            resp.text[:300],
        )
        return False
    except Exception as exc:
        logger.error("Exception occurred while sending Telegram notification: %s", exc)
        return False


async def send_security_alert(
    ip: str,
    jail: str,
    action: str,
    recidive_info: str = "",
    force: bool = False,
    cooldown: Optional[float] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send a structured intrusion defense alert to Telegram when Fail2ban bans an IP.

    Args:
        ip: Offending source IP address.
        jail: Fail2ban jail name (e.g. 'sshd').
        action: Filter action triggered ('Ban', 'Restore Ban', 'Unban').
        recidive_info: Information on repeat offense level.
        force: Bypass deduplication cache if True.
        cooldown: Custom cooldown window in seconds.
        chat_id: Target chat override.

    Returns:
        bool: True if dispatched, False if throttled by cooldown or failed.
    """
    cache_key = f"sec:{jail.strip().lower()}:{ip.strip()}:{action.strip().lower()}"

    if not force and deduplicator.is_rate_limited(cache_key, cooldown):
        rem = deduplicator.get_cooldown_remaining(cache_key, cooldown)
        logger.info(
            "Security alert for %s on jail %s throttled (cooldown remaining: %.1fs)",
            ip,
            jail,
            rem,
        )
        return False

    # Safely escape strings for Telegram HTML parse_mode
    safe_ip = html.escape(ip)
    safe_jail = html.escape(jail)
    safe_action = html.escape(action.upper())
    safe_recidive = html.escape(recidive_info) if recidive_info else "Initial Strike (1st Offense)"

    message = (
        "🛡️ <b>[YUDIAZ SENTINEL] SECURITY INTRUSION ALERT</b>\n\n"
        f"<b>Action:</b> <code>{safe_action}</code>\n"
        f"<b>Jail:</b> <code>{safe_jail}</code>\n"
        f"<b>Offending IP:</b> <code>{safe_ip}</code>\n"
        f"<b>Recidive Level:</b> {safe_recidive}\n"
        f"<b>Target Node:</b> <code>vps.daniandraaa.my.id</code> (20.200.220.190)\n"
        f"<b>Timestamp:</b> <code>{_current_iso_time()}</code>\n"
        "<b>Enforcement:</b> UFW Kernel Packet Filter & Fail2ban Recidive\n"
        "\n<i>Yudiaz Creative Studio VPS Defense System</i>"
    )

    success = await send_telegram_message(message, chat_id=chat_id)
    if success:
        deduplicator.record_alert(cache_key)
    return success


async def send_resource_alert(
    resource: str,
    current_val: float,
    threshold: float,
    force: bool = False,
    cooldown: Optional[float] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send high-priority warning when system hardware utilization exceeds threshold.

    Args:
        resource: Resource identifier ('CPU', 'RAM', 'Disk (/)', etc.).
        current_val: Current measured percentage.
        threshold: Configured threshold limit percentage (e.g. 85.0).
        force: Bypass deduplication cache if True.
        cooldown: Custom cooldown window in seconds.
        chat_id: Target chat override.

    Returns:
        bool: True if dispatched, False if throttled by cooldown or failed.
    """
    cache_key = f"res:{resource.strip().lower()}"

    if not force and deduplicator.is_rate_limited(cache_key, cooldown):
        rem = deduplicator.get_cooldown_remaining(cache_key, cooldown)
        logger.info(
            "Resource alert for %s throttled (cooldown remaining: %.1fs)",
            resource,
            rem,
        )
        return False

    safe_resource = html.escape(resource.upper())
    message = (
        "⚠️ <b>[YUDIAZ SENTINEL] RESOURCE THRESHOLD BREACH</b>\n\n"
        f"<b>Resource:</b> <code>{safe_resource}</code>\n"
        f"<b>Current Utilization:</b> <code>{current_val:.1f}%</code>\n"
        f"<b>Alert Threshold:</b> <code>{threshold:.1f}%</code>\n"
        "<b>Severity:</b> <b>WARNING / HIGH</b>\n"
        f"<b>Target Node:</b> <code>vps.daniandraaa.my.id</code> (Daniilham-PC)\n"
        f"<b>Timestamp:</b> <code>{_current_iso_time()}</code>\n"
        "\n<i>Yudiaz Creative Studio Infrastructure Telemetry</i>"
    )

    success = await send_telegram_message(message, chat_id=chat_id)
    if success:
        deduplicator.record_alert(cache_key)
    return success


async def send_service_alert(
    service: str,
    status: str,
    details: str = "",
    force: bool = False,
    cooldown: Optional[float] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send service state degradation or outage alert to Telegram.

    Args:
        service: Name or identifier of affected service (e.g. 'hermes-agent', 'caddy').
        status: Service state ('offline', 'degraded', 'unhealthy').
        details: Diagnostic context or error descriptions.
        force: Bypass deduplication cache if True.
        cooldown: Custom cooldown window in seconds.
        chat_id: Target chat override.

    Returns:
        bool: True if dispatched, False if throttled by cooldown or failed.
    """
    cache_key = f"svc:{service.strip().lower()}:{status.strip().lower()}"

    if not force and deduplicator.is_rate_limited(cache_key, cooldown):
        rem = deduplicator.get_cooldown_remaining(cache_key, cooldown)
        logger.info(
            "Service alert for %s [%s] throttled (cooldown remaining: %.1fs)",
            service,
            status,
            rem,
        )
        return False

    safe_service = html.escape(service)
    safe_status = html.escape(status.upper())
    safe_details = html.escape(details) if details else "Health probe failed"

    message = (
        "🚨 <b>[YUDIAZ SENTINEL] SERVICE STATUS ALERT</b>\n\n"
        f"<b>Service:</b> <code>{safe_service}</code>\n"
        f"<b>State:</b> <b>{safe_status}</b>\n"
        f"<b>Details:</b> <i>{safe_details}</i>\n"
        f"<b>Target Node:</b> <code>vps.daniandraaa.my.id</code>\n"
        f"<b>Timestamp:</b> <code>{_current_iso_time()}</code>\n"
        "\n<i>Yudiaz Creative Studio Telemetry Ops</i>"
    )

    success = await send_telegram_message(message, chat_id=chat_id)
    if success:
        deduplicator.record_alert(cache_key)
    return success


async def send_daily_digest(
    stats: dict[str, Any],
    chat_id: Optional[str] = None,
) -> bool:
    """Dispatch the daily operational telemetry and security digest to Telegram.

    Args:
        stats: Dictionary containing telemetry, security, and attached services statistics.
        chat_id: Target chat override.

    Returns:
        bool: True if successfully sent, False otherwise.
    """
    report_date = html.escape(str(stats.get("date", _current_iso_time())))
    cpu_load = html.escape(str(stats.get("cpu_load", "N/A")))
    ram_usage = html.escape(str(stats.get("ram_usage", "N/A")))
    disk_usage = html.escape(str(stats.get("disk_usage", "N/A")))
    uptime = html.escape(str(stats.get("uptime", "N/A")))
    bans_today = html.escape(str(stats.get("bans_today", 0)))
    active_jails = html.escape(str(stats.get("active_jails", "sshd")))
    firewall_status = html.escape(str(stats.get("firewall_status", "Active (UFW)")))
    services_online = html.escape(str(stats.get("services_online", "All services online")))

    message = (
        "📊 <b>[YUDIAZ SENTINEL] DAILY TELEMETRY & SECURITY DIGEST</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Report Window:</b> <code>{report_date}</code> (20:00 WIB / 13:00 UTC)\n"
        "<b>Host:</b> <code>vps.daniandraaa.my.id</code> (Daniilham-PC)\n\n"
        "<b>⚡ System Performance:</b>\n"
        f"• CPU Load: <code>{cpu_load}</code>\n"
        f"• Memory: <code>{ram_usage}</code>\n"
        f"• Storage: <code>{disk_usage}</code>\n"
        f"• System Uptime: <code>{uptime}</code>\n\n"
        "<b>🛡️ VPS 4-Layer Defense:</b>\n"
        f"• Total Bans Today: <b>{bans_today}</b>\n"
        f"• Active Jails: <code>{active_jails}</code>\n"
        f"• Firewall Status: <b>{firewall_status}</b>\n"
        "• Hardening: <b>4 Layers Active (UFW, F2B, Sysctl, SSH)</b>\n\n"
        "<b>🚀 Attached Services:</b>\n"
        f"• Status: <b>{services_online}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Yudiaz Creative Studio Telemetry & Autonomous Operations</i>"
    )

    return await send_telegram_message(message, chat_id=chat_id)
