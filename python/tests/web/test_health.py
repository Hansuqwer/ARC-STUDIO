import pytest

pytestmark = pytest.mark.asyncio


async def test_health_returns_ok(client):
    for path in ("/health", "/healthz", "/api/health"):
        r = await client.get(path)
        if r.status_code == 404:
            continue
        assert r.status_code == 200
        body = await r.json()
        assert isinstance(body, dict)
        return
    pytest.skip("no health endpoint mounted")
