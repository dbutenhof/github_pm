# github_pm

A tool to help with project management using GitHub issues, PRs, milestones, labels

## Overview

**github_pm** is a project management tool that leverages GitHub's API to help you manage issues, pull requests, milestones, and labels more efficiently. It is designed for developers and teams who want powerful workflows around their GitHub projects.

This project provides a backend API (FastAPI) and a frontend web UI for seamless and organized project management, all with modern best practices.

______________________________________________________________________

## Features

- Organize, search, and filter GitHub Issues and Pull Requests
- Manage milestones, labels, and project boards
- Automate common GitHub project management tasks
- Easy-to-use web interface (frontend)
- Powerful RESTful API (backend)

______________________________________________________________________

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+ (for the frontend)

### Installation

#### Backend

```bash
cd backend
uv sync --dev    # Installs dependencies using uv
uv run python -m github_pm   # Start the backend API
```

Backend configuration is through a `.env` file in the `backend` directory.
The .env_sample file shows the necessary configuration keywords, including
a personal access token for GitHub API access and the target GitHub
repository name.

To create a GitHub API token, open your personal GitHub Settings, and select "Developer Settings" from the sidebar. Open "Personal access tokens" and select "Tokens (classic)"

Click on "Generate new token" and select the "Generate new token (classic)" option from the pulldown. You can set a Note to identify this particular token. Select the Expiration (30 days default), and "repo". Make sure you copy and save the generated token right away, because you can't display it again.

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

This will start both the backend (default port 8080) and the frontend (port 3000).
Pass `--port <n>` to `./run-local.sh` to use a different backend port (the frontend proxy follows automatically).
in the background. The script will give you a sample alias command to stop both
of them, like

```console
Backend is running in the background at http://localhost:8080
Frontend is running in the background at http://localhost:3000

To terminate, run:
  kill -- - 49613

HINT: capture this in an alias for later:
and then you can terminate with 'kill-pm'

  alias kill-pm="kill -- - 49613"
```

______________________________________________________________________

## Usage

- Navigate to the frontend web UI to manage your GitHub projects visually.
- Access the API docs at `http://localhost:8080/docs` when the backend is running (adjust the port if you used `--port`).

The UI shows all the milestones defined for the configured GitHub project, with
the description and due date. You can show all issues and PRs associated with a
milestone by opening the "Show issues" control.

At the top of the page, the Manage Milestones and Manage Labels controls allow you
to see all of the available milestones and labels for the project. Here you can
delete any item by clicking the "x" in the chiclet, or create new items using the
"+" icon.

Issues and PRs are grouped under their milestone headers, so the table does not
repeat a separate Milestone column. Each issue or PR row has an Actions menu
(the compact ellipsis icon next to the title). Use it to close an issue or move
it to another milestone. Moving an issue refreshes the loaded milestone cards so
it appears under its new milestone. Labels can be removed with the label
chiclet's "x" icon or added with the "+" icon.

If the repository defines GitHub issue fields named "Priority" or "Effort", they
appear as columns between Links and Labels. Click a field value to open a
pulldown and choose a new option, or choose "No value" to clear it. Fields are
read from the repository owner's issue field definitions, so projects without
those fields simply show no extra columns.

The Type column shows an Epic icon when an issue has sub-issues. Otherwise it
reflects the GitHub issue type: a rocket for Feature, a bug for Bug, and a
task/clipboard for Task. Issues without a type show a neutral placeholder, and
custom type names get a generic icon with the type name in the tooltip. Click a
non-Epic type icon to open a pulldown showing the available type names and
icons. Epic is derived from sub-issues and cannot be selected directly; clicking
its icon explains how to change it.

If the issue is assigned to one or more team members, the display will display
their GitHub login names. You can change the list of assignees using the pulldown.

Issues are sorted by number by default. Click the sort icon in the Number,
Type, Author, Priority, Effort, or Title header to sort siblings within each
hierarchy level; click the same header again to reverse the direction. The
selected column sort is remembered between sessions. Priority and Effort
ascending run from the lowest option to the highest, and rows without a value
sort last.

The Labels header has its own sort icon. It opens the label-order editor used to
put selected labels ahead of other issues. Choosing a column header switches
back to column sorting; changing the label order switches to label sorting.
Unlisted labels sort after the configured labels.

______________________________________________________________________

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

______________________________________________________________________

## Configuration

- Edit your backend configuration and package dependencies in `backend/pyproject.toml`
- Customize Flake8 with `.flake8` in the backend directory

______________________________________________________________________

## Contributing

Issues and pull requests are welcome!
See [CONTRIBUTING.md](CONTRIBUTING.md) (if available) or open an issue for any questions or suggestions.

______________________________________________________________________

## License

[Apache License 2.0](LICENSE)

______________________________________________________________________

## Links

- **Homepage & Docs:** [https://github.com/dbutenhof/github-pm](https://github.com/dbutenhof/github-pm)
- **Repository:** [https://github.com/dbutenhof/github-pm](https://github.com/dbutenhof/github-pm)
- **Report Issues:** [https://github.com/dbutenhof/github-pm/issues](https://github.com/dbutenhof/github-pm/issues)
