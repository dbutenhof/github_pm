"""CLI entry point for github_pm.

Assisted-by: Cursor
"""

import os

import click
import uvicorn


@click.command()
@click.option(
    "--port",
    type=click.IntRange(1, 65535),
    default=8080,
    help="TCP port to bind (default: 8080).",
)
def main(port: int) -> None:
    """Launch the FastAPI application with uvicorn."""
    pgid = os.getpgid(0)
    print(f"'kill -- -{pgid}' to stop the server")
    uvicorn.run(
        "github_pm.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
