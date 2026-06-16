from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from typing_extensions import Self

from . import _ops
from ._transport import Config, default_headers, raise_for_status, resolve_config
from .database import AsyncDatabase, Database
from .resources import AsyncDatabasesResource, DatabasesResource

if TYPE_CHECKING:
    from types import TracebackType

    from ._models import HealthStatus
    from ._ops import Op


class Client:
    """Synchronous client for the Mona API.

    Use as a context manager to ensure the underlying HTTP connection is closed,
    or call :meth:`close` explicitly.

    Attributes:
        databases: Control-plane and query helpers for hosted databases.

    Examples:
        Create a database and query it::

            from mona import Client

            with Client(api_key="mk-...", base_url="https://mona.example.workers.dev") as client:
                client.databases.create(name="my-app")
                rows = client.database("my-app").fetchall("select * from t;")

    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        query_base_url: str | None = None,
        default_database: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize a synchronous client.

        Args:
            api_key: Bearer token for API authentication. Falls back to the
                ``MONA_API_KEY`` environment variable when omitted.
            base_url: Control-plane base URL. Falls back to ``MONA_BASE_URL``.
            query_base_url: Optional override for the data-plane host. Defaults
                to ``base_url``.
            default_database: Default database for :meth:`database`. Falls back
                to ``MONA_DEFAULT_DATABASE``.
            timeout: Per-request timeout in seconds.
            max_retries: Connection-level retries passed to httpx.
            http_client: Optional pre-configured :class:`httpx.Client`. When
                provided, ``timeout`` and ``max_retries`` are not applied.

        Raises:
            ValueError: If no API key is available from arguments or the
                environment.

        Examples:
            Configure from environment variables::

                import os

                os.environ["MONA_API_KEY"] = "mk-..."
                os.environ["MONA_BASE_URL"] = "https://mona.example.workers.dev"

                with Client() as client:
                    client.health()

        """
        self._config: Config = resolve_config(
            api_key,
            base_url,
            query_base_url,
            timeout,
            max_retries,
            default_database,
        )
        self._http = http_client or httpx.Client(
            headers=default_headers(self._config.api_key),
            timeout=self._config.timeout,
            transport=httpx.HTTPTransport(retries=self._config.max_retries),
        )
        self.databases = DatabasesResource(self)

    def database(self, name: str | None = None) -> Database:
        """Return a handle for running SQL against a database.

        Args:
            name: Database name. Falls back to :attr:`default_database` when
                omitted.

        Returns:
            A :class:`~mona.Database` handle.

        Raises:
            ValueError: If no name is available from arguments or client config.

        Examples:
            Bind a database and query it::

                db = client.database("my-app")
                result = db.query("select {x: 1};")

            Use the client default database::

                client = Client(..., default_database="my-app")
                rows = client.database().query("select * from my-app;").rows

        """
        resolved = name if name is not None else self._config.default_database
        if not resolved:
            msg = (
                "database name is required: pass name=... or set default_database=... "
                "or the MONA_DEFAULT_DATABASE environment variable"
            )
            raise ValueError(msg)
        return Database(self, resolved)

    @property
    def default_database(self) -> str | None:
        """Default database name for :meth:`database`."""
        return self._config.default_database

    def _url(self, op: Op) -> str:
        base = self._config.query_base_url if op.plane == "query" else self._config.base_url
        return f"{base}{op.path}"

    def _send(self, op: Op) -> httpx.Response:
        kwargs: dict[str, object] = {}
        if op.timeout is not None:
            kwargs["timeout"] = op.timeout
        response = self._http.request(op.method, self._url(op), json=op.json, **kwargs)
        return raise_for_status(response)

    def health(self) -> HealthStatus:
        """Check API availability.

        Returns:
            Parsed health payload from ``GET /health``.

        Examples:
            Verify the service is up::

                status = client.health()
                assert status.status == "ok"

        """
        ep = _ops.health()
        return ep.parse(self._send(ep.op))

    def close(self) -> None:
        """Close the underlying HTTP client and release connections.

        Examples:
            Explicit cleanup without a context manager::

                client = Client(api_key="mk-...", base_url="https://api.example")
                try:
                    client.databases.list()
                finally:
                    client.close()

        """
        self._http.close()

    def __enter__(self) -> Self:
        """Enter a context manager and return this client.

        Returns:
            This :class:`Client` instance.

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and close the HTTP client.

        Args:
            exc_type: Exception type, if an error was raised in the block.
            exc: Exception instance, if raised.
            tb: Traceback for the exception, if raised.

        """
        self.close()


class AsyncClient:
    """Asynchronous client for the Mona API.

    Use as an async context manager to ensure the underlying HTTP connection is
    closed, or call :meth:`aclose` explicitly.

    Attributes:
        databases: Async control-plane and query helpers for hosted databases.

    Examples:
        Create a database and query it::

            from mona import AsyncClient

            async with AsyncClient(
                api_key="mk-...",
                base_url="https://mona.example.workers.dev",
            ) as client:
                await client.databases.create(name="my-app")
                rows = await client.database("my-app").fetchall("select * from t;")

    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        query_base_url: str | None = None,
        default_database: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize an asynchronous client.

        Args:
            api_key: Bearer token for API authentication. Falls back to the
                ``MONA_API_KEY`` environment variable when omitted.
            base_url: Control-plane base URL. Falls back to ``MONA_BASE_URL``.
            query_base_url: Optional override for the data-plane host. Defaults
                to ``base_url``.
            default_database: Default database for :meth:`database`. Falls back
                to ``MONA_DEFAULT_DATABASE``.
            timeout: Per-request timeout in seconds.
            max_retries: Connection-level retries passed to httpx.
            http_client: Optional pre-configured :class:`httpx.AsyncClient`.
                When provided, ``timeout`` and ``max_retries`` are not applied.

        Raises:
            ValueError: If no API key is available from arguments or the
                environment.

        Examples:
            Configure from environment variables::

                import os

                os.environ["MONA_API_KEY"] = "mk-..."
                os.environ["MONA_BASE_URL"] = "https://mona.example.workers.dev"

                async with AsyncClient() as client:
                    await client.health()

        """
        self._config: Config = resolve_config(
            api_key,
            base_url,
            query_base_url,
            timeout,
            max_retries,
            default_database,
        )
        self._http = http_client or httpx.AsyncClient(
            headers=default_headers(self._config.api_key),
            timeout=self._config.timeout,
            transport=httpx.AsyncHTTPTransport(retries=self._config.max_retries),
        )
        self.databases = AsyncDatabasesResource(self)

    def database(self, name: str | None = None) -> AsyncDatabase:
        """Return an async handle for running SQL against a database."""
        resolved = name if name is not None else self._config.default_database
        if not resolved:
            msg = (
                "database name is required: pass name=... or set default_database=... "
                "or the MONA_DEFAULT_DATABASE environment variable"
            )
            raise ValueError(msg)
        return AsyncDatabase(self, resolved)

    @property
    def default_database(self) -> str | None:
        """Default database name for :meth:`database`."""
        return self._config.default_database

    def _url(self, op: Op) -> str:
        base = self._config.query_base_url if op.plane == "query" else self._config.base_url
        return f"{base}{op.path}"

    async def _send(self, op: Op) -> httpx.Response:
        kwargs: dict[str, object] = {}
        if op.timeout is not None:
            kwargs["timeout"] = op.timeout
        response = await self._http.request(op.method, self._url(op), json=op.json, **kwargs)
        return raise_for_status(response)

    async def health(self) -> HealthStatus:
        """Check API availability.

        Returns:
            Parsed health payload from ``GET /health``.

        Examples:
            Verify the service is up::

                status = await client.health()
                assert status.status == "ok"

        """
        ep = _ops.health()
        return ep.parse(await self._send(ep.op))

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections.

        Examples:
            Explicit cleanup without a context manager::

                client = AsyncClient(api_key="mk-...", base_url="https://api.example")
                try:
                    await client.databases.list()
                finally:
                    await client.aclose()

        """
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        """Enter an async context manager and return this client.

        Returns:
            This :class:`AsyncClient` instance.

        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the HTTP client.

        Args:
            exc_type: Exception type, if an error was raised in the block.
            exc: Exception instance, if raised.
            tb: Traceback for the exception, if raised.

        """
        await self.aclose()
