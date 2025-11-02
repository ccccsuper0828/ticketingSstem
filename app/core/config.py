from functools import lru_cache
from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "dev"
    app_name: str = "Ticketing API"

    # Database connection (supports DB_* and DATABASE_* env names)
    database_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("DB_HOST", "DATABASE_HOST"),
    )
    database_port: int = Field(
        default=3306,
        validation_alias=AliasChoices("DB_PORT", "DATABASE_PORT"),
    )
    database_user: str = Field(
        default="root",
        validation_alias=AliasChoices("DB_USER", "DATABASE_USER"),
    )
    database_password: str = Field(
        default="changeme",
        validation_alias=AliasChoices("DB_PASSWORD", "DATABASE_PASSWORD"),
    )
    database_name: str = Field(
        default="ticketing",
        validation_alias=AliasChoices("DB_NAME", "DATABASE_NAME"),
    )
    database_echo: bool = False

    # Pooling (milliseconds in provided env)
    db_connection_limit: int = Field(
        default=10,
        validation_alias=AliasChoices("DB_CONNECTION_LIMIT", "DATABASE_POOL_SIZE"),
    )
    db_acquire_timeout_ms: int = Field(
        default=60000,
        validation_alias=AliasChoices("DB_ACQUIRE_TIMEOUT", "POOL_ACQUIRE_TIMEOUT"),
    )
    db_timeout_ms: int = Field(
        default=60000,
        validation_alias=AliasChoices("DB_TIMEOUT", "DB_CONNECT_TIMEOUT_MS"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}?charset=utf8mb4"
        )

    @computed_field  # type: ignore[misc]
    @property
    def db_acquire_timeout_seconds(self) -> int:
        return max(1, int(self.db_acquire_timeout_ms // 1000))

    @computed_field  # type: ignore[misc]
    @property
    def db_timeout_seconds(self) -> int:
        return max(1, int(self.db_timeout_ms // 1000))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


