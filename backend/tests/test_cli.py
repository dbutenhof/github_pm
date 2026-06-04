"""Tests for the cli module.

Generated-by: Cursor
Assisted-by: Cursor
"""

import sys
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

# Mock uvicorn before importing cli module to avoid import errors
sys.modules["uvicorn"] = MagicMock()

from github_pm.cli import main  # noqa: E402 (must be after mock)


class TestMain:
    """Test the main CLI function."""

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_calls_getpgid_and_prints_message(
        self, mock_getpgid, mock_uvicorn_run
    ):
        """Test that main gets the process group ID and prints the kill command."""
        mock_getpgid.return_value = 12345

        result = CliRunner().invoke(main, [])

        assert result.exit_code == 0
        mock_getpgid.assert_called_once_with(0)
        assert result.output.strip() == "'kill -- -12345' to stop the server"

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_calls_uvicorn_with_default_port(self, mock_getpgid, mock_uvicorn_run):
        """Test that main calls uvicorn.run with the default port."""
        mock_getpgid.return_value = 12345

        result = CliRunner().invoke(main, [])

        assert result.exit_code == 0
        mock_uvicorn_run.assert_called_once_with(
            "github_pm.app:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
        )

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_calls_uvicorn_with_custom_port(self, mock_getpgid, mock_uvicorn_run):
        """Test that --port is passed through to uvicorn.run."""
        mock_getpgid.return_value = 12345

        result = CliRunner().invoke(main, ["--port", "9000"])

        assert result.exit_code == 0
        mock_uvicorn_run.assert_called_once_with(
            "github_pm.app:app",
            host="0.0.0.0",
            port=9000,
            reload=True,
        )

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_handles_different_pgid_values(self, mock_getpgid, mock_uvicorn_run):
        """Test that main works with different process group ID values."""
        mock_getpgid.return_value = 99999

        result = CliRunner().invoke(main, [])

        assert result.exit_code == 0
        mock_getpgid.assert_called_once_with(0)
        mock_uvicorn_run.assert_called_once()

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_prints_correct_kill_command_format(
        self, mock_getpgid, mock_uvicorn_run
    ):
        """Test that the printed kill command has the correct format."""
        test_pgids = [1, 100, 12345, 999999]

        for pgid in test_pgids:
            mock_getpgid.return_value = pgid

            result = CliRunner().invoke(main, [])

            assert result.exit_code == 0
            expected_message = f"'kill -- -{pgid}' to stop the server"
            assert result.output.strip() == expected_message
