import httpx
import pytest
import respx

from mona import Client, ConflictError, DatabaseRecord, NotFoundError, Result

BASE = "https://api.test"


def make_client(**kwargs: object) -> Client:
    return Client(api_key="mk-secret", base_url=BASE, **kwargs)


@respx.mock
def test_create_database_puts_body_and_auth_header() -> None:
    route = respx.put(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(200, json={"name": "my-app", "region": "us-east"}),
    )
    with make_client() as client:
        db = client.databases.create(name="my-app", region="us-east")

    assert isinstance(db, DatabaseRecord)
    assert db.name == "my-app"
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer mk-secret"
    assert request.read() == b'{"region":"us-east"}'


@respx.mock
def test_list_databases_unwraps_envelope() -> None:
    respx.post(f"{BASE}/v1/databases").mock(
        return_value=httpx.Response(
            200,
            json={"databases": [{"name": "a"}, {"name": "b", "region": "eu"}]},
        ),
    )
    with make_client() as client:
        page = client.databases.list()

    assert [d.name for d in page] == ["a", "b"]
    assert page[1].region == "eu"


@respx.mock
def test_list_databases_filters_by_prefix() -> None:
    respx.post(f"{BASE}/v1/databases").mock(
        return_value=httpx.Response(
            200,
            json={
                "databases": [
                    {"name": "app-a"},
                    {"name": "app-b"},
                    {"name": "other"},
                ],
            },
        ),
    )
    with make_client() as client:
        page = client.databases.list(prefix="app-")

    assert [d.name for d in page] == ["app-a", "app-b"]


@respx.mock
def test_get_database_hits_metadata_path() -> None:
    route = respx.get(f"{BASE}/v1/databases/my-app/metadata").mock(
        return_value=httpx.Response(200, json={"name": "my-app"}),
    )
    with make_client() as client:
        db = client.databases.get("my-app")

    assert db.name == "my-app"
    assert route.called


@respx.mock
def test_delete_database_returns_none_on_204() -> None:
    route = respx.delete(f"{BASE}/v1/databases/my-app").mock(return_value=httpx.Response(204))
    with make_client() as client:
        assert client.databases.delete("my-app") is None
    assert route.called


@respx.mock
def test_resolve_instance_hits_instance_path() -> None:
    route = respx.get(f"{BASE}/v1/databases/my-app/instance").mock(
        return_value=httpx.Response(200, json={"instance_id": "inst-123"}),
    )
    with make_client() as client:
        resolved = client.databases.resolve_instance("my-app")

    assert resolved.instance_id == "inst-123"
    assert route.called


@respx.mock
def test_query_hits_data_plane_and_parses_rows() -> None:
    route = respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [1], "rows_affected": 0}]},
        ),
    )
    with make_client() as client:
        result = client.databases.query("my-app", "SELECT 1")

    assert isinstance(result, Result)
    assert result.rows == [1]
    assert result.rows_affected == 0
    assert route.calls.last.request.read() == b'{"statements":[{"sql":"SELECT 1"}]}'


@respx.mock
def test_query_uses_query_base_url_override() -> None:
    respx.post("https://edge.test/v1/databases/my-app").mock(
        return_value=httpx.Response(200, json={"results": [{"rows": [], "rows_affected": 0}]}),
    )
    with make_client(query_base_url="https://edge.test") as client:
        result = client.databases.query("my-app", "SELECT 1")
    assert result.rows == []


@respx.mock
def test_json_error_raises_typed_exception() -> None:
    respx.get(f"{BASE}/v1/databases/missing/metadata").mock(
        return_value=httpx.Response(404, json={"code": "not_found", "message": "nope"}),
    )
    with make_client() as client, pytest.raises(NotFoundError) as exc:
        client.databases.get("missing")
    assert exc.value.code == "not_found"


@respx.mock
def test_conflict_on_create_raises() -> None:
    respx.put(f"{BASE}/v1/databases/dup").mock(
        return_value=httpx.Response(409, json={"code": "conflict", "message": "exists"}),
    )
    with make_client() as client, pytest.raises(ConflictError):
        client.databases.create(name="dup")


def test_api_key_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONA_API_KEY", "mk-env")
    monkeypatch.setenv("MONA_BASE_URL", BASE)
    with respx.mock:
        route = respx.post(f"{BASE}/v1/databases").mock(
            return_value=httpx.Response(200, json={"databases": []}),
        )
        with Client() as client:
            client.databases.list()
    assert route.calls.last.request.headers["authorization"] == "Bearer mk-env"


def test_missing_api_key_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MONA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key"):
        Client(base_url=BASE)
