import httpx
import pytest
import respx

from mona import AsyncClient, Client, Database, Result

BASE = "https://api.test"


def make_client(**kwargs: object) -> Client:
    return Client(api_key="mk-secret", base_url=BASE, **kwargs)


def make_async_client(**kwargs: object) -> AsyncClient:
    return AsyncClient(api_key="mk-secret", base_url=BASE, **kwargs)


def test_database_method_returns_handle_without_http() -> None:
    with make_client() as client:
        db = client.database("my-app")
    assert isinstance(db, Database)
    assert db.name == "my-app"
    assert db.id == "my-app"
    assert str(db) == "mona-database:my-app"


def test_default_database_on_client() -> None:
    with make_client(default_database="my-app") as client:
        db = client.database()
    assert db.name == "my-app"


def test_database_without_name_or_default_raises() -> None:
    with make_client() as client, pytest.raises(ValueError, match="database name is required"):
        client.database()


def test_databases_subscript_raises_type_error() -> None:
    with make_client() as client, pytest.raises(TypeError, match=r"client\.database"):
        client.databases["my-app"]


@respx.mock
def test_query_returns_result_directly() -> None:
    route = respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [{"x": 1}], "rows_affected": 0}]},
        ),
    )
    with make_client() as client:
        result = client.database("my-app").query("select {x: 1};")

    assert isinstance(result, Result)
    assert result.rows == [{"x": 1}]
    assert route.calls.last.request.read() == b'{"statements":[{"sql":"select {x: 1};"}]}'


@respx.mock
def test_insert_builds_sql_and_returns_result() -> None:
    route = respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [], "rows_affected": 2}]},
        ),
    )
    with make_client() as client:
        result = client.database("my-app").insert(
            "beatles",
            {"name": "John"},
            {"name": "Paul"},
        )

    assert result.rows_affected == 2
    body = route.calls.last.request.read().decode()
    assert "insert into beatles" in body
    assert "John" in body
    assert "Paul" in body


@respx.mock
def test_execute_single_statement_is_chainable() -> None:
    route = respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [{"x": 1}], "rows_affected": 0}]},
        ),
    )
    with make_client() as client:
        db = client.database("my-app")
        handle = db.execute("select {x: 1};")
        rows = handle.fetchall()

    assert handle is db
    assert handle.name == "my-app"
    assert rows == [{"x": 1}]
    assert route.calls.last.request.read() == b'{"statements":[{"sql":"select {x: 1};"}]}'


@respx.mock
def test_execute_batch_returns_all_results() -> None:
    route = respx.post(f"{BASE}/v1/databases/beatles").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "results": [
                        {"rows": [], "rows_affected": 0},
                        {"rows": [], "rows_affected": 4},
                    ],
                },
            ),
            httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "rows": [
                                {"name": "John"},
                                {"name": "Paul"},
                                {"name": "George"},
                                {"name": "Ringo"},
                            ],
                            "rows_affected": 0,
                        },
                    ],
                },
            ),
        ],
    )
    with make_client() as client:
        db = client.database("beatles")
        results = db.execute(
            [
                "create table beatles;",
                (
                    "insert into beatles ({ name: 'John' }, { name: 'Paul' }, "
                    "{ name: 'George' }, { name: 'Ringo' });"
                ),
            ],
        )
        rows = db.fetchall("select * from beatles;")

    assert len(results) == 2
    assert results[0].rows_affected == 0
    assert results[1].rows_affected == 4
    assert rows == [
        {"name": "John"},
        {"name": "Paul"},
        {"name": "George"},
        {"name": "Ringo"},
    ]
    assert route.call_count == 2


@respx.mock
def test_fetchall_with_sql_argument() -> None:
    respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "rows": [{"name": "John"}, {"name": "Paul"}],
                        "rows_affected": 0,
                    },
                ],
            },
        ),
    )
    with make_client() as client:
        rows = client.database("my-app").fetchall("select * from beatles;")

    assert rows == [{"name": "John"}, {"name": "Paul"}]


@respx.mock
def test_fetchone_and_fetchmany_read_buffer() -> None:
    respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "rows": [{"n": 1}, {"n": 2}, {"n": 3}],
                        "rows_affected": 0,
                    },
                ],
            },
        ),
    )
    with make_client() as client:
        db = client.database("my-app").execute("select * from t;")
        assert db.fetchone() == {"n": 1}
        assert db.fetchmany(2) == [{"n": 2}, {"n": 3}]
        assert db.fetchone() is None


@respx.mock
def test_metadata_exists_and_schema_helpers() -> None:
    respx.get(f"{BASE}/v1/databases/my-app/metadata").mock(
        return_value=httpx.Response(200, json={"name": "my-app", "region": "us-east"}),
    )
    respx.get(f"{BASE}/v1/databases/missing/metadata").mock(
        return_value=httpx.Response(404, json={"code": "not_found", "message": "nope"}),
    )
    respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"rows": [{"tables": []}], "rows_affected": 0}]},
        ),
    )
    with make_client() as client:
        db = client.database("my-app")
        metadata = db.metadata()
        assert metadata.name == "my-app"
        assert db.exists() is True
        schema = db.schema()
        assert schema.rows == [{"tables": []}]

        missing = client.database("missing")
        assert missing.exists() is False


@respx.mock
async def test_async_database_execute_and_fetchall() -> None:
    respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "rows": [{"name": "John"}],
                        "rows_affected": 0,
                    },
                ],
            },
        ),
    )
    async with make_async_client() as client:
        rows = await client.database("my-app").fetchall("select * from beatles;")

    assert rows == [{"name": "John"}]


@respx.mock
async def test_async_execute_batch() -> None:
    respx.post(f"{BASE}/v1/databases/my-app").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"rows": [], "rows_affected": 0},
                    {"rows": [], "rows_affected": 2},
                ],
            },
        ),
    )
    async with make_async_client() as client:
        results = await client.database("my-app").execute(
            ["create table t;", "insert into t ({x: 1});"],
        )

    assert len(results) == 2
    assert results[1].rows_affected == 2


def test_execute_parameters_not_supported() -> None:
    with make_client() as client, pytest.raises(NotImplementedError, match="parameters"):
        client.database("my-app").execute("select 1;", parameters=[1])


def test_query_parameters_not_supported() -> None:
    with make_client() as client, pytest.raises(NotImplementedError, match="parameters"):
        client.database("my-app").query("select 1;", 1)
