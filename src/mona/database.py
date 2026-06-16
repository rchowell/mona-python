"""MonaDB-style database handles for sync and async SQL execution."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TYPE_CHECKING, Self, overload

from . import _ops
from ._errors import NotFoundError
from ._models import Database as DatabaseRecord
from ._models import Result, Statement

if TYPE_CHECKING:
    from ._client import AsyncClient, Client


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    return json.dumps(value)


def _format_row(row: dict[str, object]) -> str:
    fields = ", ".join(f"{key}: {_format_value(val)}" for key, val in row.items())
    return f"{{{fields}}}"


def _build_insert_sql(table: str, rows: tuple[dict[str, object], ...]) -> str:
    if not rows:
        msg = "insert requires at least one row"
        raise ValueError(msg)
    values = ", ".join(_format_row(row) for row in rows)
    return f"insert into {table} ({values});"


class Database:
    """Handle for running SQL against a hosted database.

    Obtain with :meth:`~mona.Client.database`. High-level helpers such as
    :meth:`query` and :meth:`insert` return :class:`~mona.Result` directly.
    Low-level :meth:`execute` buffers rows for :meth:`fetchone`,
    :meth:`fetchmany`, and :meth:`fetchall`.

    Attributes:
        name: Database name used in API paths.

    Examples:
        Query and insert::

            from mona import Client

            with Client(api_key="mk-...", base_url="https://api.example") as client:
                db = client.database("my-app")
                db.insert("my-app", {"name": "John"})
                rows = db.query("select * from my-app;").rows

    """

    def __init__(self, client: Client, name: str) -> None:
        self._client = client
        self.name = name
        self._result: Result | None = None
        self._cursor = 0

    @property
    def id(self) -> str:
        """Database name (alias for :attr:`name`)."""
        return self.name

    def __str__(self) -> str:
        return f"mona-database:{self.name}"

    def __repr__(self) -> str:
        return f"Database({self.name!r})"

    def _run(
        self,
        statements: list[Statement],
        *,
        timeout: float | None = None,
    ) -> list[Result]:
        ep = _ops.execute(self.name, statements)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def _buffer(self, result: Result) -> None:
        self._result = result
        self._cursor = 0

    def query(
        self,
        statement: str,
        *args: object,
        timeout: float | None = None,
    ) -> Result:
        """Run a read query and return its result.

        Args:
            statement: SQL to execute.
            *args: Positional bind parameters (not yet supported by the server).
            timeout: Optional per-request timeout in seconds.

        Returns:
            Parsed result for the statement.

        Raises:
            NotImplementedError: If ``args`` are provided.
            APIError: If the API returns an error response.

        Examples:
            Fetch rows directly::

                result = db.query("select * from beatles;")
                assert result.rows == [{"name": "John"}]

        """
        if args:
            msg = "parameters are not yet supported by the server"
            raise NotImplementedError(msg)
        return self._run([Statement(sql=statement)], timeout=timeout)[0]

    def insert(
        self,
        table: str,
        *rows: dict[str, object],
        timeout: float | None = None,
    ) -> Result:
        """Insert one or more rows into a table.

        Args:
            table: Target table name.
            *rows: Row dicts to insert.
            timeout: Optional per-request timeout in seconds.

        Returns:
            Parsed result for the insert statement.

        Raises:
            ValueError: If no rows are provided.
            APIError: If the API returns an error response.

        Examples:
            Insert multiple rows in one request::

                result = db.insert("beatles", {"name": "John"}, {"name": "Paul"})
                assert result.rows_affected == 2

        """
        sql = _build_insert_sql(table, rows)
        return self._run([Statement(sql=sql)], timeout=timeout)[0]

    def metadata(self, *, timeout: float | None = None) -> DatabaseRecord:
        """Fetch control-plane metadata for this database."""
        ep = _ops.get_database(self.name)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def exists(self, *, timeout: float | None = None) -> bool:
        """Return whether this database exists."""
        try:
            self.metadata(timeout=timeout)
        except NotFoundError:
            return False
        return True

    def schema(self, *, timeout: float | None = None) -> Result:
        """Return the catalog for this database."""
        return self.query("select catalog;", timeout=timeout)

    @overload
    def execute(
        self,
        sql: str,
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> Self: ...

    @overload
    def execute(
        self,
        sql: list[str],
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> list[Result]: ...

    def execute(
        self,
        sql: str | list[str],
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> Self | list[Result]:
        """Run one or more SQL statements.

        A single string executes one statement, buffers its result, and returns
        ``self`` for chaining. A sequence executes each statement in one request
        and returns one :class:`~mona.Result` per statement; the last result is
        buffered for subsequent fetches.

        Args:
            sql: A single SQL string or a list of statements to run in batch.
            parameters: Bound parameters (not yet supported by the server).
            timeout: Optional per-request timeout in seconds.

        Returns:
            This handle when ``sql`` is a string, otherwise a list of
            :class:`~mona.Result` objects.

        Raises:
            NotImplementedError: If ``parameters`` is provided.
            APIError: If the API returns an error response.

        Examples:
            Chain a query and fetch::

                rows = db.execute("select * from beatles;").fetchall()

            Run a batch of statements::

                results = db.execute(
                    [
                        "create table beatles;",
                        "insert into beatles ({name: 'John'});",
                    ]
                )
                assert results[1].rows_affected == 1

        """
        if parameters is not None:
            msg = "parameters are not yet supported by the server"
            raise NotImplementedError(msg)

        if isinstance(sql, str):
            results = self._run([Statement(sql=sql)], timeout=timeout)
            self._buffer(results[0])
            return self

        statements = [Statement(sql=statement) for statement in sql]
        results = self._run(statements, timeout=timeout)
        if results:
            self._buffer(results[-1])
        return results

    def sql(
        self,
        query: str,
        parameters: object = None,
        *,
        timeout: float | None = None,
    ) -> Self:
        """Run a single SQL statement.

        Alias of :meth:`execute` for one statement.

        Args:
            query: SQL to execute.
            parameters: Bound parameters (not yet supported by the server).
            timeout: Optional per-request timeout in seconds.

        Returns:
            This handle for chaining.

        Raises:
            NotImplementedError: If ``parameters`` is provided.

        Examples:
            MonaDB-style entry point::

                db.sql("select * from t;").fetchall()

        """
        return self.execute(query, parameters=parameters, timeout=timeout)

    def fetchall(self, sql: str | None = None, *, timeout: float | None = None) -> list[object]:
        """Return all remaining buffered rows.

        Args:
            sql: Optional SQL to execute before reading the buffer.
            timeout: Optional per-request timeout in seconds.

        Returns:
            All unconsumed rows from the current result buffer.

        Examples:
            Execute and fetch in one call::

                rows = db.fetchall("select * from beatles;")

        """
        if sql is not None:
            self.execute(sql, timeout=timeout)
        if self._result is None:
            return []
        rows = self._result.rows[self._cursor :]
        self._cursor = len(self._result.rows)
        return rows

    def fetchone(self) -> object | None:
        """Return the next buffered row.

        Returns:
            The next row dict or scalar, or ``None`` when the buffer is
            exhausted.

        Examples:
            Iterate row by row::

                db.execute("select * from t;")
                while (row := db.fetchone()) is not None:
                    print(row)

        """
        if self._result is None or self._cursor >= len(self._result.rows):
            return None
        row = self._result.rows[self._cursor]
        self._cursor += 1
        return row

    def fetchmany(self, size: int = 1) -> list[object]:
        """Return up to ``size`` rows from the buffer.

        Args:
            size: Maximum number of rows to return.

        Returns:
            Up to ``size`` rows from the current buffer.

        Examples:
            Read rows in chunks::

                db.execute("select * from t;")
                batch = db.fetchmany(10)

        """
        if self._result is None:
            return []
        end = min(self._cursor + size, len(self._result.rows))
        rows = self._result.rows[self._cursor : end]
        self._cursor = end
        return rows


class AsyncDatabase:
    """Async handle for running SQL against a hosted database.

    Obtain with :meth:`~mona.AsyncClient.database`. See :class:`Database` for
    usage patterns; await each method call.

    Attributes:
        name: Database name used in API paths.

    Examples:
        Query and insert::

            from mona import AsyncClient

            async with AsyncClient(
                api_key="mk-...",
                base_url="https://api.example",
            ) as client:
                db = client.database("my-app")
                await db.insert("my-app", {"name": "John"})
                result = await db.query("select * from my-app;")

    """

    def __init__(self, client: AsyncClient, name: str) -> None:
        self._client = client
        self.name = name
        self._result: Result | None = None
        self._cursor = 0

    @property
    def id(self) -> str:
        """Database name (alias for :attr:`name`)."""
        return self.name

    def __str__(self) -> str:
        return f"mona-database:{self.name}"

    def __repr__(self) -> str:
        return f"AsyncDatabase({self.name!r})"

    async def _run(
        self,
        statements: list[Statement],
        *,
        timeout: float | None = None,
    ) -> list[Result]:
        ep = _ops.execute(self.name, statements)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    def _buffer(self, result: Result) -> None:
        self._result = result
        self._cursor = 0

    async def query(
        self,
        statement: str,
        *args: object,
        timeout: float | None = None,
    ) -> Result:
        """Run a read query and return its result."""
        if args:
            msg = "parameters are not yet supported by the server"
            raise NotImplementedError(msg)
        return (await self._run([Statement(sql=statement)], timeout=timeout))[0]

    async def insert(
        self,
        table: str,
        *rows: dict[str, object],
        timeout: float | None = None,
    ) -> Result:
        """Insert one or more rows into a table."""
        sql = _build_insert_sql(table, rows)
        return (await self._run([Statement(sql=sql)], timeout=timeout))[0]

    async def metadata(self, *, timeout: float | None = None) -> DatabaseRecord:
        """Fetch control-plane metadata for this database."""
        ep = _ops.get_database(self.name)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    async def exists(self, *, timeout: float | None = None) -> bool:
        """Return whether this database exists."""
        try:
            await self.metadata(timeout=timeout)
        except NotFoundError:
            return False
        return True

    async def schema(self, *, timeout: float | None = None) -> Result:
        """Return the catalog for this database."""
        return await self.query("select catalog;", timeout=timeout)

    @overload
    async def execute(
        self,
        sql: str,
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> Self: ...

    @overload
    async def execute(
        self,
        sql: list[str],
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> list[Result]: ...

    async def execute(
        self,
        sql: str | list[str],
        *,
        parameters: object = None,
        timeout: float | None = None,
    ) -> Self | list[Result]:
        """Run one or more SQL statements."""
        if parameters is not None:
            msg = "parameters are not yet supported by the server"
            raise NotImplementedError(msg)

        if isinstance(sql, str):
            results = await self._run([Statement(sql=sql)], timeout=timeout)
            self._buffer(results[0])
            return self

        statements = [Statement(sql=statement) for statement in sql]
        results = await self._run(statements, timeout=timeout)
        if results:
            self._buffer(results[-1])
        return results

    async def sql(
        self,
        query: str,
        parameters: object = None,
        *,
        timeout: float | None = None,
    ) -> Self:
        """Run a single SQL statement."""
        return await self.execute(query, parameters=parameters, timeout=timeout)

    async def fetchall(
        self,
        sql: str | None = None,
        *,
        timeout: float | None = None,
    ) -> list[object]:
        """Return all remaining buffered rows."""
        if sql is not None:
            await self.execute(sql, timeout=timeout)
        if self._result is None:
            return []
        rows = self._result.rows[self._cursor :]
        self._cursor = len(self._result.rows)
        return rows

    async def fetchone(self) -> object | None:
        """Return the next buffered row."""
        if self._result is None or self._cursor >= len(self._result.rows):
            return None
        row = self._result.rows[self._cursor]
        self._cursor += 1
        return row

    async def fetchmany(self, size: int = 1) -> list[object]:
        """Return up to ``size`` rows from the buffer."""
        if self._result is None:
            return []
        end = min(self._cursor + size, len(self._result.rows))
        rows = self._result.rows[self._cursor : end]
        self._cursor = end
        return rows
