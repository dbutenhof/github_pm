# Agent instructions for github_pm workspaces

## Required checks before finishing any task

- **`tox` must complete successfully** for every change that touches the Python backend (and should be run once you believe backend work is done). Run it from the **`backend`** directory:

  ```bash
  cd backend && tox
  ```

  This runs the environments defined in `backend/pyproject.toml` (format, import order, lint, tests, coverage). Do **not** consider backend work complete while **`tox`** reports failures.

- **Fix all lint failures and unit test failures** reported by those checks (and any other checks you ran) **before** stopping. A green **`tox`** run is the acceptance bar for backend changes.

- For **frontend** (`frontend/`) changes, run **`npm test`** (and **`npm run format:check`** if you edited formatted sources) from `frontend/` and fix failures there as well when the task involves the UI or client code.

## Notes

- Use **`uv`** in the backend as described in the project `README.md` (e.g. `uv sync`, `uv run`).
- Prefer small, focused diffs; match existing style and patterns in both backend and frontend.
