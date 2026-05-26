import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_allows_default_idempotency_salt_in_local_environment() -> None:
    Settings(environment="local", idempotency_salt="local-development-salt")


def test_rejects_default_idempotency_salt_outside_local_environment() -> None:
    with pytest.raises((ValueError, ValidationError)):
        Settings(environment="production", idempotency_salt="local-development-salt")


def test_rejects_default_rabbitmq_credentials_outside_local_environment() -> None:
    with pytest.raises((ValueError, ValidationError)):
        Settings(
            environment="production",
            idempotency_salt="strong-production-salt",
            rabbitmq_url="amqp://guest:guest@rabbitmq:5672/",
        )
