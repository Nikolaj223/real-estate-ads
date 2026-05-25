from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from typing import Iterator
from urllib.parse import urlparse
from urllib.request import urlopen

import pika
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger("browse_worker")


class Settings(BaseSettings):
    log_level: str = "INFO"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_exchange: str = "homeoffer.browse"
    rabbitmq_dead_letter_exchange: str = "homeoffer.browse.dlx"
    rabbitmq_queue: str = "browse.jobs"
    rabbitmq_routing_key: str = "browse"
    rabbitmq_prefetch: int = 1
    allowed_browse_host_suffix: str = "avito.ru"

    selenium_remote_url: str = "http://selenium-hub:4444/wd/hub"
    selenium_wait_timeout_seconds: int = 20
    selenium_page_load_timeout_seconds: int = 45
    selenium_startup_timeout_seconds: int = 90

    html_log_chunk_size: int = 16000
    requeue_on_failure: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class BrowseJob(BaseModel):
    job_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    requested_at: datetime
    idempotency_key: str | None = None


class BrowseUrlRejected(ValueError):
    pass


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )


def selenium_status_url(remote_url: str) -> str:
    base_url = remote_url.rstrip("/")
    if base_url.endswith("/wd/hub"):
        base_url = base_url[: -len("/wd/hub")]
    return f"{base_url}/status"


def assert_allowed_browse_url(url: str, allowed_host_suffix: str) -> None:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise BrowseUrlRejected("unsupported URL scheme")
    if parsed_url.username or parsed_url.password:
        raise BrowseUrlRejected("URL credentials are not allowed")
    if not parsed_url.hostname:
        raise BrowseUrlRejected("URL host is required")

    host = parsed_url.hostname.rstrip(".").lower()
    allowed_suffix = allowed_host_suffix.lower().lstrip(".")
    if host != allowed_suffix and not host.endswith(f".{allowed_suffix}"):
        raise BrowseUrlRejected("only Avito URLs are allowed")


def wait_for_selenium(settings: Settings) -> None:
    deadline = time.monotonic() + settings.selenium_startup_timeout_seconds
    status_url = selenium_status_url(settings.selenium_remote_url)

    while time.monotonic() < deadline:
        try:
            with urlopen(status_url, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("value", {}).get("ready") is True:
                    logger.info("selenium.ready url=%s", status_url)
                    return
        except Exception as error:
            logger.info("selenium.waiting url=%s error=%s", status_url, error)
        time.sleep(3)

    raise RuntimeError("Selenium Grid did not become ready in time")


def build_driver(settings: Settings) -> webdriver.Remote:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,1200")
    options.set_capability("pageLoadStrategy", "eager")

    driver = webdriver.Remote(command_executor=settings.selenium_remote_url, options=options)
    driver.set_page_load_timeout(settings.selenium_page_load_timeout_seconds)
    return driver


def iter_chunks(value: str, chunk_size: int) -> Iterator[str]:
    if chunk_size <= 0:
        yield value
        return

    for index in range(0, len(value), chunk_size):
        yield value[index : index + chunk_size]


def render_and_log_html(job: BrowseJob, settings: Settings) -> None:
    driver: webdriver.Remote | None = None
    try:
        driver = build_driver(settings)
        logger.info("browse.started job_id=%s url=%s", job.job_id, job.url)
        driver.get(job.url)
        WebDriverWait(driver, settings.selenium_wait_timeout_seconds).until(
            lambda current_driver: current_driver.execute_script("return document.readyState")
            in {"interactive", "complete"},
        )
        html = driver.page_source
        logger.info("browse.html.begin job_id=%s url=%s bytes=%s", job.job_id, job.url, len(html.encode("utf-8")))
        for part_index, chunk in enumerate(iter_chunks(html, settings.html_log_chunk_size), start=1):
            logger.info("browse.html.chunk job_id=%s part=%s\n%s", job.job_id, part_index, chunk)
        logger.info("browse.html.end job_id=%s", job.job_id)
    finally:
        if driver:
            driver.quit()


def declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel, settings: Settings) -> None:
    channel.exchange_declare(exchange=settings.rabbitmq_dead_letter_exchange, exchange_type="direct", durable=True)
    channel.queue_declare(queue=f"{settings.rabbitmq_queue}.dead", durable=True)
    channel.queue_bind(
        queue=f"{settings.rabbitmq_queue}.dead",
        exchange=settings.rabbitmq_dead_letter_exchange,
        routing_key=settings.rabbitmq_routing_key,
    )

    channel.exchange_declare(exchange=settings.rabbitmq_exchange, exchange_type="direct", durable=True)
    channel.queue_declare(
        queue=settings.rabbitmq_queue,
        durable=True,
        arguments={"x-dead-letter-exchange": settings.rabbitmq_dead_letter_exchange},
    )
    channel.queue_bind(
        queue=settings.rabbitmq_queue,
        exchange=settings.rabbitmq_exchange,
        routing_key=settings.rabbitmq_routing_key,
    )
    channel.basic_qos(prefetch_count=settings.rabbitmq_prefetch)


def consume(settings: Settings) -> None:
    parameters = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    declare_topology(channel, settings)

    def handle_message(
        channel_: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes,
    ) -> None:
        try:
            job = BrowseJob.model_validate_json(body)
            assert_allowed_browse_url(job.url, settings.allowed_browse_host_suffix)
            render_and_log_html(job, settings)
        except ValidationError as error:
            logger.exception("browse.invalid_message delivery_tag=%s error=%s", method.delivery_tag, error)
            channel_.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        except BrowseUrlRejected as error:
            logger.exception("browse.rejected_url delivery_tag=%s error=%s", method.delivery_tag, error)
            channel_.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        except (WebDriverException, Exception) as error:
            logger.exception(
                "browse.failed delivery_tag=%s message_id=%s error=%s",
                method.delivery_tag,
                properties.message_id,
                error,
            )
            channel_.basic_nack(delivery_tag=method.delivery_tag, requeue=settings.requeue_on_failure)
            return

        channel_.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("browse.acknowledged job_id=%s", job.job_id)

    channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=handle_message)
    logger.info("worker.consuming queue=%s", settings.rabbitmq_queue)
    channel.start_consuming()


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    wait_for_selenium(settings)

    while True:
        try:
            consume(settings)
        except pika.exceptions.AMQPConnectionError as error:
            logger.warning("rabbitmq.connection_lost error=%s", error)
            time.sleep(5)


if __name__ == "__main__":
    main()
