"""Tests for the context module.

ai-generated: Cursor
"""

import os
from unittest.mock import patch

from github_pm.context import context, Settings


class TestSettings:
    """Test the Settings class."""

    def test_default_settings(self):
        """Test that default settings are correct."""
        # Arrange - Clear env vars that might override defaults
        env_vars_to_clear = ["APP_NAME", "GITHUB_REPO", "GITHUB_TOKEN"]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.pop(var, None)

        try:
            # Act - Create settings without .env file by using a temp directory
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    settings = Settings()
                finally:
                    os.chdir(original_cwd)

            # Assert
            assert settings.app_name == "GitHub Project Manager"
            assert settings.github_repo == "vllm-project/guidellm"
            assert settings.github_token == ""
        finally:
            # Restore original environment
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_custom_settings_from_env(self):
        """Test that settings can be overridden from environment variables."""
        # Arrange
        env_vars = {
            "APP_NAME": "My Custom App",
            "GITHUB_REPO": "myorg/myrepo",
            "GITHUB_TOKEN": "ghp_test_token_12345",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.app_name == "My Custom App"
        assert settings.github_repo == "myorg/myrepo"
        assert settings.github_token == "ghp_test_token_12345"

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case-insensitive."""
        # Arrange
        env_vars = {
            "app_name": "Lowercase App Name",
            "GITHUB_REPO": "test/repo",
            "github_token": "lowercase_token",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.app_name == "Lowercase App Name"
        assert settings.github_repo == "test/repo"
        assert settings.github_token == "lowercase_token"

    def test_mixed_case_env_vars(self):
        """Test that mixed case environment variables work."""
        # Arrange
        env_vars = {
            "App_Name": "Mixed Case App",
            "GitHub_Repo": "mixed/case",
            "GITHUB_TOKEN": "mixed_token",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.app_name == "Mixed Case App"
        assert settings.github_repo == "mixed/case"
        assert settings.github_token == "mixed_token"

    def test_extra_fields_ignored(self):
        """Test that extra fields in environment are ignored."""
        # Arrange
        env_vars = {
            "APP_NAME": "Test App",
            "EXTRA_FIELD_1": "should be ignored",
            "EXTRA_FIELD_2": "also ignored",
            "UNRELATED_VAR": "ignored too",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.app_name == "Test App"
        # Verify extra fields are not accessible
        assert not hasattr(settings, "EXTRA_FIELD_1")
        assert not hasattr(settings, "EXTRA_FIELD_2")
        assert not hasattr(settings, "UNRELATED_VAR")

    def test_env_file_loading(self, tmp_path):
        """Test that settings can be loaded from .env file."""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_NAME=Env File App\n"
            "GITHUB_REPO=envfile/repo\n"
            "GITHUB_TOKEN=env_file_token\n"
        )

        # Act
        with patch.dict(os.environ, {}, clear=False):
            # Temporarily change directory to where .env file is located
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                settings = Settings()
            finally:
                os.chdir(original_cwd)

        # Assert
        assert settings.app_name == "Env File App"
        assert settings.github_token == "env_file_token"
        assert settings.github_repo == "envfile/repo"

    def test_env_file_override_by_env_vars(self, tmp_path):
        """Test that environment variables override .env file values."""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_NAME=Env File App\n"
            "GITHUB_REPO=envfile/repo\n"
            "GITHUB_TOKEN=env_file_token\n"
        )

        env_vars = {
            "APP_NAME": "Env Var Override",
            "GITHUB_TOKEN": "env_var_token",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                settings = Settings()
            finally:
                os.chdir(original_cwd)

        # Assert
        # Environment variables should override .env file
        assert settings.app_name == "Env Var Override"
        assert settings.github_token == "env_var_token"
        # This one should come from .env file
        assert settings.github_repo == "envfile/repo"

    def test_empty_string_values(self):
        """Test that empty string values are handled correctly."""
        # Arrange
        env_vars = {
            "APP_NAME": "",
            "GITHUB_REPO": "",
            "GITHUB_TOKEN": "",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.app_name == ""
        assert settings.github_repo == ""
        assert settings.github_token == ""

    def test_settings_attributes_exist(self):
        """Test that all expected settings attributes exist."""
        # Arrange
        settings = Settings()

        # Act & Assert
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "github_repo")
        assert hasattr(settings, "github_token")
        assert isinstance(settings.app_name, str)
        assert isinstance(settings.github_repo, str)
        assert isinstance(settings.github_token, str)

    def test_settings_model_config(self):
        """Test that Settings model configuration is correct."""
        # Arrange
        settings = Settings()

        # Act & Assert
        # Verify model_config settings (model_config is a dict in Pydantic v2)
        config = settings.model_config
        assert config.get("extra") == "ignore"
        assert config.get("validate_default") is True
        assert config.get("case_sensitive") is False
        assert config.get("env_file") == ".env"

    def test_partial_env_override(self):
        """Test that only some settings can be overridden from environment."""
        # Arrange
        env_vars = {
            "GITHUB_TOKEN": "partial_token",
        }
        # Clear other env vars that might interfere
        env_vars_to_clear = ["APP_NAME", "GITHUB_REPO"]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.pop(var, None)

        try:
            # Act
            with patch.dict(os.environ, env_vars, clear=False):
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(tmpdir)
                        settings = Settings()
                    finally:
                        os.chdir(original_cwd)

            # Assert
            # Only github_token should be overridden
            assert settings.github_token == "partial_token"
            # Others should use defaults
            assert settings.app_name == "GitHub Project Manager"
            assert settings.github_repo == "vllm-project/guidellm"
        finally:
            # Restore original environment
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_settings_are_pydantic_model(self):
        """Test that Settings is a proper Pydantic model."""
        # Arrange & Act
        settings = Settings()

        # Assert
        # Verify it has Pydantic model methods
        assert hasattr(settings, "model_dump")
        assert hasattr(settings, "model_validate")
        assert hasattr(settings, "model_config")

    def test_settings_model_dump(self):
        """Test that Settings can be dumped to dict."""
        # Arrange - Clear env vars to get defaults
        env_vars_to_clear = ["APP_NAME", "GITHUB_REPO", "GITHUB_TOKEN"]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.pop(var, None)

        try:
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    settings = Settings()
                finally:
                    os.chdir(original_cwd)

            # Act
            dumped = settings.model_dump()

            # Assert
            assert isinstance(dumped, dict)
            assert "app_name" in dumped
            assert "github_repo" in dumped
            assert "github_token" in dumped
            assert dumped["app_name"] == "GitHub Project Manager"
            assert dumped["github_repo"] == "vllm-project/guidellm"
            assert dumped["github_token"] == ""
        finally:
            # Restore original environment
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value


class TestContext:
    """Test the context module-level instance."""

    def test_context_is_settings_instance(self):
        """Test that context is an instance of Settings."""
        # Assert
        assert isinstance(context, Settings)

    def test_context_has_attributes(self):
        """Test that context has all expected attributes."""
        # Assert
        assert isinstance(context.app_name, str)
        assert isinstance(context.github_repo, str)
        assert isinstance(context.github_token, str)
        assert hasattr(context, "app_name")
        assert hasattr(context, "github_repo")
        assert hasattr(context, "github_token")

    def test_context_is_singleton(self):
        """Test that context is a module-level singleton instance."""
        # Arrange & Act
        from github_pm.context import context as context1
        from github_pm.context import context as context2

        # Assert
        assert context1 is context2
        assert id(context1) == id(context2)
