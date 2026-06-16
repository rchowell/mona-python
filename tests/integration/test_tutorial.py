"""Integration tests mirroring site/content/docs/tutorial.md."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mona import Client

pytestmark = pytest.mark.integration


@pytest.mark.xfail(
    reason="monadb engine panics on table DDL in the current Tilt build "
    "(node returns 500 'monadb panicked'); not an SDK issue",
    strict=False,
)
def test_tutorial_beatles_walkthrough(client: Client, database: str) -> None:
    db = client.database(database)
    results = db.execute(
        [
            "create table beatles;",
            (
                "insert into beatles ({ name: 'John' }, { name: 'Paul' }, "
                "{ name: 'George' }, { name: 'Ringo' });"
            ),
        ],
    )
    assert len(results) == 2
    assert results[0].rows_affected == 0
    assert results[1].rows_affected == 4

    rows = db.fetchall("select * from beatles;")
    assert rows == [
        {"name": "John"},
        {"name": "Paul"},
        {"name": "George"},
        {"name": "Ringo"},
    ]
