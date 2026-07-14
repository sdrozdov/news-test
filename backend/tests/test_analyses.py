ARTICLE = {
    "title": "Renewable energy adoption hits record high",
    "description": "Solar and wind capacity grew sharply this year.",
    "content": "Global renewable capacity additions set a new record...",
    "url": "https://example.com/renewables",
    "source_name": "Example News",
}


async def _create(client, article=ARTICLE):
    return await client.post("/api/analyses", json={"article": article})


async def test_analyze_creates_result(client):
    response = await _create(client)
    assert response.status_code == 201
    body = response.json()
    assert body["summary"]
    assert body["sentiment"] == "positive"
    assert body["sentiment_score"] == 0.7
    assert body["model"] == "fake-model"
    assert body["article"]["url"] == ARTICLE["url"]
    assert body["article"]["title"] == ARTICLE["title"]


async def test_list_and_get(client):
    created = (await _create(client)).json()
    listed = await client.get("/api/analyses")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = await client.get(f"/api/analyses/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


async def test_reanalyzing_same_url_is_idempotent(client):
    await _create(client)
    await _create(client)  # same URL again
    listed = await client.get("/api/analyses")
    assert len(listed.json()) == 1  # updated in place, not duplicated


async def test_delete(client):
    created = (await _create(client)).json()
    deleted = await client.delete(f"/api/analyses/{created['id']}")
    assert deleted.status_code == 204

    assert (await client.get("/api/analyses")).json() == []
    assert (await client.get(f"/api/analyses/{created['id']}")).status_code == 404


async def test_get_missing_returns_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/analyses/{missing}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_negative_sentiment_article(client):
    article = {**ARTICLE, "title": "Markets tumble amid uncertainty", "url": "https://example.com/markets"}
    body = (await _create(client, article)).json()
    assert body["sentiment"] == "negative"
    assert body["sentiment_score"] < 0


async def test_reanalyze_returns_200_not_201(client):
    first = await _create(client)
    assert first.status_code == 201
    second = await _create(client)  # same URL
    assert second.status_code == 200
    assert second.headers["location"] == f"/api/analyses/{second.json()['id']}"


async def test_non_http_url_rejected(client):
    bad = {**ARTICLE, "url": "javascript:alert(1)"}
    response = await client.post("/api/analyses", json={"article": bad})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_oversized_title_rejected(client):
    big = {**ARTICLE, "title": "x" * 2000}
    response = await client.post("/api/analyses", json={"article": big})
    assert response.status_code == 422


async def test_ai_error_maps_to_status(app, client):
    from app.dependencies import get_ai_client
    from app.errors import AIServiceError

    class RaisingAIClient:
        model = "x"

        async def analyze(self, article):
            raise AIServiceError("provider down")

    app.dependency_overrides[get_ai_client] = lambda: RaisingAIClient()
    response = await _create(client)
    assert response.status_code == 502
    assert response.json()["code"] == "ai_service_error"


async def test_results_are_scoped_per_user(app, client):
    """Each user only sees their own results; the same URL is independent per user."""
    from app.dependencies import get_current_user
    from app.schemas.user import UserRead

    await _create(client)  # created as the default dev user
    assert len((await client.get("/api/analyses")).json()) == 1

    # Switch identity: user-b sees none of the dev user's results.
    app.dependency_overrides[get_current_user] = lambda: UserRead(id="user-b")
    assert (await client.get("/api/analyses")).json() == []

    # user-b can analyze the same URL independently (its own copy).
    created = await _create(client)
    assert created.status_code == 201
    assert len((await client.get("/api/analyses")).json()) == 1
