"""
Runtime configuration via pydantic settings.
Centralizes tokens for external services.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_token: str | None = None
    gitlab_token: str | None = None
    altmetric_token: str | None = None

    def token_for_host(self, host: Literal["github", "gitlab"]) -> str:
        token = self.github_token if host == "github" else self.gitlab_token
        if not token:
            raise ValueError(
                f"No API token configured for host '{host}'. "
                f"Set {'GITHUB_TOKEN' if host=="github" else 'GITLAB_TOKEN'}."
            )
        return token
