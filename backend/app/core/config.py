"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application configuration sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "kb"
    postgres_password: str = "kb_password_change_me"
    postgres_db: str = "knowledge_base"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index: str = "documents"

    redis_url: str = "redis://redis:6379/0"
    search_cache_ttl: int = 300

    max_upload_mb: int = 20
    chunk_size: int = 1000
    chunk_overlap: int = 100
    upload_dir: str = "/data/uploads"
    log_level: str = "INFO"

    @property
    def database_dsn(self) -> str:
        """Return the async SQLAlchemy DSN for PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def max_upload_bytes(self) -> int:
        """Return the maximum allowed upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
