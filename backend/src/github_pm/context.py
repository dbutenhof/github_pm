from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_sdlc_label_csv(value: object) -> frozenset[str]:
    """Parse comma-separated label names into a lowercase set."""
    if isinstance(value, frozenset):
        return value
    if not isinstance(value, str):
        return frozenset()
    return frozenset(part.strip().lower() for part in value.split(",") if part.strip())


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
    # SDLC KPIs: classify PRs (comma-separated; matched case-insensitively on label name).
    # Stored as str so empty .env values do not break settings parsing. Use
    # sdlc_metrics._parse_sdlc_label_csv for set semantics.
    # Precedence when multiple match: bug fix > docs > feature (see sdlc_metrics.classify_pr_type).
    sdlc_feature_labels: Annotated[str, Field(default="enhancement,feature")]
    sdlc_bug_labels: Annotated[str, Field(default="bug")]
    sdlc_docs_labels: Annotated[str, Field(default="documentation")]
    sdlc_escape_label: Annotated[str, Field(default="escape")]


context = Settings()
