"""CLI entry point for github_pm."""

import os

import uvicorn


def main():
    """Launch the FastAPI application with uvicorn."""
    pgid = os.getpgid(0)
    print(f"'kill -- -{pgid}' to stop the server")
    uvicorn.run(
        "github_pm.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
