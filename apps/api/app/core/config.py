from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HomeOffer Browse API"
    environment: str = "local"
    log_level: str = "INFO"

    rabbitmq_url: str = Field(default="amqp://guest:guest@rabbitmq:5672/")
    rabbitmq_exchange: str = "homeoffer.browse"
    rabbitmq_dead_letter_exchange: str = "homeoffer.browse.dlx"
    rabbitmq_queue: str = "browse.jobs"
    rabbitmq_routing_key: str = "browse"

    allowed_browse_host_suffix: str = "avito.ru"
    idempotency_salt: str = "local-development-salt"
    idempotency_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
