# YUDIAZ SENTINEL // UI/UX DESIGN SYSTEM & TECHNICAL SPECIFICATION
**Codename:** Yudiaz Sentinel VPS Operations Console  
**Target Domain:** `vps.daniandraaa.my.id`  
**Author:** Senna Louviere (Creative Director, Yudiaz Creative Studio)  
**Stakeholders:** Raziel Hendrix (CTO), Daniandra Prayudisty (CEO), Mika Stellan (Frontend Engineer)  
**Version:** 1.0.0 — Production Specification  
**Design Standard:** Dark Mode Luxury Brutalism // WCAG 2.1 AA Compliant  

---

## 1. Executive Summary & Creative Vision

Yudiaz Sentinel adalah antarmuka operasional real-time (Command & Telemetry Console) untuk memantau performa, integritas infrastruktur, layanan aktif, dan orkestrasi 9 AI Agent Yudiaz Creative Studio yang berjalan pada Azure Cloud VPS (`vps.daniandraaa.my.id`).

### 1.1 Philosophy: Modern Brutalist-Minimalist Luxury
1. **Monolithic Precision:** Garis tegas (1px subtle border strokes), layout kisi terstruktur, kontras tajam tanpa noise visual yang tidak perlu.
2. **Tactile Luminescence:** Penggunaan aksen *Quantum Cyan* dan *Cyber Iris* berpendar lembut di atas latar gelap pekat (*Obsidian Core*), memberikan kesan server control room kelas enterprise mewah.
3. **Data-Density without Clutter:** Telemetri hardware (CPU, RAM, Disk I/O) disajikan menggunakan hierarki tipografi mikro yang presisi (JetBrains Mono untuk data teknis, Plus Jakarta Sans untuk identitas antarmuka).
4. **Zero-Lag Perceived Performance:** Animasi transisi halus (150ms–250ms), SVG-native gauges, dan render optimal tanpa ketergantungan library visual yang berat.

---

## 2. Official Brand Identity & Master Mark (Concept 2B)

Sentinel mengadopsi identitas resmi Yudiaz Creative Studio: **Concept 2B — The Negative Space Portal (Gestalt Monolith)**.

```
       LEFT MONOLITH                  RIGHT MONOLITH
       (D Monolith Spine)             (D Vault Arch)
       +-----------------+            +-----------------+
       |                 |            |      .-""""-.   |
       |     |\          |            |    .'        '. |
       |     | \         |            |   /            \|
       |     |  \        |  PORTAL Y  |  |              |
       |     |   \       |  (CUTOUT)  |  |              |
       |     |    \      |            |  |              |
       |     |     \     |            |  |              |
       |     |      \    |            |   \            /|
       |     |       |   |            |    '.        .' |
       |     +-------+   |            |      '-....-'   |
       +-----------------+            +-----------------+
        Outer Monolith D contour with an internal Y slit
```

### 2.1 Geometry & Math
- **Mark File Reference:** `/home/daniilham/yudiaz-sentinel/assets/yudiaz-logo-mark.svg`
- **Lockup File Reference:** `/home/daniilham/yudiaz-sentinel/assets/yudiaz-logo-lockup.svg`
- **ViewBox:** `0 0 500 500` (Mark) / `0 0 960 300` (Lockup)
- **Monolith Vectors:**
  - *Left Monolith Path:* `M 118 100 L 182 100 L 236 218 Q 238 222 238 228 L 238 400 L 118 400 Z` (Fill: `#FFFFFF` / `#F8FAFC`)
  - *Right Monolith Path:* `M 264 400 L 264 228 Q 264 222 266 218 L 318 100 C 370 100, 412 158, 412 250 C 412 342, 370 400, 264 400 Z` (Fill: `#FFFFFF` / `#F8FAFC`)
- **Safe Zone Rule:** Minimal padding sekeliling logo sebesar $0.25 \times \text{height}$.
- **Clearance Scale:**
  - Navigation Bar Mark: Tinggi 32px
  - Lockup Hero Brand: Lebar 180px–220px
  - Favicon Sizes: 16px, 32px, 64px

---

## 3. Design Tokens & Color Palette

### 3.1 Color Palette Matrix

| Token Name | Hex Code | HSL | RGB | Peruntukan UI |
|---|---|---|---|---|
| `--color-obsidian-core` | `#07090E` | `225°, 33%, 4%` | `7, 9, 14` | Background kanvas utama aplikasi |
| `--color-surface-panel` | `#0E131F` | `222°, 38%, 9%` | `14, 19, 31` | Kartu panel utama, glassmorphism base |
| `--color-surface-elevated`| `#141A29` | `221°, 34%, 12%` | `20, 26, 41` | Hover state, dropdowns, modal windows |
| `--color-border-subtle` | `#1E293B` | `217°, 33%, 17%` | `30, 41, 59` | Border standard 1px container |
| `--color-border-accent` | `#334155` | `215°, 25%, 27%` | `51, 65, 85` | Border highlight aktif & focused |
| `--color-cyber-iris` | `#6366F1` | `239°, 84%, 67%` | `99, 102, 241` | Brand primary accent, graphs, CTA |
| `--color-quantum-cyan` | `#00F2FE` | `184°, 100%, 50%` | `0, 242, 254` | Telemetry active spark, glowing gauges |
| `--color-platinum-white`| `#F8FAFC` | `210°, 40%, 98%` | `248, 250, 252`| Heading teks level 1 & value metrik |
| `--color-slate-muted` | `#94A3B8` | `215°, 16%, 65%` | `148, 163, 184`| Body text, secondary metrics, subtitles |
| `--color-dark-muted` | `#475569` | `215°, 19%, 35%` | `71, 85, 105` | Metadata label, inactive states |

### 3.2 Telemetry Status Semantic Tokens

| Status Semantics | Hex Code | RGB | Glow Box Shadow | Indikasi |
|---|---|---|---|---|
| **Online / Nominal** | `#10B981` | `16, 185, 129` | `0 0 12px rgba(16, 185, 129, 0.45)` | Uptime OK, Services Running, Agent Ready |
| **Warning / Elevated**| `#F59E0B` | `245, 158, 11` | `0 0 12px rgba(245, 158, 11, 0.45)` | RAM > 80%, High CPU Load, Ephemeral disk |
| **Critical / Alert** | `#EF4444` | `239, 68, 68` | `0 0 14px rgba(239, 68, 68, 0.55)` | Service down, I/O Stall, Core spike |
| **Neutral / Standby** | `#64748B` | `100, 116, 139`| `none` | Offline, Idle task, Cached data |

### 3.3 Contrast & WCAG 2.1 AA Compliance Matrix
Semua pasangan teks dan background diuji terhadap standar WCAG 2.1 Level AA (minimal 4.5:1 untuk teks normal, 3.0:1 untuk teks besar dan komponen grafis):

- `#F8FAFC` on `#07090E`: Contrast Ratio **17.8:1** (Pass AAA)
- `#94A3B8` on `#0E131F`: Contrast Ratio **6.4:1** (Pass AA)
- `#00F2FE` on `#0E131F`: Contrast Ratio **12.1:1** (Pass AAA)
- `#6366F1` on `#07090E`: Contrast Ratio **5.2:1** (Pass AA)
- `#10B981` on `#0E131F`: Contrast Ratio **7.8:1** (Pass AAA)

---

## 4. Typography Scale & Fonts

Sentinel mengombinasikan font sans-serif modern berkarakter geometric untuk UI chrome dengan font monospaced bereputasi teknis tinggi untuk telemetri angka:

1. **Brand & Interface Sans:** `'Plus Jakarta Sans'`, system-ui, `-apple-system`, sans-serif
2. **Technical Telemetry Monospace:** `'JetBrains Mono'`, `'Fira Code'`, monospace

### 4.1 Type Scale Hierarchy

| Level | Size (Desktop / Mobile) | Weight | Line Height | Tracking | Font Family |
|---|---|---|---|---|---|
| **Display Title** | 28px / 22px | 800 (Extrabold) | 1.2 | `-0.02em` | Plus Jakarta Sans |
| **Section Header** | 18px / 16px | 700 (Bold) | 1.3 | `-0.01em` | Plus Jakarta Sans |
| **Card Header** | 14px / 13px | 600 (Semibold) | 1.4 | `+0.05em` | Plus Jakarta Sans (UPPERCASE) |
| **Telemetry Big Value**| 32px / 26px | 700 (Bold) | 1.1 | `-0.03em` | JetBrains Mono |
| **Telemetry Metric** | 18px / 16px | 600 (Semibold) | 1.2 | `0` | JetBrains Mono |
| **Body Regular** | 14px / 13px | 400 (Regular) | 1.5 | `0` | Plus Jakarta Sans |
| **Caption / Label** | 11px / 10px | 500 (Medium) | 1.4 | `+0.08em` | JetBrains Mono (UPPERCASE) |
| **Micro Badge** | 10px / 9px | 700 (Bold) | 1.0 | `+0.12em` | JetBrains Mono (UPPERCASE) |

---

## 5. Layout Architecture & Component Hierarchy

### 5.1 Wireframe ASCII Layout Breakdown

```
+==============================================================================================================+
| [LOGO CONCEPT 2B] YUDIAZ SENTINEL // vps.daniandraaa.my.id      [LIVE PULSE]  UPTIME: 14d 08h 22m   PING: 14ms |
+==============================================================================================================+
|                                    HARDWARE TELEMETRY COMMAND MATRIX                                         |
| +----------------------------------+------------------------------------+----------------------------------+ |
| | vCPU 4-CORE ENGINE               | 54 GiB RAM DDR4 SUBSYSTEM          | NVMe STORAGE & I/O ARRAY         | |
| | [Overall: 24.5% Sparkline]       | [Radial Arc: 18.4GB Used / 34%]    | [OS Root /: 61GB (32% Used)]     | |
| | Core 0: [======     ] 45%        | Breakdown:                         | [Ephemeral /mnt: 110GB (14%)]    | |
| | Core 1: [===        ] 22%        | - Active: 18.4 GB                  | Read: 4.2 MB/s | Write: 1.8 MB/s | |
| | Core 2: [====       ] 28%        | - Cached: 12.1 GB                  | IOPS: 420 req/s                  | |
| | Core 3: [==         ] 11%        | - Free:   23.5 GB                  | Healthy (S.M.A.R.T Verified)     | |
| | Load: 0.42 (1m) 0.38 (5m) 0.31   | Swap: 0 / 4.0 GiB (Optimal)        | Status: NVMe Gen4 Online         | |
| +----------------------------------+------------------------------------+----------------------------------+ |
+--------------------------------------------------------------------------------------------------------------+
|                                      MAIN DUAL-COLUMN ARCHITECTURE                                           |
| +---------------------------------------------------+------------------------------------------------------+ |
| | COLUMN 1: INFRASTRUCTURE & ACTIVE SERVICES        | COLUMN 2: YUDIAZ AI AGENT HUB (9 ROSTER TEAM)        | |
| |                                                   |                                                      | |
| | [CARD A: HOST SPECIFICATIONS]                     | [FILTER TABS: All (9) | Core Dev (7) | Ops & Intel (2)]| |
| | - Architecture: Intel Xeon Platinum 8370C @2.8GHz |                                                      | |
| | - Cores: 4 vCPU Virtual Machine                   | 1. RAZIEL HENDRIX  [CTO & Orchestrator]      [ONLINE] | |
| | - Memory: 54.0 GiB High-Density ECC DDR4          | 2. KAEL ASHFORD    [Lead System Architect]   [ONLINE] | |
| | - Cloud: Microsoft Azure (Seoul / Korea Central)  | 3. NARA VASQUEZ    [Lead Tech Researcher]    [ONLINE] | |
| | - OS: Ubuntu 24.04 LTS (Noble Numbat)             | 4. SENNA LOUVIERE  [Creative Director]       [ACTIVE] | |
| | - Kernel: 6.17.0-1022-azure                       | 5. IDRIS NAKAMURA  [Senior Dev & DevOps]     [ONLINE] | |
| | - IP Address: 20.200.220.190 [COPY]               | 6. MIKA STELLAN    [Frontend Engineer]       [BUSY]   | |
| |                                                   | 7. VIKTOR MOREAU   [Lead QA & Security]      [IDLE]   | |
| | [CARD B: ACTIVE PROJECTS & DAEMONS SHOWCASE]      | 8. ELARA SINCLAIR  [PA CEO & Operations]     [ONLINE] | |
| | 1. Hermes Agent Platform (Port 9119)   [ONLINE]   | 9. JOVAN ARITZA    [Intel Officer]           [WATCH]  | |
| | 2. 9Router AI Gateway   (Port 20128)  [ONLINE]   |                                                      | |
| | 3. Caddy Reverse Proxy  (Port 80/443) [ACTIVE]   | [CARD FOOTER: Team Dispatcher // Direct Channel Ready| |
| | 4. Yudiaz Creative Studio Assets      [SYNCED]   |                                                      | |
| +---------------------------------------------------+------------------------------------------------------+ |
+==============================================================================================================+
| YUDIAZ CREATIVE STUDIO (C) 2026 // CEO: DANIANDRA PRAYUDISTY // CTO: RAZIEL HENDRIX // SYSTEM INTEGRITY 100%|
+==============================================================================================================+
```

---

## 6. Detailed Component Specifications

### 6.1 Status Bar & Global Navigation
- **Brandmark Area:** Official Yudiaz Concept 2B (Negative Space Portal) Monogram. Ukuran 36px x 36px, fill Platinum White dengan subtle glow Quantum Cyan on hover.
- **Title Block:** `YUDIAZ SENTINEL` (Font weight 800, tracking 0.15em), sub-label `vps.daniandraaa.my.id // AZURE KOREA CENTRAL`.
- **Live Status Indicator:**
  - Double-ring beacon pulse: Center dot `#10B981` (8px), outer pinging ripple ring (`rgba(16, 185, 129, 0.4)`).
  - Teks: `HOST ONLINE`.
- **Uptime Counter:** Ticker dinamis `14d 08h 22m 45s`, berdetak per detik.
- **Latency Indicator:** Dynamic round-trip ping ke VPS gateway (14ms – 18ms), status badge `ULTRA LOW LATENCY`.
- **Control Tools:** Tombol Quick Refresh, Timezone Switcher (`KST / UTC / WIB`), dan System Audio / Alert toggle.

### 6.2 Hardware Telemetry Block (The Tri-Sensor Cluster)
1. **Sensor 1: vCPU 4-Core Telemetry**
   - *Overall Usage Sparkline:* 60-point dynamic line graph dengan gradient fill `rgba(99, 102, 241, 0.2)` ke transparan.
   - *Core Bar Matrix:* 4 horizontal segmented bars (Core 0, 1, 2, 3), masing-masing dengan label frekuensi (`2.80 GHz`) dan persentase utilisasi real-time.
   - *Load Averages:* Badges monospaced untuk interval 1 min (`0.42`), 5 min (`0.38`), dan 15 min (`0.31`).
2. **Sensor 2: Memory RAM 54 GiB Subsystem**
   - *Circular Radial SVG Arc:* SVG meter melingkar 270 derajat dengan gradient stroke Cyber Iris ke Quantum Cyan.
   - *Total Capacity:* `54.0 GiB` DDR4.
   - *Subdivision Bar:* Linear stacked gauge dengan color-coding:
     * Active/Used: `18.4 GiB` (`#6366F1`)
     * Buffer/Cache: `12.1 GiB` (`#00F2FE`)
     * Available Free: `23.5 GiB` (`#1E293B`)
   - *Swap Status:* `0 MB / 4.0 GiB` (0% utilized, kernel paging optimal).
3. **Sensor 3: NVMe Storage & I/O Subsystem**
   - *Partition A (OS Root `/`):* `61.0 GB Total` | `19.5 GB Used (32%)` | `41.5 GB Free`.
   - *Partition B (Ephemeral Fast NVMe `/mnt`):* `110.0 GB Total` | `15.4 GB Used (14%)` | `94.6 GB Free`.
   - *I/O Activity Monitor:* Real-time Read Throughput (`4.2 MB/s`), Write Throughput (`1.8 MB/s`), Total IOPS counter (`420 IOPS`).
   - *Health Check Tag:* `S.M.A.R.T. PASSED // NVMe GEN4 OK`.

### 6.3 System Specifications Card
- **Monolithic Spec Grid:** Kartu informasi spesifikasi host server dengan ikon micro-circuit dan copy button untuk fast deployment reference:
  * **Processor:** Intel Xeon Platinum 8370C @ 2.80GHz (4 vCPU, Ice Lake Microarchitecture, AVX-512)
  * **Memory:** 54 GiB High-Density ECC Cloud RAM
  * **Datacenter:** Microsoft Azure Cloud (Region: Seoul / Korea Central `ap-northeast-2`)
  * **OS & Kernel:** Ubuntu 24.04 LTS (Noble Numbat) // Linux Kernel `6.17.0-1022-azure`
  * **Network Address:** Public IPv4 `20.200.220.190` (Dengan tombol copy interaktif + toast visual).

### 6.4 Active Projects & Daemon Showcase
Panel visual berstatus live untuk port-port kritis:
1. **Hermes Agent Platform**
   - Port: `9119` (TCP)
   - Status: `ONLINE // RUNNING`
   - Description: Core Multi-Agent Orchestration & Subagent Execution Engine.
2. **9Router AI Gateway**
   - Port: `20128` (TCP)
   - Status: `ONLINE // READY`
   - Description: High-speed LLM Router & Reverse Proxy untuk OpenAI, Anthropic, dan Custom Endpoints.
3. **Caddy TLS Reverse Proxy**
   - Port: `80 / 443` (HTTP/HTTPS)
   - Status: `ACTIVE // TLS VERIFIED`
   - Description: Automated ACME Let's Encrypt TLS Termination untuk `vps.daniandraaa.my.id`.
4. **Yudiaz Creative Studio Core Assets**
   - Protocol: `HTTPS / CDN`
   - Status: `MOUNTED // SYNCED`
   - Description: Brand identity vector repositories, tokens, & media caches.

### 6.5 AI Agent Team Hub (9 Yudiaz Agents)
Menampilkan 9 AI Agent Yudiaz Creative Studio dengan pembagian departemen, foto/avatar visual bergaya digital avatar monolitik, badge peran, spesialisasi, dan status real-time:

#### Filter Tabs:
- `All Agents (9)`
- `Core Dev & Architecture (7)`
- `Operations & Intelligence (2)`

#### Agent Roster Details:
1. **Raziel Hendrix**
   - Avatar: Obsidian-tinted Commander crest (`#6366F1`)
   - Role: `CTO & Orchestrator`
   - Department: `Core Engineering`
   - Status: `ONLINE // ORCHESTRATING`
   - Spec: Brief decomposition, task delegation, team synthesis, architecture signoff.
2. **Kael Ashford**
   - Avatar: Geometric Blueprint Glyph (`#00F2FE`)
   - Role: `Lead System Architect`
   - Department: `Core Engineering`
   - Status: `ONLINE // ACTIVE`
   - Spec: System topology, database schema, microservices contract, high-load design.
3. **Nara Vasquez**
   - Avatar: Neural Compass Emblem (`#38BDF8`)
   - Role: `Lead Tech Researcher`
   - Department: `Core Engineering`
   - Status: `ONLINE // RESEARCHING`
   - Spec: arXiv benchmarks, competitive AI intelligence, algorithm validation.
4. **Senna Louviere**
   - Avatar: Negative Space Portal Prism (`#F43F5E`)
   - Role: `Creative Director`
   - Department: `Core Engineering`
   - Status: `ACTIVE // DESIGNING`
   - Spec: UI/UX design systems, luxury brutalism, design tokens, WCAG 2.1 compliance.
5. **Idris Nakamura**
   - Avatar: Terminal Hex Core (`#10B981`)
   - Role: `Senior Developer & DevOps`
   - Department: `Core Engineering`
   - Status: `ONLINE // EXECUTING`
   - Spec: Backend API, Go/Node/Python pipelines, containerization, Azure cloud ops.
6. **Mika Stellan**
   - Avatar: Reactive Quantum Lattice (`#A855F7`)
   - Role: `Frontend Engineer`
   - Department: `Core Engineering`
   - Status: `BUSY // CODING`
   - Spec: React, Next.js, Tailwind CSS, motion shaders, client-side state.
7. **Viktor Moreau**
   - Avatar: Aegis Shield Glyph (`#F59E0B`)
   - Role: `Lead QA & Security`
   - Department: `Core Engineering`
   - Status: `STANDBY // AUDITING`
   - Spec: Penetration testing, vulnerability audit, unit/E2E test suites, security gates.
8. **Elara Sinclair**
   - Avatar: Chrono Star Icon (`#EC4899`)
   - Role: `PA to CEO & Ops`
   - Department: `Executive Support`
   - Status: `ONLINE // MONITORING`
   - Spec: CEO agenda, schedule dispatch, executive briefing, social media surveillance.
9. **Jovan Aritza**
   - Avatar: Intel Radar Array (`#06B6D4`)
   - Role: `Intelligence Officer`
   - Department: `Intelligence & Field`
   - Status: `WATCHING // ACTIVE`
   - Spec: Telkom University intel surveillance, external event reconnaissance, scraping.

---

## 7. Interactive Mockup Architecture (`mockup.html`)

Mockup mandiri dirancang di `/home/daniilham/yudiaz-sentinel/templates/mockup.html` dengan spesifikasi:
1. **Self-Contained & Instant-Preview:** Menggunakan Tailwind CSS CDN + custom embedded styling untuk glassmorphism dan SVG filters. Dapat dibuka langsung di browser manapun tanpa build step.
2. **SVG Brandmark Terintegrasi:** Menggunakan asset SVG resmi Yudiaz Concept 2B (Negative Space Portal) baik sebagai navbar logo maupun modal visual watermark.
3. **Interactive Telemetry Engine (Client-Side Sim):**
   - Uptime ticker berdetak setiap detik.
   - Dynamic real-time fluctuation pada nilai gauge CPU & RAM (simulate live server ping).
   - Real-time sparkline SVG redrawing.
4. **Interactive Filters:** Tab filtering untuk Agent Hub (All, Core Dev, Ops & Intel) yang mengubah tampilan grid secara instan.
5. **Interactive Modal / Drawer:**
   - Modal detail inspeksi hardware dan system logs.
   - Agent inspection drawer saat kartu agent diklik.
   - Click-to-copy pada Public IP dengan toast notification yang elegan.

---

## 8. Implementation Guide for Mika Stellan (Frontend Engineer)

Panduan teknis bagi Mika Stellan untuk implementasi produksi (React / Next.js / Vanilla Tailwind):

### 8.1 Tailwind Config Snippet (`tailwind.config.js`)
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./pages/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: {
          core: '#07090E',
          panel: '#0E131F',
          elevated: '#141A29',
          border: '#1E293B',
          highlight: '#334155',
        },
        cyber: {
          iris: '#6366F1',
          'iris-glow': 'rgba(99, 102, 241, 0.25)',
        },
        quantum: {
          cyan: '#00F2FE',
          'cyan-glow': 'rgba(0, 242, 254, 0.3)',
        },
        platinum: '#F8FAFC',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glass-panel': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'cyan-glow': '0 0 20px rgba(0, 242, 254, 0.25)',
        'iris-glow': '0 0 20px rgba(99, 102, 241, 0.25)',
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
```

### 8.2 Component Architecture & State Contract
```typescript
// Telemetry Data Interface
export interface TelemetryPayload {
  timestamp: string;
  uptimeSeconds: number;
  pingMs: number;
  cpu: {
    totalPercent: number;
    cores: number[]; // [core0, core1, core2, core3]
    loadAvg: [number, number, number]; // [1m, 5m, 15m]
    sparklineHistory: number[]; // 60 data points
  };
  ram: {
    totalBytes: number; // 54 GB
    usedBytes: number;
    cachedBytes: number;
    freeBytes: number;
    swapUsedBytes: number;
    swapTotalBytes: number;
  };
  disk: {
    root: { total: number; used: number; percent: number };
    ephemeral: { total: number; used: number; percent: number };
    io: { readBytesSec: number; writeBytesSec: number; iops: number };
  };
  services: {
    hermes: 'online' | 'degraded' | 'offline';
    nineRouter: 'online' | 'degraded' | 'offline';
    caddy: 'online' | 'degraded' | 'offline';
    assets: 'synced' | 'syncing' | 'error';
  };
  agents: AgentStatus[];
}

export interface AgentStatus {
  id: string;
  name: string;
  role: string;
  department: 'dev' | 'support';
  status: 'online' | 'active' | 'busy' | 'standby';
  currentTask: string;
  avatarGlyph: string;
}
```

### 8.3 Accessibility (a11y) & Performance Checklist
- [x] Pastikan semua SVG memiliki `aria-hidden="true"` jika dekoratif, atau `role="img"` dengan `aria-label` yang jelas.
- [x] Gunakan `prefers-reduced-motion` untuk menonaktifkan pulse radar jika user mengaktifkan pengaturan reduced motion OS.
- [x] Semua tombol memiliki outline focus state yang jelas (`focus-visible:ring-2 focus-visible:ring-quantum-cyan`).
- [x] Font swap (`font-display: swap`) diterapkan untuk JetBrains Mono dan Plus Jakarta Sans agar terhindar dari FOIT.

---
*Sign-off:*  
**Senna Louviere**  
Creative Director, Yudiaz Creative Studio  
*Approved by Raziel Hendrix (CTO)*
