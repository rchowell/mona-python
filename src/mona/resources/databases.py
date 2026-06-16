"""Sync and async database resource implementations."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from mona import _ops
from mona._models import AsyncDatabasePage, DatabasePage

if TYPE_CHECKING:
    from mona._client import AsyncClient, Client
    from mona._models import Database as DatabaseRecord
    from mona._models import ResolveDatabaseInstanceResponse, Result


class DatabasesResource:
    """Synchronous database management operations.

    Accessed as ``client.databases``. Obtain a SQL handle with
    :meth:`~mona.Client.database`.

    Examples:
        Manage databases and run queries::

            from mona import Client

            with Client(api_key="mk-...", base_url="https://api.example") as client:
                client.databases.create(name="my-app")
                rows = client.database("my-app").query("select 1;").rows

    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def __getitem__(self, name: str) -> None:
        msg = "Use client.database(...) instead of client.databases[...]"
        raise TypeError(msg)

    def create(
        self,
        name: str,
        region: str | None = None,
        *,
        timeout: float | None = None,
    ) -> DatabaseRecord:
        """Create a new database."""
        ep = _ops.create_database(name, region)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def list(
        self,
        *,
        prefix: str | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
        timeout: float | None = None,
    ) -> DatabasePage:
        """List databases in the account.

        Args:
            prefix: Return only databases whose names start with this prefix.
            cursor: Resume listing from a previous page cursor.
            page_size: Limit the number of results returned.
            timeout: Optional per-request timeout in seconds.

        Returns:
            An iterable page of database metadata records.

        Examples:
            Filter by prefix::

                for record in client.databases.list(prefix="app-"):
                    print(record.name)

        """

        def fetch_next(next_cursor: str) -> DatabasePage:
            return self.list(
                prefix=prefix,
                cursor=next_cursor,
                page_size=page_size,
                timeout=timeout,
            )

        ep = _ops.list_databases(
            prefix=prefix,
            cursor=cursor,
            page_size=page_size,
            fetch_next=fetch_next,
        )
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def get(self, database: str, *, timeout: float | None = None) -> DatabaseRecord:
        """Fetch metadata for a database."""
        ep = _ops.get_database(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def delete(self, database: str, *, timeout: float | None = None) -> None:
        """Delete a database."""
        ep = _ops.delete_database(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def resolve_instance(
        self,
        database: str,
        *,
        timeout: float | None = None,
    ) -> ResolveDatabaseInstanceResponse:
        """Resolve the backing instance for a database."""
        ep = _ops.resolve_database_instance(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(self._client._send(op))

    def query(
        self,
        database: str,
        sql: str,
        *,
        timeout: float | None = None,
    ) -> Result:
        """Execute a single statement and return its result."""
        return self._client.database(database).query(sql, timeout=timeout)


class AsyncDatabasesResource:
    """Asynchronous database management operations."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def __getitem__(self, name: str) -> None:
        msg = "Use client.database(...) instead of client.databases[...]"
        raise TypeError(msg)

    async def create(
        self,
        name: str,
        region: str | None = None,
        *,
        timeout: float | None = None,
    ) -> DatabaseRecord:
        """Create a new database."""
        ep = _ops.create_database(name, region)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    async def list(
        self,
        *,
        prefix: str | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
        timeout: float | None = None,
    ) -> AsyncDatabasePage:
        """List databases in the account."""

        async def fetch_next(next_cursor: str) -> AsyncDatabasePage:
            return await self.list(
                prefix=prefix,
                cursor=next_cursor,
                page_size=page_size,
                timeout=timeout,
            )

        ep = _ops.list_databases(
            prefix=prefix,
            cursor=cursor,
            page_size=page_size,
        )
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        page = ep.parse(await self._client._send(op))
        return AsyncDatabasePage(
            databases=page.databases,
            next_cursor=page.next_cursor,
            fetch_next=fetch_next,
        )

    async def get(self, database: str, *, timeout: float | None = None) -> DatabaseRecord:
        """Fetch metadata for a database."""
        ep = _ops.get_database(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    async def delete(self, database: str, *, timeout: float | None = None) -> None:
        """Delete a database."""
        ep = _ops.delete_database(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    async def resolve_instance(
        self,
        database: str,
        *,
        timeout: float | None = None,
    ) -> ResolveDatabaseInstanceResponse:
        """Resolve the backing instance for a database."""
        ep = _ops.resolve_database_instance(database)
        op = replace(ep.op, timeout=timeout) if timeout is not None else ep.op
        return ep.parse(await self._client._send(op))

    async def query(
        self,
        database: str,
        sql: str,
        *,
        timeout: float | None = None,
    ) -> Result:
        """Execute a single statement and return its result."""
        return await self._client.database(database).query(sql, timeout=timeout)
