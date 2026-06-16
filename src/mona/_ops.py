"""Endpoint definitions shared by the sync and async clients.

Each function returns an :class:`Endpoint` carrying the HTTP request to make and a
pure ``parse`` callable mapping the response to a typed result. Keeping request
construction and parsing here means the sync and async resources are thin glue that
differ only in ``send`` vs ``await asend``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from ._models import (
    Database,
    DatabasePage,
    HealthStatus,
    ResolveDatabaseInstanceResponse,
    Result,
    Statement,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

T = TypeVar("T")

Plane = Literal["control", "query"]


@dataclass(frozen=True)
class Op:
    method: str
    path: str
    json: dict[str, Any] | None = None
    plane: Plane = "control"
    timeout: float | None = None


@dataclass(frozen=True)
class Endpoint(Generic[T]):
    op: Op
    parse: Callable[[httpx.Response], T] = field()


def health() -> Endpoint[HealthStatus]:
    return Endpoint(Op("GET", "/health"), lambda r: HealthStatus.model_validate(r.json()))


def create_database(database: str, region: str | None) -> Endpoint[Database]:
    body: dict[str, Any] | None = {"region": region} if region is not None else {}
    return Endpoint(
        Op("PUT", f"/v1/databases/{database}", body),
        lambda r: Database.model_validate(r.json()),
    )


def _parse_list_response(
    response: httpx.Response,
    *,
    prefix: str | None,
    page_size: int | None,
    fetch_next: Callable[[str], DatabasePage] | None,
) -> DatabasePage:
    data = response.json()
    databases = [Database.model_validate(record) for record in data["databases"]]
    if prefix is not None:
        databases = [record for record in databases if record.name.startswith(prefix)]
    if page_size is not None:
        databases = databases[:page_size]
    next_cursor = data.get("next_cursor")
    next_cursor = next_cursor or None if isinstance(next_cursor, str) else None
    return DatabasePage(
        databases=databases,
        next_cursor=next_cursor,
        fetch_next=fetch_next,
    )


def list_databases(
    *,
    prefix: str | None = None,
    cursor: str | None = None,
    page_size: int | None = None,
    fetch_next: Callable[[str], DatabasePage] | None = None,
) -> Endpoint[DatabasePage]:
    body: dict[str, Any] = {}
    if prefix is not None:
        body["prefix"] = prefix
    if cursor is not None:
        body["cursor"] = cursor
    if page_size is not None:
        body["page_size"] = page_size

    return Endpoint(
        Op("POST", "/v1/databases", body or None),
        lambda response: _parse_list_response(
            response,
            prefix=prefix,
            page_size=page_size,
            fetch_next=fetch_next,
        ),
    )


def get_database(database: str) -> Endpoint[Database]:
    return Endpoint(
        Op("GET", f"/v1/databases/{database}/metadata"),
        lambda r: Database.model_validate(r.json()),
    )


def delete_database(database: str) -> Endpoint[None]:
    return Endpoint(Op("DELETE", f"/v1/databases/{database}"), lambda _: None)


def resolve_database_instance(database: str) -> Endpoint[ResolveDatabaseInstanceResponse]:
    return Endpoint(
        Op("GET", f"/v1/databases/{database}/instance"),
        lambda r: ResolveDatabaseInstanceResponse.model_validate(r.json()),
    )


def _parse_execute_response(response: httpx.Response) -> list[Result]:
    return [Result.model_validate(result) for result in response.json()["results"]]


def execute(database: str, statements: list[Statement]) -> Endpoint[list[Result]]:
    body = {
        "statements": [statement.model_dump(exclude_none=True) for statement in statements],
    }
    return Endpoint(
        Op(
            "POST",
            f"/v1/databases/{database}",
            body,
            plane="query",
        ),
        _parse_execute_response,
    )


def query(database: str, sql: str) -> Endpoint[Result]:
    ep = execute(database, [Statement(sql=sql)])

    def _first_result(response: httpx.Response) -> Result:
        return _parse_execute_response(response)[0]

    return Endpoint(ep.op, _first_result)
