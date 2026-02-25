# Quick Plan: Fix Missing Visualization Dependencies

## Problem
`run.py` fails with `ERROR: frontend/visualization/node_modules missing` because `install.py` does not include `frontend/visualization` in its dependency installation logic.

## Analysis
- `run.py` (L24): Defines `FRONTEND_VISUALIZATION_DIR`.
- `run.py` (L357-358): Specifically checks for `node_modules` in that directory.
- `install.py`: Missing `FRONTEND_VISUALIZATION_DIR` definition and `_ensure_frontend_deps` call for it.

## Proposed Changes
### [install.py](file:///d:/git-metrics-detector/v10/Git-metrics-detector/install.py)
- Define `FRONTEND_VISUALIZATION_DIR`.
- Add `_ensure_frontend_deps(FRONTEND_VISUALIZATION_DIR)` to the `main()` function.

## Verification Plan
1. Run `python install.py` and verify it attempts to install deps for `frontend/visualization`.
2. check if `frontend/visualization/node_modules` exists.
3. Run `python run.py --smoke` to verify all services start (or at least pass the check).
