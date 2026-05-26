from __future__ import annotations

import ipaddress
import json
import logging
import socket
import sys
import time
from datetime import datetime
from collections.abc import Iterable
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

PRIVATE_URL_PATTERNS = [
    "http://localhost/*",
    "https://localhost/*",
    "http://127.*",
    "https://127.*",
    "http://0.*",
    "https://0.*",
    "http://10.*",
    "https://10.*",
    "http://169.254.*",
    "https://169.254.*",
    "http://172.16.*",
    "https://172.16.*",
    "http://172.17.*",
    "https://172.17.*",
    "http://172.18.*",
    "https://172.18.*",
    "http://172.19.*",
    "https://172.19.*",
    "http://172.20.*",
    "https://172.20.*",
    "http://172.21.*",
    "https://172.21.*",
    "http://172.22.*",
    "https://172.22.*",
    "http://172.23.*",
    "https://172.23.*",
    "http://172.24.*",
    "https://172.24.*",
    "http://172.25.*",
    "https://172.25.*",
    "http://172.26.*",
    "https://172.26.*",
    "http://172.27.*",
    "https://172.27.*",
    "http://172.28.*",
    "https://172.28.*",
    "http://172.29.*",
    "https://172.29.*",
    "http://172.30.*",
    "https://172.30.*",
    "http://172.31.*",
    "https://172.31.*",
    "http://192.168.*",
    "https://192.168.*",
    "http://[::1]/*",
    "https://[::1]/*",
]


class Settings(BaseSettings):
    environment: str = "local"
    log_level: str = "INFO"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_exchange: str = "homeoffer.browse"
    rabbitmq_dead_letter_exchange: str = "homeoffer.browse.dlx"
    rabbitmq_queue: str = "browse.jobs"
    rabbitmq_routing_key: str = "browse"
    rabbitmq_prefetch: int = 1
    allowed_browse_host_suffix: str = "avito.ru"
    resolve_browse_dns: bool = True

    selenium_remote_url: str = "http://selenium-hub:4444/wd/hub"
    selenium_wait_timeout_seconds: int = 20
    selenium_page_load_timeout_seconds: int = 45
    selenium_startup_timeout_seconds: int = 90

    html_log_chunk_size: int = 16000
    requeue_on_failure: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context: object) -> None:
        if self.environment.lower() in {"local", "test"}:
            return

        rabbitmq_url = urlparse(self.rabbitmq_url)
        if rabbitmq_url.username == "guest" and rabbitmq_url.password == "guest":
            raise ValueError("RABBITMQ_URL must not use guest:guest credentials outside local/test")


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


def resolve_addresses(host: str, port: int) -> set[str]:
    addresses: set[str] = set()
    for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        addresses.add(result[4][0])
    return addresses


def is_public_ip_address(address: str) -> bool:
    try:
        ip_address = ipaddress.ip_address(address)
    except ValueError:
        return False

    return not (
        ip_address.is_loopback
        or ip_address.is_private
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_reserved
        or ip_address.is_unspecified
    )


def assert_allowed_browse_url(url: str, allowed_host_suffix: str, *, resolve_dns: bool = False) -> None:
    try:
        parsed_url = urlparse(url)
        port = parsed_url.port
    except ValueError as error:
        raise BrowseUrlRejected("invalid URL") from error

    if parsed_url.scheme not in {"http", "https"}:
        raise BrowseUrlRejected("unsupported URL scheme")
    if parsed_url.username or parsed_url.password:
        raise BrowseUrlRejected("URL credentials are not allowed")
    if not parsed_url.hostname:
        raise BrowseUrlRejected("URL host is required")
    if port and port not in {80, 443}:
        raise BrowseUrlRejected("only default http/https ports are allowed")

    host = parsed_url.hostname.rstrip(".").lower()
    allowed_suffix = allowed_host_suffix.lower().lstrip(".")
    if host != allowed_suffix and not host.endswith(f".{allowed_suffix}"):
        raise BrowseUrlRejected("only Avito URLs are allowed")

    if resolve_dns:
        effective_port = port or (443 if parsed_url.scheme == "https" else 80)
        try:
            resolved_addresses: Iterable[str] = resolve_addresses(host, effective_port)
        except OSError as error:
            raise BrowseUrlRejected("URL host cannot be resolved") from error

        resolved_addresses = set(resolved_addresses)
        if not resolved_addresses:
            raise BrowseUrlRejected("URL host cannot be resolved")

        if any(not is_public_ip_address(address) for address in resolved_addresses):
            raise BrowseUrlRejected("URL host resolves to a non-public address")


def configure_network_guards(driver: webdriver.Remote) -> None:
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": PRIVATE_URL_PATTERNS})
    except Exception as error:
        raise BrowseUrlRejected(f"failed to configure browser network guard: {error}") from error


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
        configure_network_guards(driver)
        logger.info("browse.started job_id=%s url=%s", job.job_id, job.url)
        driver.get(job.url)
        WebDriverWait(driver, settings.selenium_wait_timeout_seconds).until(
            lambda current_driver: current_driver.execute_script("return document.readyState")
            in {"interactive", "complete"},
        )
        assert_allowed_browse_url(
            driver.current_url,
            settings.allowed_browse_host_suffix,
            resolve_dns=settings.resolve_browse_dns,
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
            assert_allowed_browse_url(
                job.url,
                settings.allowed_browse_host_suffix,
                resolve_dns=settings.resolve_browse_dns,
            )
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
