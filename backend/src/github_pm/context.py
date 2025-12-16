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
    github_token: Annotated[str, Field(default="")]


context = Settings()
