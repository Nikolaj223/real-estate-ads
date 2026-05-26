import pytest

from app.core.url_policy import BrowseUrlRejected, assert_allowed_browse_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.avito.ru/samara/kvartiry/123",
        "https://m.avito.ru/moskva/kvartiry/123",
        "http://avito.ru/realty/123",
    ],
)
def test_allows_avito_hosts(url: str) -> None:
    assert_allowed_browse_url(url, "avito.ru")


@pytest.mark.parametrize(
    "url",
    [
        "https://evil-avito.ru/samara/kvartiry/123",
        "https://avito.ru.evil.example/samara/kvartiry/123",
        "ftp://www.avito.ru/samara/kvartiry/123",
        "https://user:pass@www.avito.ru/samara/kvartiry/123",
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(BrowseUrlRejected):
        assert_allowed_browse_url(url, "avito.ru")


def test_rejects_non_default_ports() -> None:
    with pytest.raises(BrowseUrlRejected):
        assert_allowed_browse_url("https://www.avito.ru:4443/samara/kvartiry/123", "avito.ru")


def test_rejects_allowed_host_when_dns_resolves_to_private_address() -> None:
    with pytest.raises(BrowseUrlRejected):
        assert_allowed_browse_url(
            "https://www.avito.ru/samara/kvartiry/123",
            "avito.ru",
            resolve_dns=True,
            resolver=lambda _host, _port: {"127.0.0.1"},
        )


def test_allows_allowed_host_when_dns_resolves_to_public_address() -> None:
    assert_allowed_browse_url(
        "https://www.avito.ru/samara/kvartiry/123",
        "avito.ru",
        resolve_dns=True,
        resolver=lambda _host, _port: {"93.184.216.34"},
    )
