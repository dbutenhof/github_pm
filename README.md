# github_pm
A tool to help with project management using GitHub issues, PRs, milestones, labels

## Overview

**github_pm** is a project management tool that leverages GitHub's API to help you manage issues, pull requests, milestones, and labels more efficiently. It is designed for developers and teams who want powerful workflows around their GitHub projects.

This project provides a backend API (FastAPI) and a frontend web UI for seamless and organized project management, all with modern best practices.

---

## Features

- Organize, search, and filter GitHub Issues and Pull Requests
- Manage milestones, labels, and project boards
- Automate common GitHub project management tasks
- Easy-to-use web interface (frontend)
- Powerful RESTful API (backend)
- Robust CLI for scripting and automation

---

## Getting Started

### Prerequisites

- Python 3.14+
- Node.js 20+ (for the frontend)

### Installation

#### Backend

```bash
cd backend
uv sync --dev    # Installs dependencies using uv
uv run python -m github_pm   # Start the backend API
```

#### Frontend

```bash
cd frontend
npm ci             # Install dependencies
npm run dev        # Start the frontend development server
```

#### Full test deployment

```bash
./run-local.sh
```

This will start both the backend (on port 8000) and the frontend (on port 3000)
in the background. The script will give you a sample alias command to stop both
of them, like

```console
Backend is running in the background at http://localhost:8000
Frontend is running in the background at http://localhost:3000

To terminate, run:
  kill -- - 49613

HINT: capture this in an alias for later:
and then you can terminate with 'kill-pm'

  alias kill-pm="kill -- - 49613"
```

---

## Usage

- Navigate to the frontend web UI to manage your GitHub projects visually.
- Access the API docs at `http://localhost:8000/docs` when the backend is running.

The UI shows all the milestones defined for the GitHub project, with the description
and due date. You can show all issues and PRs associated with a milestone by opening
the "Show issues" control.

At the top of the page, the Manage Milestones and Manage Labels controls allow you
to see all of the available milestones and labels for the project. Here you can
delete any item by clicking the "x" in the chiclet, or create new items using the
"+" icon.

Each expanded issue is shown with the current milestone: you can assign that issue
to a new milestone using the pulldown. You can also remove assigned labels by
clicking the label chiclet's "x" icon, or add new labels to the issue with the "+"
icon.

---

## Development

### Linting & Formatting

- **Backend:**  
  - Lint: `uv run flake8 src tests`
  - Format: `uv run black --check src tests`
  - Import Sort: `uv run isort --check src tests`
- **Frontend:**  
  - Format: `npm run format:check`
  - Lint: (add your preferred lint command)

### Testing

- **Backend:**  
  - Run tests (add your test framework/command here)
- **Frontend:**  
  - Run tests: `npm test -- --run`

### Continuous Integration

GitHub Actions are set up for linting, formatting, and testing on pull requests and pushes:

- Backend: Python linting, formatting, dependency install via [uv](https://github.com/astral-sh/uv)
- Frontend: Node linting, formatting, and tests

---

## Configuration

- Edit your backend configuration and package dependencies in `backend/pyproject.toml`
- Customize Flake8 with `.flake8` in the backend directory

---

## Contributing

Issues and pull requests are welcome!  
See [CONTRIBUTING.md](CONTRIBUTING.md) (if available) or open an issue for any questions or suggestions.

---

## License

[Apache License 2.0](LICENSE)

---

## Links

- **Homepage & Docs:** [https://github.com/dbutenhof/github-pm](https://github.com/dbutenhof/github-pm)
- **Repository:** [https://github.com/dbutenhof/github-pm](https://github.com/dbutenhof/github-pm)
- **Report Issues:** [https://github.com/dbutenhof/github-pm/issues](https://github.com/dbutenhof/github-pm/issues)

