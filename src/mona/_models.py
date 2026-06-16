from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class Database(BaseModel):
    """Database metadata returned by control-plane operations.

    Returned by :meth:`~mona.resources.databases.DatabasesResource.create`,
    :meth:`~mona.resources.databases.DatabasesResource.get`, and
    :meth:`~mona.resources.databases.DatabasesResource.list`.

    Attributes:
        name: Unique database name.
        region: Optional deployment region.
        created_at: ISO-8601 creation timestamp, when provided by the API.

    Examples:
        Inspect metadata after creation::

            record = client.databases.create(name="my-app", region="us-east")
            assert record.name == "my-app"
            assert record.region == "us-east"

    """

    name: str
    region: str | None = None
    created_at: str | None = None


class Statement(BaseModel):
    """A SQL statement with optional bound parameters.

    Attributes:
        sql: SQL text to execute.
        args: Optional positional arguments (not yet supported end-to-end).

    Examples:
        Build a batch payload::

            from mona import Statement

            statements = [
                Statement(sql="create table t;"),
                Statement(sql="insert into t values (?);", args=[1]),
            ]

    """

    sql: str
    args: list[Any] | None = None


class Row(BaseModel):
    """Deprecated row wrapper.

    Prefer flat JSON values in :attr:`~mona.Result.rows`.

    Attributes:
        values: Column values for a single row.

    Examples:
        Legacy wrapped row shape (normalized away by :class:`Result`)::

            Row(values=[{"name": "John"}])

    """

    values: list[Any]


class Result(BaseModel):
    """The result of executing a SQL statement.

    Attributes:
        rows: Result rows as dicts or scalars.
        rows_affected: Number of rows changed by DML statements.

    Examples:
        Read rows from a query::

            result = db.query("select {x: 1};")
            assert result.rows == [{"x": 1}]
            assert result.rows_affected == 0

    """

    rows: list[object]
    rows_affected: int

    @field_validator("rows", mode="before")
    @classmethod
    def _normalize_rows(cls, rows: object) -> object:
        if not isinstance(rows, list):
            return rows
        normalized: list[object] = []
        for row in rows:
            if isinstance(row, dict) and set(row) == {"values"}:
                values = row["values"]
                if isinstance(values, list) and len(values) == 1:
                    normalized.append(values[0])
                else:
                    normalized.append(values)
            else:
                normalized.append(row)
        return normalized


class DatabasePage:
    """A page of database metadata records.

    Returned by :meth:`~mona.resources.databases.DatabasesResource.list`.
    Iterable like a list. Call :meth:`get_next_page` when :attr:`next_cursor` is set.

    Attributes:
        databases: Metadata records in this page.
        next_cursor: Cursor for the next page, if any.

    Examples:
        List with an optional prefix filter::

            for record in client.databases.list(prefix="app-"):
                print(record.name)

    """

    def __init__(
        self,
        *,
        databases: list[Database],
        next_cursor: str | None = None,
        fetch_next: Callable[[str], DatabasePage] | None = None,
    ) -> None:
        self.databases = databases
        self.next_cursor = next_cursor
        self._fetch_next = fetch_next

    def __iter__(self) -> Iterator[Database]:
        return iter(self.databases)

    def __len__(self) -> int:
        return len(self.databases)

    def __getitem__(self, index: int) -> Database:
        return self.databases[index]

    def get_next_page(self) -> DatabasePage | None:
        """Fetch the next page using the cursor from the previous response."""
        if self.next_cursor is None or self._fetch_next is None:
            return None
        return self._fetch_next(self.next_cursor)


class AsyncDatabasePage:
    """Async variant of :class:`DatabasePage`."""

    def __init__(
        self,
        *,
        databases: list[Database],
        next_cursor: str | None = None,
        fetch_next: Callable[[str], AsyncDatabasePage] | None = None,
    ) -> None:
        self.databases = databases
        self.next_cursor = next_cursor
        self._fetch_next = fetch_next

    def __iter__(self) -> Iterator[Database]:
        return iter(self.databases)

    def __len__(self) -> int:
        return len(self.databases)

    def __getitem__(self, index: int) -> Database:
        return self.databases[index]

    async def get_next_page(self) -> AsyncDatabasePage | None:
        """Fetch the next page using the cursor from the previous response."""
        if self.next_cursor is None or self._fetch_next is None:
            return None
        return await self._fetch_next(self.next_cursor)


class HealthStatus(BaseModel):
    """Service health, as returned by ``GET /health``.

    Attributes:
        status: Health indicator (for example ``"ok"``).
        service: Optional service name.
        node_id: Optional node identifier.

    Examples:
        Check service health::

            status = client.health()
            assert status.status == "ok"

    """

    status: str
    service: str | None = None
    node_id: str | None = None


class FieldError(BaseModel):
    """A single field-level validation failure.

    Attributes:
        field: Name of the invalid field.
        message: Human-readable validation message.

    Examples:
        Access nested validation errors::

            detail.errors[0].field
            detail.errors[0].message

    """

    field: str
    message: str


class ProblemDetail(BaseModel):
    """RFC 9457 problem details returned by some API surfaces.

    Attributes:
        type: URI identifying the problem type.
        title: Short human-readable summary.
        status: HTTP status code.
        detail: Optional longer explanation.
        instance: Optional URI identifying this occurrence.
        errors: Optional list of field-level validation failures.

    Examples:
        Parse a problem-details body::

            detail = ProblemDetail.model_validate(response.json())
            if detail.errors:
                print(detail.errors[0].message)

    """

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    """Structured error response from the control plane.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error description.

    Examples:
        Typical control-plane error body::

            ErrorResponse(code="not_found", message="database not found")

    """

    code: str
    message: str


class ResolveDatabaseInstanceResponse(BaseModel):
    """Database-to-instance resolution from the control plane.

    Attributes:
        instance_id: Identifier of the backing database instance.

    Examples:
        Resolve where a database is hosted::

            resolved = client.databases.resolve_instance("my-app")
            print(resolved.instance_id)

    """

    instance_id: str
