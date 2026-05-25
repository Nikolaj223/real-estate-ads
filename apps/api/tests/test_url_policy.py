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
