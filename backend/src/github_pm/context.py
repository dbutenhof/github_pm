import secrets
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        validate_default=True,
        case_sensitive=False,
        env_file=".env",
    )
    app_name: Annotated[str, Field(default="GitHub Project Manager")]
    github_repo: Annotated[str, Field(default="vllm-project/guidellm")]
    github_client_id: Annotated[str, Field(default="")]
    github_client_secret: Annotated[str, Field(default="")]
    github_oauth_callback_url: Annotated[
        str, Field(default="http://localhost:8000/api/v1/auth/callback")
    ]
    session_secret: Annotated[
        str,
        Field(
            default_factory=lambda: secrets.token_urlsafe(32),
            description="Secret key for session encryption",
        ),
    ]


context = Settings()
