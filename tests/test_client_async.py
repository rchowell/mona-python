import httpx
import pytest
import respx

from mona import AsyncClient, DatabaseRecord, NotFoundError, Result

BASE = "https://api.test"


def make_client(**kwargs: object) -> AsyncClient:
    return AsyncClient(api_key="mk-secret", base_url=BASE, **kwargs)


@respx.mock
async def test_create_database_async() -> None:
    route = respx.put(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(200, json={"name": "my-app"}),
    )
    async with make_client() as client:
        db = await client.databases.create(name="my-app")

    assert isinstance(db, DatabaseRecord)
    assert db.name == "my-app"
    assert route.calls.last.request.headers["authorization"] == "Bearer mk-secret"


@respx.mock
async def test_list_databases_async() -> None:
    respx.post(f"{BASE}/v1/databases").mock(
        return_value=httpx.Response(200, json={"databases": [{"name": "a"}]}),
    )
    async with make_client() as client:
        dbs = await client.databases.list()
    assert [d.name for d in dbs] == ["a"]


@respx.mock
async def test_delete_async_returns_none() -> None:
    respx.delete(f"{BASE}/v1/databases/my-app").mock(return_value=httpx.Response(204))
    async with make_client() as client:
        assert await client.databases.delete("my-app") is None


@respx.mock
async def test_query_async_data_plane() -> None:
    respx.post("https://edge.test/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [42], "rows_affected": 1}]},
        ),
    )
    async with make_client(query_base_url="https://edge.test") as client:
        result = await client.database("my-app").query("SELECT 42")
    assert isinstance(result, Result)
    assert result.rows == [42]
    assert result.rows_affected == 1


@respx.mock
async def test_error_raises_typed_exception_async() -> None:
    respx.get(f"{BASE}/v1/databases/missing/metadata").mock(
        return_value=httpx.Response(404, json={"code": "not_found", "message": "nope"}),
    )
    async with make_client() as client:
        with pytest.raises(NotFoundError):
            await client.databases.get("missing")
