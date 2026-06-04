#!/bin/bash
#
# Run the backend and frontend locally in a mode where saving changes will
# immediately update the running instances. This is useful for active
# development.
#
# Usage:
#   ./run-local.sh [--port <n>]
#
# Extra arguments are passed through to the github_pm CLI (e.g. --port 9000).
#
# Dependencies:
# - Users will need to update the backend/.env file to meet their needs or
#   set (at least) the GITHUB_TOKEN environment variable.
#
# Environment Variables:
# - DEBUG: set to any value to enable debug mode
# - GITHUB_TOKEN: the GitHub token to use for authentication
#   - This is required if the backend/.env file is not present.
# - APP_NAME: the name of the application
#   - This is used to identify the application in the UI.
#   - This is optional and will default to "GitHub Project Manager".
# - GITHUB_REPO: the GitHub repository to use for authentication
#   - This is used to identify the repository in the UI.
#   - This is optional and will default to "vllm-project/guidellm".
# - BACKEND_PORT: set automatically from --port (default 8080) for the Vite
#   dev proxy when starting the frontend via this script.
#
# Assisted-by: Cursor AI
if [ ! -z "${DEBUG}" ]; then
    set -xe
fi
TOP=$(git rev-parse --show-toplevel)
BACKEND=${TOP}/backend
FRONTEND=${TOP}/frontend
if [ ! -f "${BACKEND}/.env" -a -z "${GITHUB_TOKEN}" ]; then
    echo "Error: GITHUB_TOKEN not defined" >&2
    echo "Please set the GITHUB_TOKEN environment variable to meet your needs." >&2
    exit 1
fi

# Forward script args to github_pm; derive port for readiness checks and messages.
GITHUB_PM_ARGS=("$@")
BACKEND_PORT=8080
args=("${GITHUB_PM_ARGS[@]}")
idx=0
while [ "${idx}" -lt "${#args[@]}" ]; do
    arg="${args[idx]}"
    case "${arg}" in
        --port)
            next=$((idx + 1))
            if [ "${next}" -lt "${#args[@]}" ]; then
                BACKEND_PORT="${args[next]}"
            fi
            ;;
        --port=*)
            BACKEND_PORT="${arg#--port=}"
            ;;
    esac
    idx=$((idx + 1))
done
export BACKEND_PORT

# Make sure all dependencies are installed.
temp_file=$(mktemp)
echo "Installing dependencies... (${temp_file})"
(
    cd "${BACKEND}"
    uv sync
    cd "${FRONTEND}"
    npm install
) > "${temp_file}" 2>&1

if [ $? -ne 0 ]; then
    echo "Error: failed to install dependencies" >&2
    cat "${temp_file}" >&2
    rm "${temp_file}"
    exit 1
fi

# start the backend
echo "Starting backend..."
(
    cd ${BACKEND}
    uv run github_pm "${GITHUB_PM_ARGS[@]}"
) &
backend_pid=$!

# start the frontend
echo "Starting frontend..."
(
    cd ${FRONTEND}
    npm run dev
) &
frontend_pid=$!

# Killing the subshells won't kill all child processes, so grab their process
# group IDs and use those instead. They're likely in the same PGID; but check
# both to be sure.
b_pgid=$(ps -o pgid= -p ${backend_pid})
f_pgid=$(ps -o pgid= -p ${frontend_pid})

# Remove spaces from "ps -o" output
backend_pgid=${b_pgid//[[:space:]]/}
frontend_pgid=${f_pgid//[[:space:]]/}

to_kill="-${backend_pgid}"
if [[ ${frontend_pgid} -ne ${backend_pgid} ]]; then
    to_kill="${to_kill} -${frontend_pgid}"
fi

# Let frontend and backend start up and write their output before we finish,
# or our helpful note will be lost.
waiting=0
while ! curl -s "http://localhost:${BACKEND_PORT}/" > /dev/null 2>&1; do
    if [ ${waiting} -eq 0 ]; then
        echo "Waiting for backend to start..."
    fi
    sleep 1
    waiting=$((waiting + 1))
    if [ ${waiting} -gt 10 ]; then
        echo "Error: backend didn't start in time" >&2
        exit 1
    fi
done
waiting=0
while ! curl -s http://localhost:3000/ > /dev/null 2>&1; do
    if [ ${waiting} -eq 0 ]; then
        echo "Waiting for frontend to start..."
    fi
    sleep 1
    waiting=$((waiting + 1))
    if [ ${waiting} -gt 10 ]; then
        echo "Error: frontend didn't start in time" >&2
        exit 1
    fi
done

echo ""
echo "--------------------------------"
echo "Backend is running in the background at http://localhost:${BACKEND_PORT}"
echo "Frontend is running in the background at http://localhost:3000"
echo ""
echo "To terminate, run:"
echo "  kill -- ${to_kill}"
echo ""
echo "HINT: capture this in an alias for later:"
echo "and then you can terminate with 'kill-pm'"
echo ""
echo "  alias kill-pm=\"kill -- ${to_kill}\""
echo ""
