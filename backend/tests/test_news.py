async def test_search_returns_articles(client):
    response = await client.get("/api/news/search", params={"q": "energy"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "energy"
    assert body["count"] == len(body["articles"])
    assert body["articles"][0]["title"]
    assert body["articles"][0]["url"]


async def test_search_respects_max(client):
    response = await client.get("/api/news/search", params={"q": "energy", "max": 1})
    assert response.status_code == 200
    assert response.json()["count"] == 1


async def test_search_requires_query(client):
    response = await client.get("/api/news/search")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_search_upstream_error_maps_to_status(app, client):
    from app.dependencies import get_news_client
    from app.errors import NewsAPIError

    class RaisingNewsClient:
        async def search(self, *args, **kwargs):
            raise NewsAPIError("rate limited", status_code=429)

    app.dependency_overrides[get_news_client] = lambda: RaisingNewsClient()
    response = await client.get("/api/news/search", params={"q": "x"})
    assert response.status_code == 429
    assert response.json()["code"] == "news_api_error"


async def test_top_headlines_returns_articles(client):
    response = await client.get("/api/news/top-headlines", params={"category": "technology"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "technology"
    assert body["count"] == len(body["articles"])
    assert body["articles"][0]["url"]


async def test_top_headlines_page_two_is_empty(client):
    # Page > 1 needs a paid GNews plan; the fake returns nothing, so "load more" ends.
    response = await client.get("/api/news/top-headlines", params={"category": "world", "page": 2})
    assert response.status_code == 200
    assert response.json()["count"] == 0


async def test_extract_returns_reader_content(client):
    response = await client.get("/api/news/extract", params={"url": "https://example.com/x"})
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://example.com/x"
    assert body["blocks"][0] == {"type": "text", "value": "First paragraph."}
    assert any(b["type"] == "image" for b in body["blocks"])
