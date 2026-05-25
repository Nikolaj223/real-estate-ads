from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.config import Settings
from app.core.url_policy import BrowseUrlRejected, assert_allowed_browse_url
from app.schemas.browse import BrowseAccepted, BrowseJob, BrowseRequest
from app.services.idempotency import InMemoryIdempotencyStore, build_job_id
from app.services.rabbitmq import RabbitPublisher

router = APIRouter()


def get_request_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_publisher(request: Request) -> RabbitPublisher:
    return request.app.state.publisher


def get_idempotency_store(request: Request) -> InMemoryIdempotencyStore:
    return request.app.state.idempotency_store


@router.post("/browse", response_model=BrowseAccepted, status_code=status.HTTP_202_ACCEPTED)
async def browse(
    payload: BrowseRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    settings: Settings = Depends(get_request_settings),
    publisher: RabbitPublisher = Depends(get_publisher),
    idempotency_store: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> BrowseAccepted:
    url = str(payload.url)
    try:
        assert_allowed_browse_url(url, settings.allowed_browse_host_suffix)
    except BrowseUrlRejected as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    job_id = build_job_id(url=url, idempotency_key=idempotency_key, salt=settings.idempotency_salt)
    _, created = idempotency_store.reserve(job_id)
    if not created:
        return BrowseAccepted(jobId=job_id, status="duplicate", deduplicated=True)

    job = BrowseJob(
        job_id=job_id,
        url=url,
        requested_at=datetime.now(UTC),
        idempotency_key=idempotency_key,
    )

    try:
        await publisher.publish_browse(job)
    except Exception as error:
        idempotency_store.forget(job_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Очередь временно недоступна",
        ) from error

    return BrowseAccepted(jobId=job_id, status="queued", deduplicated=False)
