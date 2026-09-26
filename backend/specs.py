"""Hardware baseline, operating system, and cloud provider metadata.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001
"""

from __future__ import annotations

import os
import platform
from typing import Any, Dict


def get_hardware_specs() -> Dict[str, Any]:
    """Retrieve static baseline hardware, kernel, network, and cloud metadata.

    Calibrated specifically for Daniilham-PC (Azure Seoul Korea Central).
    """
    uname = platform.uname()
    kernel_str = f"Linux {uname.release} {uname.machine}"

    # Model extraction from /proc/cpuinfo if available
    cpu_model = "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz"
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    return {
        "server": {
            "hostname": uname.node or "Daniilham-PC",
            "os": "Ubuntu 24.04 LTS (Noble Numbat)",
            "kernel": kernel_str,
            "architecture": uname.machine or "x86_64",
        },
        "cpu": {
            "model": cpu_model,
            "cores_physical": 4,
            "cores_logical": 4,
            "base_clock": "2.80 GHz",
        },
        "memory": {
            "total_physical_ram_gb": 54.0,
            "total_swap_gb": 8.0,
        },
        "storage": {
            "root_partition": "61 GB NVMe SSD",
            "ephemeral_partition": "110 GB Azure Resource SSD",
        },
        "network": {
            "public_ip": "20.200.220.190",
            "cloud_provider": "Microsoft Azure",
            "region": "Korea Central (Seoul, South Korea)",
            "primary_subdomain": "vps.daniandraaa.my.id",
            "fallback_subdomain": "vps.20.200.220.190.sslip.io",
        },
    }
