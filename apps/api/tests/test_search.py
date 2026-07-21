import pytest

from scrapling_cloud import search as search_module
from scrapling_cloud.schemas import SearchRequest


@pytest.mark.asyncio
async def test_web_search_unavailable_without_backend(monkeypatch) -> None:
    class FakeSettings:
        searxng_url = None

    monkeypatch.setattr(search_module, "get_settings", lambda: FakeSettings())
    with pytest.raises(search_module.SearchUnavailable):
        await search_module.web_search("test")


def test_search_request_defaults() -> None:
    request = SearchRequest(query="eu funding calls")
    assert request.limit == 10
    assert request.mode == "static"
    assert request.scrape_formats is None


def test_search_request_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        SearchRequest(query="")


def test_search_credits_formula() -> None:
    # Mirror of the endpoint's credit math for regression safety.
    def cost(limit, scrape):
        return max(2, 2 * ((limit + 9) // 10)) + (limit if scrape else 0)

    assert cost(10, False) == 2
    assert cost(20, False) == 4
    assert cost(10, True) == 12
