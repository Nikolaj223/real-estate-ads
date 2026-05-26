from functools import lru_cache
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    unsafe_salts: ClassVar[set[str]] = {
        "local-development-salt",
        "change-me-in-production",
        "development-only-change-me",
    }

    app_name: str = "HomeOffer Browse API"
    environment: str = "local"
    log_level: str = "INFO"

    rabbitmq_url: str = Field(default="amqp://guest:guest@rabbitmq:5672/")
    rabbitmq_exchange: str = "homeoffer.browse"
    rabbitmq_dead_letter_exchange: str = "homeoffer.browse.dlx"
    rabbitmq_queue: str = "browse.jobs"
    rabbitmq_routing_key: str = "browse"

    allowed_browse_host_suffix: str = "avito.ru"
    resolve_browse_dns: bool = True
    browse_rate_limit_per_minute: int = 60
    idempotency_salt: str = "local-development-salt"
    idempotency_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_post_init(self, __context: object) -> None:
        if self.environment.lower() in {"local", "test"}:
            return

        if self.idempotency_salt in self.unsafe_salts:
            raise ValueError("IDEMPOTENCY_SALT must be set to a strong non-default value")

        rabbitmq_url = urlparse(self.rabbitmq_url)
        if rabbitmq_url.username == "guest" and rabbitmq_url.password == "guest":
            raise ValueError("RABBITMQ_URL must not use guest:guest credentials outside local/test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
