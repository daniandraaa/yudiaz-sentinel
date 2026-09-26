"""FastAPI APIRouter definitions for Yudiaz Sentinel Telemetry & Operations API.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001 (Section 8)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import time
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
import psutil

from backend import __version__
from backend.collector import collector
from backend.probes import probe_all_services
from backend.specs import get_hardware_specs
from backend.team import get_team_roster

# Process start time for Sentinel daemon uptime calculation
DAEMON_START_TIME: float = time.time()

router = APIRouter(prefix="/api/v1", tags=["Sentinel Telemetry"])


def _standard_envelope(data: Any) -> Dict[str, Any]:
    """Standardized API response envelope adhering to Kael's architecture."""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = (
        now.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{int(now.microsecond / 1000):03d}Z"
    )
    return {
        "success": True,
        "timestamp": timestamp_str,
        "data": data,
    }


def _error_envelope(code: str, message: str, details: Any = None) -> Dict[str, Any]:
    """Standardized error envelope adhering to Kael's architecture."""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = (
        now.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{int(now.microsecond / 1000):03d}Z"
    )
    return {
        "success": False,
        "timestamp": timestamp_str,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


@router.get("/health", summary="System Liveness & Readiness Check")
async def get_health() -> Dict[str, Any]:
    """Endpoint 1: System Liveness & Readiness Check.

    Used by Caddy ingress and NOC probes to evaluate Sentinel process health.
    """
    try:
        now = time.time()
        uptime_sec = round(max(0.0, now - DAEMON_START_TIME), 2)
        proc = psutil.Process(os.getpid())
        rss_mb = round(proc.memory_info().rss / (1024 * 1024), 1)

        health_data = {
            "status": "healthy",
            "service": "yudiaz-sentinel",
            "version": __version__,
            "uptime_seconds": uptime_sec,
            "daemon_pid": os.getpid(),
            "memory_rss_mb": rss_mb,
        }
        return _standard_envelope(health_data)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "HEALTH_CHECK_ERROR",
                f"Failed to resolve daemon health: {exc}",
            ),
        )


@router.get("/metrics", summary="Real-time Telemetry Snapshot")
async def get_metrics() -> Dict[str, Any]:
    """Endpoint 2: Real-time Telemetry Snapshot.

    Returns instant CPU, RAM 54GB breakdown, Disks (NVMe & Ephemeral), and Uptime.
    """
    try:
        data = await collector.get_metrics()
        return _standard_envelope(data)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "METRIC_COLLECTION_ERROR",
                f"Unable to sample system metrics: {exc}",
            ),
        )


@router.get("/specs", summary="Hardware Baseline & Cloud Metadata")
async def get_specs() -> Dict[str, Any]:
    """Endpoint 3: Hardware Baseline & Cloud Metadata.

    Provides CPU architecture, physical memory, Azure region, and domain routing specs.
    """
    try:
        specs_data = get_hardware_specs()
        return _standard_envelope(specs_data)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "SPECS_ERROR",
                f"Failed to retrieve hardware specs: {exc}",
            ),
        )


@router.get("/projects", summary="Attached Projects & Services Status")
async def get_projects() -> Dict[str, Any]:
    """Endpoint 4: Attached Projects & Services Status.

    Concurrent non-blocking inspection of Hermes, 9Router, Caddy, Sentinel, Docker,
    and deployed production projects catalog.
    """
    try:
        probes_data = await probe_all_services()
        return _standard_envelope(probes_data)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "SERVICE_PROBE_ERROR",
                f"Failed to probe attached services: {exc}",
            ),
        )


@router.get("/team", summary="Yudiaz AI Agent Team Roster")
async def get_team() -> Dict[str, Any]:
    """Endpoint 5: Yudiaz AI Agent Team Roster.

    Returns operational directory for all 9 autonomous agents of Yudiaz Creative Studio.
    """
    try:
        roster_data = get_team_roster()
        return _standard_envelope(roster_data)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "TEAM_ROSTER_ERROR",
                f"Failed to fetch team catalog: {exc}",
            ),
        )


@router.get("/metrics/stream", summary="Live Server-Sent Events (SSE) Stream")
async def stream_metrics(request: Request) -> StreamingResponse:
    """Endpoint 6: Live Server-Sent Events (SSE) Stream.

    Pushes telemetry updates directly to browser clients every 2 seconds.
    Includes keep-alive comments to prevent stateful NAT/proxy timeout drops.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        # Initial immediate emission
        try:
            initial_tick = await collector.get_stream_tick()
            yield f"event: metric_tick\ndata: {json.dumps(initial_tick)}\n\n"
        except Exception:
            pass

        while True:
            # Detect client disconnect to cleanly tear down coroutine
            if await request.is_disconnected():
                break

            try:
                await asyncio.sleep(2.0)
                if await request.is_disconnected():
                    break

                tick_data = await collector.get_stream_tick()
                yield f"event: metric_tick\ndata: {json.dumps(tick_data)}\n\n"

                # Keepalive comment packet (Caddy / proxy bypass)
                now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%SZ")
                yield f": ping - {now_str}\n\n"
            except asyncio.CancelledError:
                break
            except Exception:
                # Shield stream against intermittent exceptions
                await asyncio.sleep(2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )
