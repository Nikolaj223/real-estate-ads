from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.browse import BrowseJob
from app.services.idempotency import InMemoryIdempotencyStore
from app.services.rate_limiter import InMemoryRateLimiter


class FakePublisher:
    def __init__(self) -> None:
        self.jobs: list[BrowseJob] = []
        self.should_fail = False

    async def publish_browse(self, job: BrowseJob) -> None:
        if self.should_fail:
            raise RuntimeError("RabbitMQ is unavailable")

        self.jobs.append(job)

    def is_ready(self) -> bool:
        return True


def build_client() -> tuple[TestClient, FakePublisher]:
    app = create_app(enable_lifespan=False)
    publisher = FakePublisher()
    app.state.settings = Settings(
        environment="test",
        idempotency_salt="test",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        resolve_browse_dns=False,
    )
    app.state.publisher = publisher
    app.state.idempotency_store = InMemoryIdempotencyStore(ttl_seconds=60)
    app.state.rate_limiter = InMemoryRateLimiter(limit=100)
    return TestClient(app), publisher


def test_browse_queues_avito_url() -> None:
    client, publisher = build_client()

    response = client.post("/browse", json={"url": "https://www.avito.ru/samara/kvartiry/123"})

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["deduplicated"] is False
    assert len(publisher.jobs) == 1
    assert publisher.jobs[0].url == "https://www.avito.ru/samara/kvartiry/123"


def test_browse_deduplicates_same_url() -> None:
    client, publisher = build_client()
    payload = {"url": "https://www.avito.ru/samara/kvartiry/123"}

    first_response = client.post("/browse", json=payload)
    second_response = client.post("/browse", json=payload)

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.json()["status"] == "duplicate"
    assert second_response.json()["deduplicated"] is True
    assert first_response.json()["jobId"] == second_response.json()["jobId"]
    assert len(publisher.jobs) == 1


def test_browse_deduplicates_same_idempotency_key() -> None:
    client, publisher = build_client()
    payload = {"url": "https://www.avito.ru/samara/kvartiry/123"}
    headers = {"Idempotency-Key": "listing-scan-123"}

    first_response = client.post("/browse", json=payload, headers=headers)
    second_response = client.post("/browse", json=payload, headers=headers)

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.json()["status"] == "duplicate"
    assert second_response.json()["deduplicated"] is True
    assert first_response.json()["jobId"] == second_response.json()["jobId"]
    assert len(publisher.jobs) == 1


def test_browse_releases_idempotency_reservation_when_publish_fails() -> None:
    client, publisher = build_client()
    payload = {"url": "https://www.avito.ru/samara/kvartiry/123"}
    publisher.should_fail = True

    failed_response = client.post("/browse", json=payload)

    publisher.should_fail = False
    retry_response = client.post("/browse", json=payload)

    assert failed_response.status_code == 503
    assert retry_response.status_code == 202
    assert retry_response.json()["status"] == "queued"
    assert len(publisher.jobs) == 1


def test_browse_rejects_non_avito_url() -> None:
    client, publisher = build_client()

    response = client.post("/browse", json={"url": "https://example.com/listing"})

    assert response.status_code == 422
    assert len(publisher.jobs) == 0


def test_browse_rate_limits_clients() -> None:
    client, publisher = build_client()
    client.app.state.rate_limiter = InMemoryRateLimiter(limit=1)

    first_response = client.post("/browse", json={"url": "https://www.avito.ru/samara/kvartiry/123"})
    second_response = client.post("/browse", json={"url": "https://www.avito.ru/samara/kvartiry/456"})

    assert first_response.status_code == 202
    assert second_response.status_code == 429
    assert len(publisher.jobs) == 1
