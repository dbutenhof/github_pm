# GitHub Project Manager Frontend

A React application built with Patternfly for managing GitHub project milestones and issues.

## Features

- View all project milestones in vertically stacked cards
- Expand milestones to see associated issues
- View issues in horizontally stacked cards with multiple rows
- Markdown-formatted issue descriptions
- User information with avatars
- Days since issue creation tracking
- Direct links to GitHub issues

## Setup

1. Install dependencies:

```bash
npm install
```

2. Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Build

To build for production:

```bash
npm run build
```

## Testing

Run tests:

```bash
npm test
```

Run tests with UI:

```bash
npm run test:ui
```

Run tests with coverage:

```bash
npm run test:coverage
```

## Code Formatting

Format all code with Prettier:

```bash
npm run format
```

Check if code is formatted correctly:

```bash
npm run format:check
```

## API Integration

The Vite dev server proxies `/api` requests to the backend. The backend port defaults to **8080** and is controlled by the `BACKEND_PORT` environment variable (read by `vite.config.js`).

When using `./run-local.sh` from the repo root, `BACKEND_PORT` is set automatically from `--port` (e.g. `./run-local.sh --port 9000`).

For `npm run dev` alone, set the port explicitly:

```bash
BACKEND_PORT=9000 npm run dev
```

Or add `BACKEND_PORT=8080` to a `.env.development` file in this directory.

### API Endpoints

- `GET /api/milestones` - Returns list of milestones
- `GET /api/issues/{milestone_number}` - Returns `{ issues, pull_requests }` for a milestone

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── MilestoneCard.jsx
│   │   ├── IssueCard.jsx
│   │   └── *.test.jsx
│   ├── services/
│   │   ├── api.js
│   │   └── *.test.js
│   ├── utils/
│   │   ├── dateUtils.js
│   │   └── *.test.js
│   ├── test/
│   │   └── setup.js
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## Technologies

- React 18
- Patternfly React Components
- Vite
- Vitest for testing
- React Testing Library
- React Markdown for rendering issue descriptions
- Prettier for code formatting
