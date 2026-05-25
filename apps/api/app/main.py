from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from app.api.browse import router as browse_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.services.idempotency import InMemoryIdempotencyStore
from app.services.rabbitmq import RabbitPublisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    app.state.settings = settings
    app.state.idempotency_store = InMemoryIdempotencyStore(settings.idempotency_ttl_seconds)
    app.state.publisher = RabbitPublisher(settings)
    await app.state.publisher.connect()

    try:
        yield
    finally:
        await app.state.publisher.close()


def create_app(enable_lifespan: bool = True) -> FastAPI:
    app = FastAPI(
        title="HomeOffer Browse API",
        version="0.1.0",
        lifespan=lifespan if enable_lifespan else None,
    )

    app.include_router(browse_router)

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready(response: Response) -> dict[str, str]:
        publisher = getattr(app.state, "publisher", None)
        if publisher and publisher.is_ready():
            return {"status": "ok"}

        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}

    return app


app = create_app()
