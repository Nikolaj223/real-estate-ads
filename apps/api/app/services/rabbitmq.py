import json
import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import Settings
from app.schemas.browse import BrowseJob

logger = logging.getLogger(__name__)


class RabbitPublisher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractRobustExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._settings.rabbitmq_url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=10)

        dead_letter_exchange = await self._channel.declare_exchange(
            self._settings.rabbitmq_dead_letter_exchange,
            ExchangeType.DIRECT,
            durable=True,
        )
        dead_letter_queue = await self._channel.declare_queue(
            f"{self._settings.rabbitmq_queue}.dead",
            durable=True,
        )
        await dead_letter_queue.bind(
            dead_letter_exchange,
            routing_key=self._settings.rabbitmq_routing_key,
        )

        self._exchange = await self._channel.declare_exchange(
            self._settings.rabbitmq_exchange,
            ExchangeType.DIRECT,
            durable=True,
        )
        queue = await self._channel.declare_queue(
            self._settings.rabbitmq_queue,
            durable=True,
            arguments={"x-dead-letter-exchange": dead_letter_exchange.name},
        )
        await queue.bind(self._exchange, routing_key=self._settings.rabbitmq_routing_key)
        logger.info("rabbitmq.publisher.ready queue=%s", self._settings.rabbitmq_queue)

    async def publish_browse(self, job: BrowseJob) -> None:
        if not self._exchange:
            raise RuntimeError("RabbitMQ publisher is not connected")

        message = Message(
            body=json.dumps(job.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=job.job_id,
            message_id=job.job_id,
            headers={"job_id": job.job_id},
        )
        await self._exchange.publish(message, routing_key=self._settings.rabbitmq_routing_key)
        logger.info("browse.job.published job_id=%s url=%s", job.job_id, job.url)

    def is_ready(self) -> bool:
        return bool(
            self._connection
            and not self._connection.is_closed
            and self._channel
            and not self._channel.is_closed
            and self._exchange
        )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
