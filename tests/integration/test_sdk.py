"""Python SDK integration tests against control + edge."""

from __future__ import annotations

import pytest

from mona import AsyncClient, Client, DatabaseRecord, HealthStatus, NotFoundError, Result

pytestmark = pytest.mark.integration


def test_health_control_and_edge(client: Client, edge_client: Client) -> None:
    control_health = client.health()
    assert isinstance(control_health, HealthStatus)
    assert control_health.status == "ok"

    edge_health = edge_client.health()
    assert edge_health.status == "ok"


def test_create_get_list_delete_lifecycle(client: Client, database_name: str) -> None:
    created = client.databases.create(name=database_name)
    assert isinstance(created, DatabaseRecord)
    assert created.name == database_name

    try:
        fetched = client.databases.get(database_name)
        assert fetched.name == database_name

        names = [db.name for db in client.databases.list()]
        assert database_name in names
    finally:
        client.databases.delete(database_name)

    after = [db.name for db in client.databases.list()]
    assert database_name not in after


def test_get_missing_database_raises_not_found(client: Client) -> None:
    with pytest.raises(NotFoundError):
        client.databases.get("sdk-it-does-not-exist-xyz")


def test_query_executes_select(client: Client, database: str) -> None:
    result = client.database(database).query("select {x: 1};")
    assert isinstance(result, Result)
    assert result.rows[0] == {"x": 1}


@pytest.mark.xfail(
    reason="monadb engine panics on table DDL in the current Tilt build "
    "(node returns 500 'monadb panicked'); not an SDK issue",
    strict=False,
)
def test_query_roundtrip_create_insert_select(client: Client, database: str) -> None:
    db = client.database(database)
    db.execute("create table items (id int, name string);")
    insert = db.insert("items", {"id": 1, "name": "alpha"})
    assert insert.rows_affected == 1

    selected = db.query("select * from items;")
    assert selected.rows[0] == {"id": 1, "name": "alpha"}


async def test_async_lifecycle_and_query(async_client: AsyncClient, database_name: str) -> None:
    async with async_client as client:
        created = await client.databases.create(name=database_name)
        assert created.name == database_name
        try:
            result = await client.database(database_name).query("select {x: 1};")
            assert result.rows[0] == {"x": 1}
        finally:
            await client.databases.delete(database_name)
