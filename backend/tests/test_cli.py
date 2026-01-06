"""Tests for the cli module.

ai-generated: Cursor
"""

import sys
from unittest.mock import MagicMock, patch

# Mock uvicorn before importing cli module to avoid import errors
sys.modules["uvicorn"] = MagicMock()

from github_pm.cli import main  # noqa: E402 (must be after mock)


class TestMain:
    """Test the main CLI function."""

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    @patch("builtins.print")
    def test_main_calls_getpgid_and_prints_message(
        self, mock_print, mock_getpgid, mock_uvicorn_run
    ):
        """Test that main gets the process group ID and prints the kill command."""
        # Arrange
        mock_getpgid.return_value = 12345

        # Act
        main()

        # Assert
        mock_getpgid.assert_called_once_with(0)
        mock_print.assert_called_once_with("'kill -- -12345' to stop the server")

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_calls_uvicorn_with_correct_parameters(
        self, mock_getpgid, mock_uvicorn_run
    ):
        """Test that main calls uvicorn.run with the correct parameters."""
        # Arrange
        mock_getpgid.return_value = 12345

        # Act
        main()

        # Assert
        mock_uvicorn_run.assert_called_once_with(
            "github_pm.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    def test_main_handles_different_pgid_values(self, mock_getpgid, mock_uvicorn_run):
        """Test that main works with different process group ID values."""
        # Arrange
        mock_getpgid.return_value = 99999

        # Act
        main()

        # Assert
        mock_getpgid.assert_called_once_with(0)
        mock_uvicorn_run.assert_called_once()

    @patch("github_pm.cli.uvicorn.run")
    @patch("github_pm.cli.os.getpgid")
    @patch("builtins.print")
    def test_main_prints_correct_kill_command_format(
        self, mock_print, mock_getpgid, mock_uvicorn_run
    ):
        """Test that the printed kill command has the correct format."""
        # Arrange
        test_pgids = [1, 100, 12345, 999999]

        for pgid in test_pgids:
            mock_getpgid.return_value = pgid
            mock_print.reset_mock()

            # Act
            main()

            # Assert
            expected_message = f"'kill -- -{pgid}' to stop the server"
            mock_print.assert_called_once_with(expected_message)
