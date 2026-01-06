#!/bin/bash
#
# Run the backend and frontend locally in a mode where saving changes will
# immediately update the running instances. This is useful for active
# development.
#
# Usage:
#   ./run-local.sh
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
    uv run github_pm 
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
while ! curl -s http://localhost:8000/ > /dev/null 2>&1; do
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
echo "Backend is running in the background at http://localhost:8000"
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
