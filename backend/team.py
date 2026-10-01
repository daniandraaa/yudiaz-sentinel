"""Yudiaz Creative Studio - AI Agent Cluster Directory & Roster.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001
"""

from __future__ import annotations

from typing import Any, Dict, List

# Roster of 9 Autonomous AI Agents operating across Yudiaz Creative Studio
AI_AGENTS_ROSTER: List[Dict[str, Any]] = [
    {
        "id": "daffa",
        "name": "Daffa",
        "role": "Head of CEO Office & Chief of Staff",
        "department": "Executive Leadership",
        "status": "active",
        "avatar_badge": "COS",
        "specialization": "Executive oversight, cross-division unblocking, strategic alignment",
        "description": "Pengawasan operasional studio, tangan kanan CEO, penyelarasan lintas divisi",
    },
    {
        "id": "raziel-hendrix",
        "name": "Raziel Hendrix",
        "role": "CTO & Orchestrator",
        "department": "Engineering Leadership",
        "status": "active",
        "avatar_badge": "CTO",
        "specialization": "Multi-agent orchestration, engineering strategy, system governance",
        "description": "Arsitek operasional, delegasi multi-agent, evaluasi sistem tingkat tinggi",
    },
    {
        "id": "kael-ashford",
        "name": "Kael Ashford",
        "role": "Lead Architect",
        "department": "System Architecture",
        "status": "active",
        "avatar_badge": "ARCH",
        "specialization": "System design, clean architecture, API contracts, deployment blueprints",
        "description": "System design, blueprint, database schema, API contracts, ADR",
    },
    {
        "id": "nara-vasquez",
        "name": "Nara Vasquez",
        "role": "Lead Researcher",
        "department": "Research & Intelligence",
        "status": "active",
        "avatar_badge": "RSCH",
        "specialization": "Emerging AI models, compute efficiency research, technical analysis",
        "description": "Riset teknologi komputasi, benchmark model LLM, audit arsitektur",
    },
    {
        "id": "senna-louviere",
        "name": "Senna Louviere",
        "role": "Creative Director",
        "department": "Creative & Design",
        "status": "active",
        "avatar_badge": "DSGN",
        "specialization": "Visual aesthetic, brand cohesion, UI/UX interaction standards",
        "description": "UI/UX aesthetic, brand styling, visual standards, human interface",
    },
    {
        "id": "idris-nakamura",
        "name": "Idris Nakamura",
        "role": "Senior Developer",
        "department": "Backend & Core Engineering",
        "status": "active",
        "avatar_badge": "DEV",
        "specialization": "FastAPI backend, high-performance async daemons, socket programming",
        "description": "Backend, API engineering, systems programming, script automation",
    },
    {
        "id": "mika-stellan",
        "name": "Mika Stellan",
        "role": "Frontend Engineer",
        "department": "Frontend & Interfaces",
        "status": "active",
        "avatar_badge": "FRONT",
        "specialization": "Responsive dashboards, Chart.js sparklines, real-time SSE UX",
        "description": "SPA dashboard, reactive UI, Tailwind CSS, charts & interactions",
    },
    {
        "id": "viktor-moreau",
        "name": "Viktor Moreau",
        "role": "Lead QA",
        "department": "Quality Assurance & Security",
        "status": "active",
        "avatar_badge": "QA",
        "specialization": "Automated verification, load testing, security audits, resilience",
        "description": "Verification, end-to-end testing, security testing, performance audit",
    },
    {
        "id": "elara-sinclair",
        "name": "Elara Sinclair",
        "role": "PA to CEO",
        "department": "Executive Operations",
        "status": "active",
        "avatar_badge": "PA",
        "specialization": "Executive coordination, timeline management, daily deliverables",
        "description": "Daily operations, project schedules, executive briefings",
    },
    {
        "id": "jovan-aritza",
        "name": "Jovan Aritza",
        "role": "Intel Agent",
        "department": "Academic & Field Intelligence",
        "status": "active",
        "avatar_badge": "INTEL",
        "specialization": "Telkom University intelligence, academic network monitoring",
        "description": "Telkom University intelligence, academic network monitoring",
    },
    {
        "id": "cucurella",
        "name": "Cucurella",
        "role": "Head of Soetahills Growth",
        "department": "Real Estate & Strategic Growth",
        "status": "active",
        "avatar_badge": "GROWTH",
        "specialization": "Real estate market intel, content planning, Soetahills property growth",
        "description": "Market intelligence properti, strategi pertumbuhan unit Soetahills, konten visual",
    },
    {
        "id": "devera",
        "name": "Devera",
        "role": "CTO & Accountant",
        "department": "Gold Capital & Finance Ops",
        "status": "active",
        "avatar_badge": "ACCT",
        "specialization": "Precious metals capital reconciliation, zero-discrepancy ledger, NPP platform",
        "description": "CTO & Lead Accountant platform No Pusing Pusing untuk Bang Fauzan & Konsorsium Emas",
    },
    {
        "id": "orca",
        "name": "Orca",
        "role": "LaTeX Editor & Academic Partner",
        "department": "Academic Publishing & Thesis Support",
        "status": "active",
        "avatar_badge": "TEX",
        "specialization": "LaTeX typesetting, Overleaf/TeX Live troubleshooting, academic proposal drafting",
        "description": "LaTeX Editor handal & mitra penulisan Proposal Tugas Akhir khusus untuk Dimas",
    },
]


def get_team_roster() -> Dict[str, Any]:
    """Return catalog of Yudiaz AI Agent cluster."""
    return {
        "organization": "Yudiaz Creative Studio",
        "total_agents": len(AI_AGENTS_ROSTER),
        "agents": AI_AGENTS_ROSTER,
    }
