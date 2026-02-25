# Git Metrics Detector

## What This Is

A full-stack application that analyzes GitHub repositories using LLM-powered intelligence to discover trackable product/engineering metrics, generates realistic synthetic time-series data, and automatically publishes interactive Metabase dashboards. Built for developers and product teams who want instant, data-driven visibility into any codebase.

## Core Value

Any GitHub repository can be analyzed and visualized with meaningful metrics and a production-quality dashboard — in minutes, not days.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ **REPO-01**: User can paste a GitHub repo URL and trigger analysis — v1.0
- ✓ **ANAL-01**: Backend fetches repo tree + key files from GitHub — v1.0
- ✓ **ANAL-02**: LLM multi-pass analysis extracts project overview and metric candidates — v1.0
- ✓ **ANAL-03**: Metrics are consolidated, deduplicated, and ranked — v1.0
- ✓ **MOCK-01**: Realistic synthetic time-series data generated (24-32 daily points per metric) — v1.0
- ✓ **DASH-01**: Metabase dashboard auto-created with public shareable URL — v1.0
- ✓ **UI-01**: Workflow UI shows analysis stages with real-time logs — v1.0
- ✓ **UI-02**: Workspaces UI lists saved analyses with dashboard links — v1.0
- ✓ **INST-01**: One-click install/run via batch files (no admin required) — v1.0

### Active

<!-- Current scope. Building toward these. -->

- [ ] Enhanced metric insights with detailed LLM explanations
- [ ] Improved LLM processing transparency/visibility
- [ ] More robust JSON parsing for LLM responses
- [ ] Better error recovery and fallback mechanisms
- [ ] Improved mock data variety and realism

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Real-time metric collection from live codebases — complexity, v2+ feature
- Multi-user authentication — single-user tool for now
- Cloud deployment — local-first by design
- Mobile app — web-first, desktop workflow

## Context

- **Tech Stack**: FastAPI (Python), React+Vite (frontend), SQLite, Metabase, Google Gemini LLM
- **Architecture**: Multi-service local deployment (4 ports: 8001, 3000, 3001, 3003)
- **Prior Work**: V2 of original concept, significant iteration on LLM reliability and mock data quality
- **Key Challenge**: LLM output reliability — JSON parsing, truncation, and fallback handling
- **Database**: SQLite at `backend/data/metrics.db` with tables: workspaces, metrics, metric_entries, analysis_jobs

## Constraints

- **Tech Stack**: Python 3.10+, Node 18+, Java 21+ (Metabase) — established, no changes
- **No Admin Access**: Must work without administrator privileges (user-space venv, unprivileged ports, portable Java)
- **Local-First**: All processing happens locally; only GitHub API + LLM API calls go external
- **LLM Provider**: Google Gemini via service account — API key managed in `backend/.env`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over PostgreSQL | Simplicity, zero-config, portable | ✓ Good |
| Metabase for dashboards | Professional visualizations without building custom charts | ✓ Good |
| LLM multi-pass analysis | Better metric discovery than single-pass | ✓ Good |
| Batch file installation | Windows-friendly, no admin needed | ✓ Good |
| Deterministic fallbacks for LLM failures | Reliability over purity | ✓ Good |

---
*Last updated: 2026-02-25 after GSD framework initialization*
