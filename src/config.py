"""Central, typed configuration.

Everything is read from environment variables (or a .env file). Nested settings use
the `__` delimiter, e.g. OPENSEARCH__HOST -> settings.opensearch.host.

Inside Docker, services address each other by service name (postgres, opensearch, ...).
From your host machine (curl, notebooks) use localhost. The compose file sets the
in-container values via .env; the defaults below are host-friendly for local scripts.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenSearchSettings(BaseSettings):
    host: str = "http://localhost:9200"
    index: str = "arxiv-papers"


class OllamaSettings(BaseSettings):
    host: str = "http://localhost:11434"
    model: str = "llama3.2:3b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Core services
    database_url: str
    redis_url: str

    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)

    # Optional keys, needed from later stages onward
    jina_api_key: str | None = None
    langfuse__public_key: str | None = None
    langfuse__secret_key: str | None = None
    telegram__bot_token: str | None = None

    arxiv__feed: str | None = None

@lru_cache
def get_settings() -> Settings:
    """Cached singleton so config is parsed once per process."""
    return Settings()
