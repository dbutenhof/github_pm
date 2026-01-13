# Backend Python Dependency Management with uv

## Dependency Management
- All backend Python dependencies MUST be managed through the `uv` tool
- When adding, removing, or updating dependencies, use `uv` commands:
  - `uv add <package>` to add a dependency
  - `uv remove <package>` to remove a dependency
  - `uv sync` to sync dependencies from `pyproject.toml` and `uv.lock`
  - `uv lock` to update the lock file
- NEVER use `pip install`, `poetry add`, or other package managers for backend dependencies
- Ensure `uv.lock` file is committed to version control

## Testing Backend Code
- ALWAYS use `uv run` prefix when running tests or test-related commands to ensure proper context
- Examples:
  - `uv run pytest` (not `pytest`)
  - `uv run pytest tests/` (not `pytest tests/`)
  - `uv run tox` (not `tox`)
  - `uv run python -m pytest` (not `python -m pytest`)
- When suggesting test commands in code or documentation, always include the `uv run` prefix
- This ensures tests run in the correct virtual environment with all dependencies properly resolved

## Code Generation and Scripts
- When generating code that runs Python commands in backend directories, always use `uv run` prefix
- When creating scripts or Makefile targets for backend operations, use `uv run` for all Python execution
