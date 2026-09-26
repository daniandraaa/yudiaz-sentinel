# YUDIAZ SENTINEL — SYSTEM ARCHITECTURE & DEPLOYMENT BLUEPRINT
**Next-Generation Lightweight VPS Infrastructure & AI Agent Cluster Telemetry**

```
Document Reference : YCS-ARCH-2026-001
Classification     : Internal Engineering Specification
Author             : Kael Ashford (Lead Architect, Yudiaz Creative Studio)
Reviewed By        : Raziel Hendrix (CTO)
Target Audience    : Idris Nakamura (Senior Developer), Mika Stellan (Frontend Engineer), Viktor Moreau (Lead QA)
Stakeholder        : Daniandra Prayudisty (CEO)
Status             : APPROVED & READY FOR ENGINEERING
Last Updated       : September 2026
```

---

## 1. Executive Summary & Architectural Vision

**Yudiaz Sentinel** adalah sistem monitoring VPS kelas produksi berbobot ultra-ringan (*zero-overhead telemetry*) yang dirancang khusus untuk memonitor infrastruktur server utama Yudiaz Creative Studio di Microsoft Azure (Region: Seoul, South Korea).

Sistem ini didesain untuk memberikan observabilitas *real-time* 360 derajat terhadap:
1. **Host Telemetry**: Beban vCPU (per-core + load average), Alokasi Memori 54 GB, dan Storage Tier NVMe/Ephemeral.
2. **Project Runtime Health**: Integritas layanan inti yang aktif pada host (Hermes Agent Platform, 9Router AI Gateway LLM Proxy, Caddy Reverse Proxy, dan Sentinel Engine).
3. **AI Agent Cluster Roster**: Metadata status operasional dan profil 9 agen otonom tim Yudiaz Creative Studio.
4. **Live Streaming Dashboard**: Visualisasi real-time dengan latensi rendah melalui Server-Sent Events (SSE) tanpa membebani siklus komputasi server.

Prinsip arsitektur yang ditetapkan:
> *"Arsitektur yang baik tidak menambah beban pada sistem yang dimonitornya. Zero unnecessary bloat, non-blocking telemetry, clean decoupling, dan fault-tolerant isolation."*

---

## 2. System Architecture Diagram

Berikut adalah topologi arsitektur sistem dari level Edge Ingress hingga Telemetry Kernel Subsystem:

```
+===================================================================================================+
|                                    CLIENT & PRESENTATION LAYER                                    |
|                                                                                                   |
|  [ CEO / CTO Desktop / Mobile Browser ]               [ Executive Live Wallboard / NOC ]          |
|      (vps.daniandraaa.my.id)                                (vps.20.200.220.190.sslip.io)         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  | HTTPS (TLS 1.3 / HTTP/2 / SNI)
                                                  v
+===================================================================================================+
|                                  EDGE & INGRESS LAYER (PORT 80/443)                               |
|                                                                                                   |
|                                         CADDY REVERSE PROXY                                       |
|  * Auto TLS via Let's Encrypt / ZeroSSL            * SSE Buffering Bypass (X-Accel-Buffering: off)|
|  * SNI Routing: vps.daniandraaa.my.id              * Security Headers (CSP, HSTS, X-Frame-Options)|
|  * Fallback SNI: vps.20.200.220.190.sslip.io       * Upstream Keep-Alive Pool                     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  | HTTP/1.1 Loopback (127.0.0.1:9229)
                                                  v
+===================================================================================================+
|                                APPLICATION LAYER: YUDIAZ SENTINEL                                 |
|                         (Python 3.12 + FastAPI / Async Uvicorn Daemon)                            |
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  | Web Router & Static Asset Controller                                                        |  |
|  | - Single-Page Dashboard (/ or static index.html)                                            |  |
|  | - Modern Tailwind CSS + Lucide Icons + Chart.js Canvas Sparklines                          |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | REST API Router (/api/v1)                                                                   |  |
|  | - /health        : Synthetic health check (Liveness / Readiness)                            |  |
|  | - /metrics       : Snapshot JSON telemetry (vCPU, RAM, Disks, Uptime)                       |  |
|  | - /specs         : Hardware baseline, Kernel, Azure Cloud Metadata                          |  |
|  | - /projects      : Service inspection (Hermes, 9Router, Caddy, Sentinel)                    |  |
|  | - /team          : Yudiaz 9-Agent status directory & telemetry                              |  |
|  | - /metrics/stream: SSE EventStream (Ticker 2s, client-driven heartbeat)                     |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | Core Telemetry Engine (Non-blocking Async Workers)                                          |  |
|  | - Cached Collector Pool (Asyncio Background Task, 1000ms TTL Cache)                         |  |
|  | - Process & Socket Health Evaluators (Zero-fork direct probes)                              |  |
+---------------------------------------------------------------------------------------------------+
                                                  |
          +---------------------------------------+---------------------------------------+
          |                                       |                                       |
          v                                       v                                       v
+-----------------------+               +-----------------------+               +-----------------------+
|  OS & KERNEL PROBES   |               | DOCKER / DAEMON PROBES|               | STORAGE & DISK MOUNTS |
|                       |               |                       |               |                       |
| - psutil / /proc /sys |               | - 9Router (Docker/API)|               | - /dev/root (61 GB)   |
| - 4x vCPU Xeon 8370C  |               |   port 20128 / HTTP   |               |   Root NVMe OS disk   |
| - 54GB RAM + 8GB Swap |               | - Hermes Agent (Port  |               | - /dev/sdb1 (110 GB)  |
| - 1m/5m/15m Load Avg  |               |   9119 System Daemon) |               |   Mounted at /mnt     |
| - Net I/O & TCP Conns |               | - Caddy Systemd Unit  |               |   Ephemeral Resource  |
+-----------------------+               +-----------------------+               +-----------------------+
```

---

## 3. Technology Stack Rationale & ADRs

### ADR-001: Backend Framework Selection
- **Status**: ACCEPTED
- **Context**: Host memiliki kapasitas RAM 54 GB dan 4 vCPU, namun menjalankan agent LLM orkestrasi dan gateway router yang menuntut responsivitas tinggi. Monitoring engine tidak boleh memakan resource signifikan (< 50 MB RSS RAM, < 0.5% CPU baseline).
- **Options Considered**:
  1. *Go / Rust compiled binary*: Performa sangat tinggi, namun *maintenance agility* untuk tim internal lebih lambat jika tim developer inti (Idris Nakamura) mahir di ekosistem Python/TypeScript.
  2. *Node.js / Express*: Footprint memory 80-120 MB, membutuhkan dependensi `node_modules` yang besar.
  3. *Python 3.12 + FastAPI + Uvicorn (uvloop)*: Footprint memory sangat terukur (~35 MB), async native, OpenAPI schema auto-generation, integrasi `psutil` sangat matang dan teruji di Linux kernel.
- **Decision**: **Python 3.12 + FastAPI + Uvicorn** diisolasi dengan toolchain `uv`.
- **Consequences**: Sangat mudah di-audit oleh Viktor Moreau, zero compile step, startup < 0.8 detik.

### ADR-002: Real-time Communication Protocol
- **Status**: ACCEPTED
- **Context**: Dashboard membutuhkan live ticker per 2 detik untuk data vCPU, RAM, dan I/O tanpa latensi HTTP handshake berulang.
- **Options Considered**:
  1. *Client Polling (setInterval fetch per 2s)*: Boros header HTTP, overhead TCP handshake berulang jika HTTP/1.1.
  2. *Full-duplex WebSockets*: Memerlukan framing stateful, connection maintenance, ping/pong frames, serta penanganan error connection upgrade di Caddy.
  3. *Server-Sent Events (SSE - `text/event-stream`)*: Native browser standard (`EventSource`), otomatis re-connect bawaan browser, uni-directional (Server ke Client) yang sangat pas untuk use-case telemetry, bekerja mulus di atas HTTP/2 melalui Caddy reverse proxy.
- **Decision**: **Server-Sent Events (SSE)** pada endpoint `/api/v1/metrics/stream`.
- **Consequences**: Mika Stellan hanya membutuhkan ~15 baris vanilla JavaScript native `EventSource` di frontend tanpa library eksternal.

### ADR-003: Frontend Architecture & Asset Delivery
- **Status**: ACCEPTED
- **Context**: Aplikasi monitoring harus bisa dibuka secara instan dari workstation CEO Daniandra, smartphone, maupun display lab tanpa membutuhkan proses build webpack/vite yang rumit di sisi server.
- **Options Considered**:
  1. *Next.js / SSR*: Overkill, menambah satu lagi Node runtime server daemon yang memakan RAM 150-250MB.
  2. *Vite + React SPA*: Membutuhkan compile build step (`npm run build`) sebelum rilis.
  3. *Vanilla Modern HTML5 + Tailwind CSS CDN + Chart.js + Lucide Icons*: Disajikan langsung sebagai file statis via FastAPI `StaticFiles` atau direktori Caddy. Zero build step, hot-reloadable, single HTML canvas rendering, memory 0 MB di server.
- **Decision**: **Single-file / Zero-build Modern SPA** (Vanilla JS ES6 Modules + Tailwind CSS + Chart.js + Lucide Icons) disajikan langsung oleh Sentinel Daemon.
- **Consequences**: Sangat cepat dimuat (< 150ms First Contentful Paint via Caddy HTTP/2 cache).

---

## 4. Hardware Baseline & System Matrix

Sentinel dikalibrasi secara presisi terhadap spesifikasi aktual server `Daniilham-PC`:

| Komponen Hardware | Spesifikasi Riil Server | Probe Target & Metric Keys |
| :--- | :--- | :--- |
| **Hostname** | `Daniilham-PC` | `os.uname().nodename` |
| **Operating System** | `Ubuntu 24.04 LTS` (Kernel: `6.17.0-1022-azure x86_64`) | `/etc/os-release`, `uname -r` |
| **Cloud Provider** | `Microsoft Azure` (Virtual Machine) | Azure Instance Metadata Service (IMDS) / Fallback config |
| **Cloud Region** | `Korea Central (Seoul, South Korea)` | Static metadata / IMDS |
| **Public IP Address**| `20.200.220.190` | Edge endpoint mapping |
| **vCPU Architecture**| 4 vCPU Intel(R) Xeon(R) Platinum 8370C @ 2.80GHz | `psutil.cpu_percent(percpu=True)`, `/proc/cpuinfo` |
| **CPU Load Average** | 1 min, 5 min, 15 min | `os.getloadavg()` |
| **Physical RAM** | Total: `54 GiB` (~57,982 MB) | `psutil.virtual_memory()` (used, free, buff/cache, available) |
| **Swap Storage** | Total: `8.0 GiB` | `psutil.swap_memory()` |
| **Primary NVMe Disk**| `/dev/root` mounted on `/` (Capacity: `61 GB`) | `psutil.disk_usage('/')` |
| **Ephemeral Disk** | `/dev/sdb1` mounted on `/mnt` (Capacity: `110 GB` Resource) | `psutil.disk_usage('/mnt')` |

---

## 5. Projects & Service Integration Catalog

Sentinel mengawasi status kesehatan 5 project inti yang berdampingan pada host:

```
+----+----------------------+---------+---------------------------+-----------------------------------+
| No | Service / Project    | Port    | Process / Runtime Type    | Health Check Inspection Strategy  |
+----+----------------------+---------+---------------------------+-----------------------------------+
| 1  | Hermes Agent Platform| 9119    | Python / System Daemon    | TCP Socket Probe + HTTP Status    |
|    |                      |         | Multi-profile Agent Core  | Check (127.0.0.1:9119)            |
+----+----------------------+---------+---------------------------+-----------------------------------+
| 2  | 9Router AI Gateway   | 20128   | Docker Container          | HTTP GET /health or TCP Ping      |
|    | (LLM Proxy)          |         | (local/9router:0.5.81-npm)| (127.0.0.1:20128)                 |
+----+----------------------+---------+---------------------------+-----------------------------------+
| 3  | Caddy Reverse Proxy  | 80/443  | Systemd Service (`caddy`) | systemctl is-active / TCP 80/443  |
+----+----------------------+---------+---------------------------+-----------------------------------+
| 4  | Yudiaz Creative Core | N/A     | Local Repos & Assets      | Directory existence & NVMe space  |
|    | Assets & Repos       |         | (/home/daniilham)         | read sanity                       |
+----+----------------------+---------+---------------------------+-----------------------------------+
| 5  | Yudiaz Sentinel      | 9229    | Python 3.12 FastAPI       | Self-diagnostic internal health   |
|    | Monitoring Engine    | (bind)  | Systemd Service           | probe (GET /api/v1/health)        |
+----+----------------------+---------+---------------------------+-----------------------------------+
```

---

## 6. Yudiaz AI Agent Cluster Roster

Sentinel mengekspos direktori agen AI studio beserta spesialisasi dan status sinkronisasi:

| # | Agent Name | Role | Studio Function & Responsibilities | Profile Status |
| :- | :--- | :--- | :--- | :--- |
| 1 | **Raziel Hendrix** | CTO & Orchestrator | Arsitek operasional, delegasi multi-agent, evaluasi sistem tingkat tinggi | `active` (Session Leader) |
| 2 | **Kael Ashford** | Lead Architect | System design, blueprint, database schema, API contracts, ADR | `active` |
| 3 | **Nara Vasquez** | Lead Researcher | Riset teknologi komputasi, benchmark model LLM, audit arsitektur | `active` |
| 4 | **Senna Louviere**| Creative Director | UI/UX aesthetic, brand styling, visual standards, human interface | `active` |
| 5 | **Idris Nakamura**| Senior Developer | Backend, API engineering, systems programming, script automation | `active` |
| 6 | **Mika Stellan** | Frontend Engineer | SPA dashboard, reactive UI, Tailwind CSS, charts & interactions | `active` |
| 7 | **Viktor Moreau** | Lead QA | Verification, end-to-end testing, security testing, performance audit | `active` |
| 8 | **Elara Sinclair** | PA to CEO | Daily operations, project schedules, executive briefings | `active` |
| 9 | **Jovan Aritza** | Intel Agent | Academic intelligence & monitoring (Telkom University integration) | `active` |

---

## 7. Project Directory Structure

Rancangan struktur file pada `/home/daniilham/yudiaz-sentinel`:

```
/home/daniilham/yudiaz-sentinel/
├── README.md
├── pyproject.toml                 # Toolchain dependency via uv
├── deploy/
│   ├── yudiaz-sentinel.service    # Systemd service unit descriptor
│   └── Caddyfile.snippet          # Caddy reverse proxy block
├── docs/
│   ├── ARCHITECTURE.md            # Master Architecture Blueprint (Dokumen ini)
│   └── API_CONTRACT.md            # Detailed JSON Schema Reference
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI bootstrap & ASGI application
│   ├── config.py                  # Server specs & constant environment definitions
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── system_collector.py    # psutil CPU, RAM, Disk, Uptime metrics
│   │   ├── service_collector.py   # Probing Hermes, 9Router, Caddy, Storage
│   │   └── team_collector.py      # AI Agent static & runtime catalog
│   └── routers/
│       ├── __init__.py
│       ├── api_v1.py              # REST endpoints definition
│       └── stream.py              # Server-Sent Events (SSE) generator
└── frontend/
    ├── index.html                 # Modern Responsive Dashboard (HTML5)
    ├── static/
    │   ├── css/
    │   │   └── dashboard.css      # Custom styling & neon glow accents
    │   └── js/
    │       ├── app.js             # State management & SSE consumer
    │       └── charts.js          # Chart.js initialization & real-time update logic
```

---

## 8. Complete REST API Contract Specification

Semua endpoint REST Sentinel menggunakan format respon seragam (*Standard Envelope*):
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": { ... }
}
```
Jika terjadi kegagalan sistem internal, format error terstandarisasi:
```json
{
  "success": false,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "error": {
    "code": "METRIC_COLLECTION_ERROR",
    "message": "Human-readable explanation of error context",
    "details": null
  }
}
```

---

### Endpoint 1: System Liveness & Readiness Check
- **Route**: `GET /api/v1/health`
- **Purpose**: Digunakan oleh Caddy / health checkers eksternal untuk verifikasi ketersediaan service.
- **Headers**:
  - `Accept: application/json`
- **Response `200 OK`**:
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": {
    "status": "healthy",
    "service": "yudiaz-sentinel",
    "version": "1.0.0",
    "uptime_seconds": 3600.45,
    "daemon_pid": 48212,
    "memory_rss_mb": 28.4
  }
}
```

---

### Endpoint 2: Real-time Telemetry Snapshot
- **Route**: `GET /api/v1/metrics`
- **Purpose**: Mengambil snapshot instan utilisasi vCPU, alokasi RAM, disk usage, uptime, dan system load.
- **Headers**:
  - `Accept: application/json`
- **Response `200 OK`**:
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": {
    "uptime": {
      "system_uptime_seconds": 44520,
      "system_uptime_human": "12 hours, 22 mins",
      "boot_time": "2026-09-25T02:09:40Z"
    },
    "cpu": {
      "overall_usage_percent": 3.75,
      "per_core_percent": [4.0, 3.2, 5.1, 2.7],
      "cores_count": 4,
      "load_average": {
        "load_1m": 0.08,
        "load_5m": 0.05,
        "load_15m": 0.02
      }
    },
    "memory": {
      "total_bytes": 57982058496,
      "total_gb": 54.0,
      "used_bytes": 2254857830,
      "used_gb": 2.1,
      "free_bytes": 48318382080,
      "free_gb": 45.0,
      "cached_bytes": 8375173120,
      "cached_gb": 7.8,
      "available_bytes": 55850000000,
      "available_gb": 52.0,
      "used_percent": 3.89,
      "swap": {
        "total_bytes": 8589934592,
        "total_gb": 8.0,
        "used_bytes": 0,
        "used_gb": 0.0,
        "free_bytes": 8589934592,
        "free_gb": 8.0,
        "used_percent": 0.0
      }
    },
    "disks": [
      {
        "device": "/dev/root",
        "mountpoint": "/",
        "fstype": "ext4",
        "description": "NVMe Primary Root Storage",
        "total_gb": 61.0,
        "used_gb": 8.3,
        "free_gb": 52.7,
        "used_percent": 14.0
      },
      {
        "device": "/dev/sdb1",
        "mountpoint": "/mnt",
        "fstype": "ext4",
        "description": "Azure Ephemeral Resource Storage",
        "total_gb": 110.0,
        "used_gb": 8.1,
        "free_gb": 97.0,
        "used_percent": 8.0
      }
    ]
  }
}
```

---

### Endpoint 3: Hardware Baseline & Cloud Metadata
- **Route**: `GET /api/v1/specs`
- **Purpose**: Menyediakan profil spesifikasi lengkap hardware, sistem operasi, dan cloud hosting.
- **Headers**:
  - `Accept: application/json`
- **Response `200 OK`**:
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": {
    "server": {
      "hostname": "Daniilham-PC",
      "os": "Ubuntu 24.04 LTS (Noble Numbat)",
      "kernel": "Linux 6.17.0-1022-azure x86_64",
      "architecture": "x86_64"
    },
    "cpu": {
      "model": "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz",
      "cores_physical": 4,
      "cores_logical": 4,
      "base_clock": "2.80 GHz"
    },
    "memory": {
      "total_physical_ram_gb": 54.0,
      "total_swap_gb": 8.0
    },
    "storage": {
      "root_partition": "61 GB NVMe SSD",
      "ephemeral_partition": "110 GB Azure Resource SSD"
    },
    "network": {
      "public_ip": "20.200.220.190",
      "cloud_provider": "Microsoft Azure",
      "region": "Korea Central (Seoul, South Korea)",
      "primary_subdomain": "vps.daniandraaa.my.id",
      "fallback_subdomain": "vps.20.200.220.190.sslip.io"
    }
  }
}
```

---

### Endpoint 4: Attached Projects & Services Status
- **Route**: `GET /api/v1/projects`
- **Purpose**: Mengecek ketersediaan port, proses, dan status hidup dari ekosistem project yang berjalan di VPS.
- **Headers**:
  - `Accept: application/json`
- **Response `200 OK`**:
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": {
    "services": [
      {
        "id": "hermes-agent",
        "name": "Hermes Agent Platform",
        "category": "AI Orchestration Core",
        "port": 9119,
        "status": "online",
        "status_code": 200,
        "runtime_type": "System Daemon",
        "details": "Multi-profile AI agent execution runtime",
        "last_checked": "2026-09-25T14:32:00Z"
      },
      {
        "id": "9router",
        "name": "9Router AI Gateway",
        "category": "LLM Inference Proxy",
        "port": 20128,
        "status": "online",
        "status_code": 200,
        "runtime_type": "Docker (local/9router:0.5.81-npm)",
        "details": "Unified LLM routing & API key virtualization",
        "last_checked": "2026-09-25T14:32:00Z"
      },
      {
        "id": "caddy",
        "name": "Caddy Reverse Proxy",
        "category": "Edge Ingress & TLS",
        "port": 443,
        "status": "online",
        "status_code": 200,
        "runtime_type": "Systemd Service (caddy.service)",
        "details": "Automated TLS termination & HTTP/2 routing",
        "last_checked": "2026-09-25T14:32:00Z"
      },
      {
        "id": "yudiaz-sentinel",
        "name": "Yudiaz Sentinel",
        "category": "Infrastructure Observability",
        "port": 9229,
        "status": "online",
        "status_code": 200,
        "runtime_type": "Systemd Service (yudiaz-sentinel.service)",
        "details": "Live zero-overhead telemetry daemon",
        "last_checked": "2026-09-25T14:32:00Z"
      },
      {
        "id": "yudiaz-assets",
        "name": "Yudiaz Creative Studio Core Assets",
        "category": "Studio Repositories & Storage",
        "port": null,
        "status": "healthy",
        "status_code": null,
        "runtime_type": "Local Filesystem Storage",
        "details": "/home/daniilham local workspace repository",
        "last_checked": "2026-09-25T14:32:00Z"
      }
    ]
  }
}
```

---

### Endpoint 5: Yudiaz AI Agent Team Roster
- **Route**: `GET /api/v1/team`
- **Purpose**: Memberikan direktori lengkap 9 AI Agent Yudiaz beserta role struktural dan status operasionalnya.
- **Headers**:
  - `Accept: application/json`
- **Response `200 OK`**:
```json
{
  "success": true,
  "timestamp": "2026-09-25T14:32:00.123Z",
  "data": {
    "organization": "Yudiaz Creative Studio",
    "total_agents": 9,
    "agents": [
      {
        "id": "raziel-hendrix",
        "name": "Raziel Hendrix",
        "role": "CTO & Orchestrator",
        "status": "active",
        "avatar_badge": "CTO",
        "specialization": "Multi-agent orchestration, engineering strategy, system governance"
      },
      {
        "id": "kael-ashford",
        "name": "Kael Ashford",
        "role": "Lead Architect",
        "status": "active",
        "avatar_badge": "ARCH",
        "specialization": "System design, clean architecture, API contracts, deployment blueprints"
      },
      {
        "id": "nara-vasquez",
        "name": "Nara Vasquez",
        "role": "Lead Researcher",
        "status": "active",
        "avatar_badge": "RSCH",
        "specialization": "Emerging AI models, compute efficiency research, technical analysis"
      },
      {
        "id": "senna-louviere",
        "name": "Senna Louviere",
        "role": "Creative Director",
        "status": "active",
        "avatar_badge": "DSGN",
        "specialization": "Visual aesthetic, brand cohesion, UI/UX interaction standards"
      },
      {
        "id": "idris-nakamura",
        "name": "Idris Nakamura",
        "role": "Senior Developer",
        "status": "active",
        "avatar_badge": "DEV",
        "specialization": "FastAPI backend, high-performance async daemons, socket programming"
      },
      {
        "id": "mika-stellan",
        "name": "Mika Stellan",
        "role": "Frontend Engineer",
        "status": "active",
        "avatar_badge": "FRONT",
        "specialization": "Responsive dashboards, Chart.js sparklines, real-time SSE UX"
      },
      {
        "id": "viktor-moreau",
        "name": "Viktor Moreau",
        "role": "Lead QA",
        "status": "active",
        "avatar_badge": "QA",
        "specialization": "Automated verification, load testing, security audits, resilience"
      },
      {
        "id": "elara-sinclair",
        "name": "Elara Sinclair",
        "role": "PA to CEO",
        "status": "active",
        "avatar_badge": "PA",
        "specialization": "Executive coordination, timeline management, daily deliverables"
      },
      {
        "id": "jovan-aritza",
        "name": "Jovan Aritza",
        "role": "Intel Agent",
        "status": "active",
        "avatar_badge": "INTEL",
        "specialization": "Telkom University intelligence, academic network monitoring"
      }
    ]
  }
}
```

---

### Endpoint 6: Live Server-Sent Events (SSE) Stream
- **Route**: `GET /api/v1/metrics/stream`
- **Purpose**: Real-time push telemetry setiap 2 detik langsung ke browser via koneksi persisten HTTP/2.
- **Headers**:
  - `Accept: text/event-stream`
- **Response Headers**:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- **Wire Format (Data Stream)**:
```
event: metric_tick
data: {"timestamp":"2026-09-25T14:32:02Z","cpu_percent":4.1,"per_core":[4.0,3.5,5.2,3.7],"load_1m":0.08,"ram_used_gb":2.1,"ram_free_gb":45.0,"ram_percent":3.89,"disk_root_percent":14.0,"disk_mnt_percent":8.0}

: ping - 14:32:04Z

event: metric_tick
data: {"timestamp":"2026-09-25T14:32:04Z","cpu_percent":3.8,"per_core":[3.8,3.2,4.8,3.4],"load_1m":0.07,"ram_used_gb":2.1,"ram_free_gb":45.0,"ram_percent":3.89,"disk_root_percent":14.0,"disk_mnt_percent":8.0}
```

---

## 9. Ingress & Edge Proxy Specification (Caddy)

Caddy dikonfigurasi untuk melayani domain primer `vps.daniandraaa.my.id` dan fallback testing `vps.20.200.220.190.sslip.io` menuju internal daemon `127.0.0.1:9229`.

### File Blueprint: `/etc/caddy/Caddyfile` (atau import snippet)
```caddy
# ==============================================================================
# YUDIAZ SENTINEL INGRESS CONFIGURATION
# Primary Target: vps.daniandraaa.my.id
# Fallback Testing Target: vps.20.200.220.190.sslip.io
# Internal Daemon: 127.0.0.1:9229
# ==============================================================================

vps.daniandraaa.my.id, vps.20.200.220.190.sslip.io {
    # Logging configuration
    log {
        output file /var/log/caddy/sentinel_access.log {
            roll_size 10mb
            roll_keep 5
        }
    }

    # Security Headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        # Disable server banner
        -Server
    }

    # Compression for static REST JSON & HTML assets
    encode zstd gzip

    # Reverse proxy upstream to Sentinel Python Daemon
    reverse_proxy 127.0.0.1:9229 {
        # Critical for SSE (Server-Sent Events) live streaming
        flush_interval -1

        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        # Keepalive upstream settings
        transport http {
            keepalive 60s
            keepalive_idle_conns 10
        }
    }
}
```

---

## 10. Systemd Service Unit Specification

Daemon dijalankan tanpa privileges `root` di bawah user `daniilham` untuk memenuhi standar zero-trust security.

### File Blueprint: `/etc/systemd/system/yudiaz-sentinel.service`
```ini
[Unit]
Description=Yudiaz Sentinel VPS Telemetry & Observability Engine
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=daniilham
Group=daniilham
WorkingDirectory=/home/daniilham/yudiaz-sentinel

# Menggunakan isolasi Python 3.12 / uv environment
Environment="PYTHONUNBUFFERED=1"
Environment="SENTINEL_HOST=127.0.0.1"
Environment="SENTINEL_PORT=9229"
Environment="SENTINEL_ENV=production"

# Eksekusi via uvicorn
ExecStart=/home/daniilham/yudiaz-sentinel/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 9229 --workers 1 --log-level info

# Resilience & Auto-recovery
Restart=always
RestartSec=5s

# Security sandboxing
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/home/daniilham/yudiaz-sentinel

# Resource limits (Prevent memory leaks from exhausting the 54GB RAM)
MemoryHigh=150M
MemoryMax=300M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

---

## 11. Engineering Directives

### 11.1. Technical Guide untuk Idris Nakamura (Backend Engineer)
1. **Toolchain Setup**:
   - Gunakan `uv` untuk membuat virtual environment Python 3.12:
     ```bash
     cd /home/daniilham/yudiaz-sentinel
     uv venv .venv --python /usr/bin/python3.12
     uv pip install fastapi uvicorn[standard] psutil pydantic
     ```
   - Hindari dependensi C-extension berat lainnya. `psutil` sudah cukup untuk 99% kebutuhan metrics kernel Linux.
2. **Non-Blocking Telemetry Collection**:
   - Jangan pernah memanggil fungsi blocking I/O secara sinkron di router async.
   - Panggilan `psutil.cpu_percent(interval=1)` bersifat blocking. Solusi arsitektural: Buat background asyncio loop worker yang mengupdate atomic in-memory cache setiap 1 detik, sehingga request endpoint `GET /api/v1/metrics` langsung membaca cache dalam < 1 milidetik tanpa `await asyncio.sleep(1)`.
3. **Service Probing Strategy**:
   - Probing port 9119 (Hermes) dan port 20128 (9Router) dilakukan dengan socket connect timeout non-blocking (0.2 detik). Jika timeout tercapai, catat status `offline` tanpa melempar 500 error ke caller.
4. **SSE Implementation**:
   - Manfaatkan `fastapi.responses.StreamingResponse` dengan async generator yang memancarkan `yield f"event: metric_tick\ndata: {json_payload}\n\n"` setiap 2 detik.
   - Sertakan ping comment (`: ping\n\n`) untuk menjaga firewall stateful connection tetap hidup.

---

### 11.2. Technical Guide untuk Mika Stellan (Frontend Engineer)
1. **Design System & Theme**:
   - Gunakan konsep **Yudiaz Cyber-Minimalist Dark Luxury**:
     - Background: Deep Obsidian `#0a0b0e` / Slate `#0f172a`
     - Card Background: `#161b26` dengan border tipis `rgba(255, 255, 255, 0.08)`
     - Accent Primary: Electric Cyan `#00f2fe` / Emerald Green `#10b981` (Online indicators)
     - Warning / Alert: Amber `#f59e0b` / Ruby `#ef4444`
   - Typography: Clean sans-serif (`Inter` atau `JetBrains Mono` untuk angka/metrics).
2. **Layout Blueprint**:
   - **Header**: Logo Yudiaz Sentinel, Hostname `Daniilham-PC`, Public IP `20.200.220.190`, Cloud Region `Azure Seoul`, Live Uptime Counter.
   - **Row 1 (Core KPI Cards)**:
     - vCPU Utilization (Overall % + mini sparkline history 30 detik)
     - Memory RAM (Gauge used vs available: 2.1 GB / 54 GB + Swap 0 GB / 8 GB)
     - NVMe Root Storage (Bar progress: 8.3 GB / 61 GB)
     - Ephemeral /mnt Storage (Bar progress: 8.1 GB / 110 GB)
   - **Row 2 (vCPU Multi-Core Grid)**:
     - 4 Core Cards individual bar indicator (Core 0, Core 1, Core 2, Core 3).
     - Load Average display: `1m`, `5m`, `15m`.
   - **Row 3 (Projects & Services Health)**:
     - Grid status card: Hermes Agent (Port 9119), 9Router AI Gateway (Port 20128), Caddy (Port 443), Yudiaz Sentinel (Port 9229).
     - Pulsing dot badge hijau jika status online.
   - **Row 4 (Yudiaz AI Agent Cluster Roster)**:
     - 9 profile cards dengan status badge `ACTIVE`, role badge, dan avatar initials.
3. **Data Ingestion via SSE**:
   - Implementasikan listener native:
     ```javascript
     const eventSource = new EventSource('/api/v1/metrics/stream');
     eventSource.addEventListener('metric_tick', (e) => {
         const data = JSON.parse(e.data);
         updateChartsAndGauges(data);
     });
     eventSource.onerror = (err) => {
         console.warn('SSE reconnecting in 3s...', err);
     };
     ```
   - Lakukan graceful fallback ke polling `GET /api/v1/metrics` jika browser lama tidak mendukung SSE atau koneksi proxy terputus.

---

### 11.3. Acceptance Criteria & QA Gate untuk Viktor Moreau (Lead QA)
1. **Resource Benchmark**:
   - Memory footprint daemon Sentinel idle < 50 MB RSS.
   - CPU utilization < 0.5% pada 1 core saat melayani 3 dashboard SSE aktif bersamaan.
2. **Latency & Response Time**:
   - Endpoint `/api/v1/health` dan `/api/v1/metrics` harus merespon < 15ms.
   - SSE interval harus stabil pada `2000ms ± 100ms`.
3. **Resilience & Fault Isolation**:
   - Jika service Hermes (9119) atau 9Router (20128) di-restart atau mati, Sentinel TIDAK boleh crash atau mengembalikan 500 status. Status service terkait harus langsung berubah menjadi `offline`.
4. **Caddy Ingress Validation**:
   - Akses via `vps.daniandraaa.my.id` dan `vps.20.200.220.190.sslip.io` harus sukses mengembalikan HTTPS dengan TLS handshake valid tanpa buffering lag pada stream SSE.

---

## 12. Architectural Sign-Off

Dokumen spesifikasi ini adalah cetak biru resmi (*authoritative design*) untuk implementasi Yudiaz Sentinel. Idris Nakamura dan Mika Stellan dipersilakan memulai implementasi sesuai boundary yang telah didefinisikan.

*Signed,*  
**Kael Ashford**  
Lead Architect — Yudiaz Creative Studio
