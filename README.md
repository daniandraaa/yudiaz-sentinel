# Yudiaz Sentinel // VPS Telemetry & Observability Engine

[![Status](https://img.shields.io/badge/Status-Live%20Production-10B981?style=flat-square)](https://vps.daniandraaa.my.id)
[![Python](https://img.shields.io/badge/Python-3.12-6366F1?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00F2FE?style=flat-square&logo=fastapi&logoColor=black)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-25%2F25%20Passed-10B981?style=flat-square)](tests/)
[![Security](https://img.shields.io/badge/Security-TLS%201.3%20%2F%20Hardened-6366F1?style=flat-square)](docs/QA_AUDIT_REPORT.md)

**Yudiaz Sentinel** is a zero-overhead, high-performance infrastructure observability daemon and command console built specifically for **Yudiaz Creative Studio**. It provides real-time telemetry, hardware metrics, service health monitoring, and multi-agent AI cluster orchestration status.

🌐 **Production Deployment:** [https://vps.daniandraaa.my.id](https://vps.daniandraaa.my.id)  
🛡️ **Edge Ingress:** Caddy Reverse Proxy (TLS 1.3, HTTP/2 & HTTP/3 multiplexing)

---

## ⚡ Key Capabilities

- **Zero-Overhead Metrics Daemon:** Memory RSS footprint `< 52 MB` and `0.0%` idle CPU usage on a 54GB RAM / 4 vCPU Intel Xeon host.
- **Real-Time Streaming:** Native Server-Sent Events (SSE) stream pushing telemetry data every 2.0 seconds with zero buffering lag.
- **Hardware Telemetry Tri-Cluster:**
  - **vCPU:** Per-core utilization, Linux load averages (1m, 5m, 15m), and dynamic SVG 60-second activity sparkline.
  - **Memory:** Radial meter, RAM breakdown (*Used, Free, Cached, Available*), and Swap state.
  - **Storage:** Multi-partition NVMe monitoring (`/dev/root` and `/mnt`) with disk I/O throughput.
- **Live Deployed Projects Showcase:** Automated health and connectivity probes for all services running on the server (`vps.daniandraaa.my.id`, `api.daniandraaa.my.id`, Hermes Agent Platform).
- **AI Agent Team Hub:** Real-time roster and operational status of all 9 Yudiaz autonomous agents (Raziel, Kael, Nara, Senna, Idris, Mika, Viktor, Elara, Jovan).
- **Brand Identity:** Implements the official **Concept 2B (The Negative Space Portal)** visual language in dark luxury cyber-brutalism.

---

## 🏗️ System Architecture

```text
  [ Client Browser / Mobile Web ]
                 │
                 ▼ (HTTPS / TLS 1.3 / HTTP/3)
    ┌─────────────────────────┐
    │   Caddy Edge Proxy      │  Port 80/443 (Let's Encrypt Auto-TLS)
    └────────────┬────────────┘
                 │ (Internal Loopback / flush_interval -1)
                 ▼
    ┌─────────────────────────┐
    │  Yudiaz Sentinel Daemon │  Port 9229 (Python 3.12 + FastAPI + Uvicorn)
    │  ├─ Async Collector     │  1000ms TTL In-Memory Atomic Cache
    │  ├─ Live SSE Generator  │  2-Second Telemetry Ticker
    │  └─ Service Probers     │  Zero-Fork Non-Blocking Socket Probes
    └────────────┬────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
[ Linux Kernel ]    [ Docker & Daemons ]
/proc & psutil      Hermes (9119), 9Router (20128)
```

---

## 📂 Repository Structure

```text
yudiaz-sentinel/
├── backend/                  # Python 3.12 FastAPI core
│   ├── collector.py          # Asynchronous system probes (CPU, RAM, Disk, IO)
│   ├── probes.py             # Service status probes & deployed projects catalog
│   ├── routes.py             # REST API endpoints & SSE streaming router
│   ├── specs.py              # Hardware & cloud datacenter metadata
│   ├── team.py               # AI Agent roster & department definitions
│   └── main.py               # Application factory & static mount
├── frontend/                 # Production SPA Dashboard
│   ├── index.html            # Dark luxury brutalist telemetry console
│   └── assets/               # Brand logos, favicons, & UI icons
├── deploy/                   # Production systemd & ingress configuration
│   ├── Caddyfile.snippet     # Reverse proxy & SSE buffering bypass rules
│   └── yudiaz-sentinel.service # Systemd unit file with memory guardrails
├── docs/                     # Technical specifications & QA audits
│   ├── ARCHITECTURE.md       # Full architecture specification (YCS-ARCH-2026-001)
│   ├── DESIGN_SPEC.md        # UI/UX design tokens & component specifications
│   └── QA_AUDIT_REPORT.md    # Automated E2E verification report (YCS-QA-2026-001)
├── tests/                    # Automated testing suite
│   ├── test_api.py           # Unit tests for REST & SSE endpoints
│   └── test_production_e2e.py # Live end-to-end integration & latency tests
└── pyproject.toml            # Project dependencies & toolchain definition
```

---

## 📡 REST & Streaming API Reference

All REST endpoints return standardized JSON envelopes:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Daemon heartbeat, PID, RSS memory, and uptime |
| `GET` | `/api/v1/metrics` | Snapshot of vCPU, RAM, Disk array, and load averages |
| `GET` | `/api/v1/specs` | Hardware, OS, Kernel, and Cloud metadata |
| `GET` | `/api/v1/projects` | Status of all services and deployed projects |
| `GET` | `/api/v1/team` | Yudiaz 9-agent roster and department assignments |
| `GET` | `/api/v1/metrics/stream` | Server-Sent Events (SSE) live push stream (2s tick) |

---

## 🚀 Quick Start (Local Development)

```bash
# 1. Clone repository
git clone https://github.com/daniandraaa/yudiaz-sentinel.git
cd yudiaz-sentinel

# 2. Setup virtual environment via uv
uv venv --python /usr/bin/python3.12 .venv
source .venv/bin/activate
uv pip install -e .

# 3. Run development server
uvicorn backend.main:app --host 127.0.0.1 --port 9229 --reload

# 4. Run test suite
pytest tests/ -v
```

---

## 👥 Yudiaz Creative Studio Engineering Team

- **Daniandra Prayudisty** — Founder & CEO
- **Raziel Hendrix** — CTO & Orchestrator
- **Kael Ashford** — Lead Architect
- **Nara Vasquez** — Lead Researcher
- **Senna Louviere** — Creative Director
- **Idris Nakamura** — Senior Developer
- **Mika Stellan** — Frontend Engineer
- **Viktor Moreau** — Lead QA & Security Engineer
- **Elara Sinclair** — PA to CEO
- **Jovan Aritza** — Intelligence Officer

---

© 2026 Yudiaz Creative Studio. All rights reserved.
