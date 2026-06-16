"""Official Python SDK for MonaDB.

Sync and async clients for managing hosted databases and executing SQL.
Built on :mod:`httpx` and :mod:`pydantic`.

Examples:
    Quick start with the synchronous client::

        from mona import Client

        with Client(api_key="mk-...", base_url="https://mona.example.workers.dev") as mo:
            mo.databases.create(name="beatles")
            rows = mo.database("beatles").query("select * from beatles;").rows

"""

from ._client import AsyncClient, Client
from ._errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    MonaError,
    NotFoundError,
)
from ._models import (
    AsyncDatabasePage,
    DatabasePage,
    ErrorResponse,
    FieldError,
    HealthStatus,
    ProblemDetail,
    ResolveDatabaseInstanceResponse,
    Result,
    Row,
    Statement,
)
from ._models import (
    Database as DatabaseRecord,
)
from ._version import __version__
from .database import AsyncDatabase, Database

__all__ = [
    "APIError",
    "AsyncClient",
    "AsyncDatabase",
    "AsyncDatabasePage",
    "AuthenticationError",
    "BadRequestError",
    "Client",
    "ConflictError",
    "Database",
    "DatabasePage",
    "DatabaseRecord",
    "ErrorResponse",
    "FieldError",
    "HealthStatus",
    "MonaError",
    "NotFoundError",
    "ProblemDetail",
    "ResolveDatabaseInstanceResponse",
    "Result",
    "Row",
    "Statement",
    "__version__",
]
