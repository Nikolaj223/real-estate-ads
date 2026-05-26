import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlparse


class BrowseUrlRejected(ValueError):
    pass


AddressResolver = Callable[[str, int], Iterable[str]]


def default_address_resolver(host: str, port: int) -> set[str]:
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


def assert_allowed_browse_url(
    url: str,
    allowed_host_suffix: str,
    *,
    resolve_dns: bool = False,
    resolver: AddressResolver = default_address_resolver,
) -> None:
    try:
        parsed_url = urlparse(url)
        port = parsed_url.port
    except ValueError as error:
        raise BrowseUrlRejected("Invalid URL") from error

    if parsed_url.scheme not in {"http", "https"}:
        raise BrowseUrlRejected("Only http and https URLs are supported")

    if parsed_url.username or parsed_url.password:
        raise BrowseUrlRejected("URL must not contain credentials")

    if not parsed_url.hostname:
        raise BrowseUrlRejected("URL must contain a host")

    if port and port not in {80, 443}:
        raise BrowseUrlRejected("Only default http/https ports are allowed")

    host = parsed_url.hostname.rstrip(".").lower()
    allowed_suffix = allowed_host_suffix.lower().lstrip(".")

    if host != allowed_suffix and not host.endswith(f".{allowed_suffix}"):
        raise BrowseUrlRejected("Only Avito URLs are allowed")

    effective_port = port or (443 if parsed_url.scheme == "https" else 80)

    if resolve_dns:
        try:
            resolved_addresses = set(resolver(host, effective_port))
        except OSError as error:
            raise BrowseUrlRejected("URL host cannot be resolved") from error

        if not resolved_addresses:
            raise BrowseUrlRejected("URL host cannot be resolved")

        if any(not is_public_ip_address(address) for address in resolved_addresses):
            raise BrowseUrlRejected("URL host resolves to a non-public address")
