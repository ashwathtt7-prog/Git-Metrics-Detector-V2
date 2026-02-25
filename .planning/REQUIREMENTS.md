# Requirements: Git Metrics Detector

**Defined:** 2026-02-25
**Core Value:** Any GitHub repository can be analyzed and visualized with meaningful metrics and a production-quality dashboard — in minutes.

## v1 Requirements (Shipped)

### Repository Analysis

- [x] **REPO-01**: User can paste a GitHub repository URL to start analysis
- [x] **REPO-02**: Backend fetches full repository file tree from GitHub API
- [x] **REPO-03**: Backend selects and fetches highest-priority source files for deep analysis
- [x] **REPO-04**: Analysis handles GitHub API rate limits gracefully (token support)

### LLM Analysis Pipeline

- [x] **ANAL-01**: Pass 1 generates project overview (domain, stack, purpose)
- [x] **ANAL-02**: Pass 2 scans files in batches for metric candidates with trace data
- [x] **ANAL-03**: Consolidation pass deduplicates and ranks discovered metrics
- [x] **ANAL-04**: Pipeline falls back to deterministic heuristics on LLM failure
- [x] **ANAL-05**: Analysis job tracks status/progress/logs for UI polling

### Mock Data Generation

- [x] **MOCK-01**: Generates 24-32 daily data points per metric (~30 days)
- [x] **MOCK-02**: Deterministic fallback generators produce metric-specific variability
- [x] **MOCK-03**: Supports multiple metric types (error rates, latency, cache ratios, etc.)

### Dashboard & Visualization

- [x] **DASH-01**: Metabase database registration and auto-bootstrap
- [x] **DASH-02**: LLM-planned dashboard card creation with SQL queries
- [x] **DASH-03**: Public sharing link generation for dashboards
- [x] **DASH-04**: Fallback to known-good card set if LLM-planned cards fail

### User Interface

- [x] **UI-01**: Workflow UI at port 3001 with repo URL input and Analyze button
- [x] **UI-02**: Real-time stage timeline with toggleable log display
- [x] **UI-03**: Generate Mock Data action after analysis completes
- [x] **UI-04**: Continue to Dashboard button opens Metabase public link
- [x] **UI-05**: Workspaces UI at port 3000 lists saved analyses

### Installation & Operations

- [x] **INST-01**: `install.py` handles full setup (venv, npm, metabase.jar, config prompts)
- [x] **INST-02**: `run.py` starts all services (backend, frontends, Metabase)
- [x] **INST-03**: Windows batch files (`Install.bat`, `Run.bat`) for click-to-run
- [x] **INST-04**: No administrator privileges required

## v2 Requirements

### Enhanced Insights

- **INSI-01**: Detailed business explanations for each metric on click
- **INSI-02**: LLM processing transparency (show reasoning, not just results)
- **INSI-03**: Metric categorization with business impact scores

### Robustness

- **RBST-01**: More robust JSON parsing for all LLM response formats
- **RBST-02**: Graceful handling of truncated LLM outputs
- **RBST-03**: Retry logic with exponential backoff for provider failures

### Data Quality

- **DATA-01**: Improved mock data with seasonal patterns and correlations
- **DATA-02**: Support for custom date ranges in generated data
- **DATA-03**: Export raw metric data as CSV/JSON

### Multi-Repo

- **MULT-01**: Compare metrics across multiple repositories
- **MULT-02**: Aggregate dashboard for portfolio view

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time metric collection | Requires instrumentation in target repos — major scope increase |
| User authentication | Single-user local tool; unnecessary complexity |
| Cloud hosting/deployment | Local-first design philosophy |
| Mobile app | Desktop workflow tool |
| Custom chart builder | Metabase handles this already |
| Git history analysis | Focus is on code structure, not commit patterns |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 to REPO-04 | v1.0 | Complete |
| ANAL-01 to ANAL-05 | v1.0 | Complete |
| MOCK-01 to MOCK-03 | v1.0 | Complete |
| DASH-01 to DASH-04 | v1.0 | Complete |
| UI-01 to UI-05 | v1.0 | Complete |
| INST-01 to INST-04 | v1.0 | Complete |
| INSI-01 to INSI-03 | Phase 1 (next) | Pending |
| RBST-01 to RBST-03 | Phase 2 (next) | Pending |
| DATA-01 to DATA-03 | Phase 3 (next) | Pending |
| MULT-01 to MULT-02 | Phase 4 (next) | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped: 22 (all shipped)
- v2 requirements: 11 total
- Mapped to next phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after GSD framework initialization*
