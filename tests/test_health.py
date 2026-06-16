import httpx
import respx

from mona import AsyncClient, Client, HealthStatus

BASE = "https://api.test"


@respx.mock
def test_health_sync() -> None:
    respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok", "service": "control"}),
    )
    with Client(api_key="k", base_url=BASE) as client:
        health = client.health()
    assert isinstance(health, HealthStatus)
    assert health.status == "ok"
    assert health.service == "control"


@respx.mock
async def test_health_async() -> None:
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={"status": "draining"}))
    async with AsyncClient(api_key="k", base_url=BASE) as client:
        health = await client.health()
    assert health.status == "draining"
    assert health.service is None
