# Agent instructions for github_pm workspaces

## Read this file when starting or resuming work

- **Open `AGENTS.md` again** when you begin a task on this repo or return after a long gap, so required checks (below) stay in context until **`tox`** and frontend checks are green.

## Attributing AI coding assistance

When using AI coding assistants to generate a module or a new function, annotate that code with a module comment or a function docstring using the `Generated-by: <name of the AI coding assistant>` tag. When substantial code changes (not including minor formatting or typo fixes) are made to a module or function not already annotated with "Generated-by" or "Assisted-by", annotate the changes with the `Assisted-by: <name of the AI coding assistant>` tag.

```markdown
Assisted-by: <name of the AI coding assistant>
```

For example:

```markdown
Assisted-by: Cursor
Assisted-by: GitHub Copilot
Assisted-by: Claude
Assisted-by: gemini-code-assist
Assisted-by: openai-code-assist
```

## Required checks before finishing any task

### Python backend (`backend/`)

- **`tox` must complete successfully** for every change that touches the Python backend (and must be run once you believe backend work is done):

  ```bash
  cd backend && tox
  ```

  This runs the environments defined in `backend/pyproject.toml`: **Black** (`format`), **isort** (`isort`), **flake8** (`lint`), **pytest** (`test`), and **coverage** (`coverage`). Do **not** consider backend work complete while **`tox`** reports failures.

- **While iterating**, you may run a faster subset (still required before hand-off if you only used this shortcut):

  ```bash
  cd backend && tox -e format,isort,lint
  ```

  When that is green, run the full **`tox`** (including **`test`** / **`coverage`**) before stopping.

- **Auto-fixing style** (use only when you are already touching those files; avoid unrelated reformatting): from `backend/` with dev dependencies installed:

  ```bash
  uv sync --extra dev
  uv run black src tests
  uv run isort src tests
  ```

  Then re-run **`tox`** (or at least **`tox -e format,isort,lint`**) so checks pass without relying on uncommitted formatter drift.

- **flake8** enforces more than imports: for example **E731** forbids assigning a **`lambda`** where a nested **`def`** is clearer. Fix all **flake8** issues, not only import order.

- **isort** is configured in `pyproject.toml` (`profile = "black"`, `known_first_party = ["github_pm"]`). First-party imports must match that layout (including ordering among `github_pm.*` imports).

- **Fix all failures** those tools report **before** stopping. A green full **`tox`** run is the acceptance bar for backend changes.

### Frontend (`frontend/`)

When the task changes UI or client code under `frontend/src/`:

```bash
cd frontend && npm run format && npm run format:check && npm test
```

- **`npm run format`** applies Prettier; **`npm run format:check`** verifies formatting in CI style; **`npm test`** runs the Vitest suite. Do not skip **`format:check`** after editing formatted sources.

## Notes

- Use **`uv`** in the backend as described in the project `README.md` (e.g. `uv sync`, `uv run`).
- Prefer small, focused diffs; match existing style and patterns in both backend and frontend.
