from urllib.parse import urlparse


class BrowseUrlRejected(ValueError):
    pass


def assert_allowed_browse_url(url: str, allowed_host_suffix: str) -> None:
    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"}:
        raise BrowseUrlRejected("Поддерживаются только http и https ссылки")

    if parsed_url.username or parsed_url.password:
        raise BrowseUrlRejected("URL не должен содержать учетные данные")

    if not parsed_url.hostname:
        raise BrowseUrlRejected("URL должен содержать host")

    host = parsed_url.hostname.rstrip(".").lower()
    allowed_suffix = allowed_host_suffix.lower().lstrip(".")

    if host != allowed_suffix and not host.endswith(f".{allowed_suffix}"):
        raise BrowseUrlRejected("Можно сканировать только объявления на Avito")
