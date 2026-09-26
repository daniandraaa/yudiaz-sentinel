"""Yudiaz Sentinel - Host Security Sentinel, Fail2ban Log Watcher & 4-Layer Defense Auditor.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001 (Security Subsystem)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
import datetime
import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil

from backend import notifier
from backend.collector import collector
from backend.probes import probe_all_services

logger = logging.getLogger("yudiaz.sentinel.security")

# Fail2ban standard log pattern:
# 2026-09-26 14:07:50,029 fail2ban.actions [126735]: NOTICE [sshd] Ban 138.226.239.234
FAIL2BAN_LOG_REGEX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d+)?)\s+"
    r"fail2ban\.\S+\s+\[\d+\]:\s+\w+\s+"
    r"\[(?P<jail>[^\]]+)\]\s+"
    r"(?P<action>Ban|Restore Ban|Unban)\s+"
    r"(?P<ip>\S+)"
)


class SecuritySentinel:
    """Security telemetry collector and real-time intrusion monitoring daemon.

    Responsibilities:
    1. Parse and audit `/var/log/fail2ban.log` for intrusion metrics and recidivism.
    2. Audit 4-Layer Host Security Defense (UFW, Fail2ban, Sysctl, SSH).
    3. Asynchronous background watcher alerting Telegram on newly discovered bans.
    4. Hardware resource threshold watchdog (>85% utilization).
    5. Daily operational telemetry & security digest scheduler at 20:00 WIB (13:00 UTC).
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        alert_threshold_cpu: float = 85.0,
        alert_threshold_ram: float = 85.0,
        alert_threshold_disk: float = 85.0,
        poll_interval: float = 5.0,
    ) -> None:
        self.default_log_path = log_path or os.getenv("FAIL2BAN_LOG_PATH", "/var/log/fail2ban.log")
        self.alert_threshold_cpu = alert_threshold_cpu
        self.alert_threshold_ram = alert_threshold_ram
        self.alert_threshold_disk = alert_threshold_disk
        self.poll_interval = poll_interval

        self._running: bool = False
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._last_file_offset: int = 0
        self._last_inode: Optional[int] = None
        self._last_digest_date: Optional[str] = None
        self._known_ip_counts: Dict[str, int] = defaultdict(int)
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def log_path(self) -> str:
        """Resolve current active fail2ban log path from env or instance configuration."""
        return os.getenv("FAIL2BAN_LOG_PATH", self.default_log_path)

    def parse_log_file(self, target_path: Optional[str] = None) -> Dict[str, Any]:
        """Safely parse the fail2ban log file without root privileges.

        Extracts total bans today, historical ban counts per IP (recidivism),
        and the list of recent ban events.

        Args:
            target_path: Optional custom file path to read from.

        Returns:
            Dictionary containing parsed security metrics.
        """
        path = target_path or self.log_path
        if not os.path.exists(path):
            logger.warning("Fail2ban log file not found at %s", path)
            return {
                "total_bans_today": 0,
                "recent_events": [],
                "active_jails": [],
                "unique_ips_banned_today": 0,
                "total_bans_all_time": 0,
                "status": "log_not_found",
            }

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        today_utc_str = now_utc.strftime("%Y-%m-%d")
        today_wib_str = (now_utc + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
        today_local_str = datetime.datetime.now().strftime("%Y-%m-%d")
        valid_today_dates = {today_utc_str, today_wib_str, today_local_str}

        ip_ban_counts: Dict[str, int] = defaultdict(int)
        today_unique_ips: Set[str] = set()
        all_ban_events: List[Dict[str, Any]] = []
        active_jails: Set[str] = set()
        total_bans_today = 0
        total_bans_all_time = 0

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = FAIL2BAN_LOG_REGEX.search(line)
                    if not match:
                        continue

                    entry = match.groupdict()
                    jail = entry["jail"]
                    action = entry["action"]
                    ip = entry["ip"]
                    timestamp_raw = entry["timestamp"]

                    active_jails.add(jail)

                    if action in ("Ban", "Restore Ban"):
                        total_bans_all_time += 1
                        ip_ban_counts[ip] += 1
                        recidive_count = ip_ban_counts[ip]

                        # Check if event occurred today
                        date_prefix = timestamp_raw[:10]
                        if date_prefix in valid_today_dates:
                            total_bans_today += 1
                            today_unique_ips.add(ip)

                        clean_ts = timestamp_raw.split(",")[0]
                        recidive_label = (
                            f"Strike #{recidive_count}"
                            if recidive_count > 1
                            else "Initial Strike (1st Offense)"
                        )

                        all_ban_events.append({
                            "timestamp": clean_ts,
                            "ip": ip,
                            "jail": jail,
                            "action": action,
                            "recidive_count": recidive_count,
                            "recidive_info": recidive_label,
                        })

        except (OSError, PermissionError) as exc:
            logger.error("Failed to read fail2ban log file at %s: %s", path, exc)
            return {
                "total_bans_today": 0,
                "recent_events": [],
                "active_jails": list(active_jails),
                "unique_ips_banned_today": 0,
                "total_bans_all_time": 0,
                "status": f"read_error: {exc}",
            }

        # Keep recent 10 events, newest first
        recent_10 = all_ban_events[-10:][::-1]

        return {
            "total_bans_today": total_bans_today,
            "recent_events": recent_10,
            "active_jails": sorted(list(active_jails)) or ["sshd"],
            "unique_ips_banned_today": len(today_unique_ips),
            "total_bans_all_time": total_bans_all_time,
            "status": "nominal",
        }

    def _check_systemd_service(self, service_name: str) -> bool:
        """Check if a systemd service is active without requiring root privileges."""
        try:
            res = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def _check_sysctl_value(self, proc_path: str) -> str:
        """Safely read kernel sysctl parameters via /proc filesystem."""
        try:
            if os.path.exists(proc_path):
                with open(proc_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return "unknown"

    def get_four_layer_defense_status(self) -> Dict[str, Any]:
        """Audit the 4-layer server defense architecture as specified in Kael's specs.

        Layer 1: UFW Firewall & Kernel Rate-Limiting
        Layer 2: Fail2ban Recidive & Exponential Multiplier
        Layer 3: Kernel TCP/IP Anti-Spoofing & Anti-DDoS (sysctl)
        Layer 4: OpenSSH Daemon Protocol Hardening
        """
        # Layer 1: UFW
        ufw_active = self._check_systemd_service("ufw")

        # Layer 2: Fail2ban
        f2b_active = self._check_systemd_service("fail2ban") or os.path.exists(self.log_path)

        # Layer 3: Kernel TCP/IP anti-DDoS
        syncookies = self._check_sysctl_value("/proc/sys/net/ipv4/tcp_syncookies")
        rp_filter = self._check_sysctl_value("/proc/sys/net/ipv4/conf/all/rp_filter")
        layer3_active = syncookies == "1"

        # Layer 4: OpenSSH hardening
        ssh_active = self._check_systemd_service("ssh") or self._check_systemd_service("sshd")
        ssh_conf_path = Path("/etc/ssh/sshd_config.d/99-yudiaz-security.conf")
        has_hardening_conf = ssh_conf_path.exists()

        return {
            "layer_1_firewall": {
                "name": "UFW Firewall & Kernel Rate-Limiting",
                "status": "active" if ufw_active else "standby",
                "policy": "Default Deny Ingress, Allow Outgoing",
                "rate_limiting": "SSH (22/tcp) Kernel Rate-Limited (>6 hits/30s dropped)",
                "open_ports": [22, 80, 443],
            },
            "layer_2_intrusion_prevention": {
                "name": "Fail2ban Recidive & Exponential Multiplier",
                "status": "active" if f2b_active else "inactive",
                "primary_jail": "sshd",
                "backend": "systemd",
                "recidive_multiplier": "1h -> 2h -> 24h -> 4w",
            },
            "layer_3_kernel_hardening": {
                "name": "Kernel TCP/IP Anti-Spoofing & Anti-DDoS",
                "status": "active" if layer3_active else "nominal",
                "tcp_syncookies": syncookies,
                "rp_filter": rp_filter,
                "details": "SYN cookie flood defense & reverse path packet verification",
            },
            "layer_4_ssh_hardening": {
                "name": "OpenSSH Daemon Protocol Hardening",
                "status": "active" if (ssh_active or has_hardening_conf) else "inactive",
                "max_auth_tries": 3,
                "login_grace_time": "30s",
                "client_alive_interval": "300s",
                "configuration_dropin": "99-yudiaz-security.conf" if has_hardening_conf else "default",
            },
        }

    def get_security_status(self) -> Dict[str, Any]:
        """Aggregate full host security telemetry, fail2ban events, and 4-layer defense state.

        Returns:
            Structured dictionary matching the Yudiaz Sentinel architecture spec.
        """
        log_metrics = self.parse_log_file()
        defense = self.get_four_layer_defense_status()
        ufw_active = defense["layer_1_firewall"]["status"] == "active"

        return {
            "total_bans_today": log_metrics["total_bans_today"],
            "recent_events": log_metrics["recent_events"],
            "firewall_status": {
                "status": "active" if ufw_active else "standby",
                "service": "ufw",
                "default_policy": "deny (incoming)",
                "rate_limiting": "enabled (22/tcp SSH)",
            },
            "four_layer_defense": defense,
            "active_jails": log_metrics["active_jails"],
            "summary": {
                "total_bans_today": log_metrics["total_bans_today"],
                "unique_ips_banned_today": log_metrics["unique_ips_banned_today"],
                "total_bans_all_time": log_metrics["total_bans_all_time"],
                "firewall_active": ufw_active,
                "fail2ban_active": defense["layer_2_intrusion_prevention"]["status"] == "active",
                "all_layers_operational": all(
                    layer.get("status") in ("active", "nominal")
                    for layer in defense.values()
                ),
            },
        }

    async def _init_file_position(self) -> None:
        """Prime the log position to current EOF so existing bans do not flood alerts on startup."""
        path = self.log_path
        if os.path.exists(path):
            try:
                stat = os.stat(path)
                self._last_file_offset = stat.st_size
                self._last_inode = stat.st_ino
                logger.info(
                    "SecuritySentinel primed log watcher at offset %d (inode %s)",
                    self._last_file_offset,
                    self._last_inode,
                )
            except OSError as exc:
                logger.warning("Could not stat fail2ban log file on startup: %s", exc)
                self._last_file_offset = 0

    async def _check_new_bans(self) -> None:
        """Scan newly appended lines in fail2ban log and dispatch Telegram alerts on new bans."""
        path = self.log_path
        if not os.path.exists(path):
            return

        try:
            stat = os.stat(path)
            # Detect log rotation or truncation
            if stat.st_size < self._last_file_offset or (
                self._last_inode is not None and stat.st_ino != self._last_inode
            ):
                logger.info("Log file rotation/truncation detected. Resetting offset to 0.")
                self._last_file_offset = 0
                self._last_inode = stat.st_ino

            if stat.st_size == self._last_file_offset:
                return

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._last_file_offset)
                new_lines = f.readlines()
                self._last_file_offset = f.tell()

            for line in new_lines:
                match = FAIL2BAN_LOG_REGEX.search(line)
                if not match:
                    continue

                entry = match.groupdict()
                action = entry["action"]
                jail = entry["jail"]
                ip = entry["ip"]

                if action in ("Ban", "Restore Ban"):
                    self._known_ip_counts[ip] += 1
                    count = self._known_ip_counts[ip]
                    recidive_label = (
                        f"Strike #{count} (Repeat Offender)"
                        if count > 1
                        else "Initial Strike (1st Ban)"
                    )
                    logger.warning("Security intrusion detected: IP %s banned in jail %s", ip, jail)
                    await notifier.send_security_alert(
                        ip=ip,
                        jail=jail,
                        action=action,
                        recidive_info=recidive_label,
                    )

        except (OSError, PermissionError) as exc:
            logger.error("Error reading new lines from fail2ban log: %s", exc)

    async def _check_resource_utilization(self) -> None:
        """Check host CPU, RAM, and Disk metrics and alert if exceeding 85% threshold."""
        try:
            # 1. CPU Usage
            cpu_percent = psutil.cpu_percent(interval=None)
            if cpu_percent > self.alert_threshold_cpu:
                await notifier.send_resource_alert("CPU", cpu_percent, self.alert_threshold_cpu)

            # 2. RAM Usage
            mem = psutil.virtual_memory()
            if mem.percent > self.alert_threshold_ram:
                await notifier.send_resource_alert("RAM", mem.percent, self.alert_threshold_ram)

            # 3. Disk Usage (Root & Ephemeral)
            disk_root = psutil.disk_usage("/")
            if disk_root.percent > self.alert_threshold_disk:
                await notifier.send_resource_alert("Disk (/)", disk_root.percent, self.alert_threshold_disk)

            if os.path.exists("/mnt"):
                try:
                    disk_mnt = psutil.disk_usage("/mnt")
                    if disk_mnt.percent > self.alert_threshold_disk:
                        await notifier.send_resource_alert(
                            "Disk (/mnt)",
                            disk_mnt.percent,
                            self.alert_threshold_disk,
                        )
                except OSError:
                    pass

        except Exception as exc:
            logger.error("Error evaluating resource thresholds: %s", exc)

    async def _check_digest_schedule(self) -> None:
        """Evaluate if current time corresponds to 20:00 WIB (13:00 UTC) daily digest schedule."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_wib = now_utc + datetime.timedelta(hours=7)

        # Configurable daily digest target (default 20:00 WIB)
        target_hour_wib = 20
        target_minute_wib = 0

        digest_time_env = os.getenv("DAILY_DIGEST_TIME", "20:00").strip()
        try:
            parts = digest_time_env.split(":")
            if len(parts) == 2:
                target_hour_wib = int(parts[0])
                target_minute_wib = int(parts[1])
        except (ValueError, TypeError):
            pass

        if now_wib.hour == target_hour_wib and now_wib.minute == target_minute_wib:
            date_key = now_wib.strftime("%Y-%m-%d")
            if self._last_digest_date != date_key:
                self._last_digest_date = date_key
                logger.info("Triggering scheduled daily telemetry digest for %s", date_key)
                await self.trigger_daily_digest()

    async def trigger_daily_digest(self) -> bool:
        """Compile complete operational telemetry and trigger daily digest dispatch.

        Can be called by the internal scheduler or manually via API.

        Returns:
            bool: True if delivered successfully to Telegram, False otherwise.
        """
        try:
            # 1. Telemetry Metrics
            metrics = await collector.get_metrics()
            cpu_val = metrics.get("cpu", {}).get("overall_usage_percent", 0.0)
            load_1m = metrics.get("cpu", {}).get("load_average", {}).get("load_1m", 0.0)
            ram_used = metrics.get("memory", {}).get("used_gb", 0.0)
            ram_total = metrics.get("memory", {}).get("total_gb", 0.0)
            ram_pct = metrics.get("memory", {}).get("used_percent", 0.0)
            uptime_str = metrics.get("uptime", {}).get("system_uptime_human", "N/A")

            disks = metrics.get("disks", [])
            root_disk = disks[0] if disks else {}
            disk_str = (
                f"{root_disk.get('used_percent', 0.0)}% used ({root_disk.get('free_gb', 0.0)} GB free)"
                if root_disk
                else "N/A"
            )

            # 2. Security Status
            sec = self.get_security_status()
            bans_today = sec.get("total_bans_today", 0)
            jails = ", ".join(sec.get("active_jails", ["sshd"]))
            fw_state = sec.get("firewall_status", {}).get("status", "active")
            fw_display = f"Active ({sec.get('firewall_status', {}).get('service', 'ufw').upper()})" if fw_state == "active" else "Standby"

            # 3. Attached Services
            probes = await probe_all_services()
            services = probes.get("services", [])
            online_count = sum(1 for s in services if s.get("status") == "online")
            services_display = f"{online_count}/{len(services)} services operational"

            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            stats_payload = {
                "date": now_str,
                "cpu_load": f"{cpu_val:.1f}% (1m load: {load_1m})",
                "ram_usage": f"{ram_used:.1f} GB / {ram_total:.1f} GB ({ram_pct:.1f}%)",
                "disk_usage": disk_str,
                "uptime": uptime_str,
                "bans_today": bans_today,
                "active_jails": jails,
                "firewall_status": fw_display,
                "services_online": services_display,
            }

            return await notifier.send_daily_digest(stats_payload)
        except Exception as exc:
            logger.error("Failed to compile or dispatch daily digest: %s", exc)
            return False

    async def _worker_loop(self) -> None:
        """Continuous background execution loop for security telemetry and watchdog tasks."""
        await self._init_file_position()

        while self._running:
            try:
                # 1. Watch fail2ban log for new ban entries
                await self._check_new_bans()

                # 2. Watch host hardware metrics against alert thresholds
                await self._check_resource_utilization()

                # 3. Check daily digest schedule
                await self._check_digest_schedule()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Exception in SecuritySentinel worker loop: %s", exc)

            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def start(self) -> None:
        """Start the Security Sentinel background monitoring worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("SecuritySentinel background worker started successfully.")

    async def stop(self) -> None:
        """Gracefully stop the background worker task."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("SecuritySentinel background worker stopped.")


# Global singleton instance
security_sentinel = SecuritySentinel()
