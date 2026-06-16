"""Fixtures for Python SDK integration tests against control + edge."""

from __future__ import annotations

import contextlib
import os
import uuid
from typing import TYPE_CHECKING

import httpx
import pytest

from mona import AsyncClient, Client

if TYPE_CHECKING:
    from collections.abc import Iterator

CONTROL_URL = os.environ.get("MONA_CONTROL_URL", "http://localhost:8082")
EDGE_URL = os.environ.get("MONA_EDGE_URL", "http://localhost:8080")
API_KEY = os.environ.get("MONA_API_KEY", "dev-key")


def _control_reachable() -> bool:
    try:
        resp = httpx.get(f"{CONTROL_URL}/health", timeout=2.0)
    except httpx.HTTPError:
        return False
    else:
        return resp.is_success


@pytest.fixture(scope="session", autouse=True)
def require_control() -> None:
    if not _control_reachable():
        pytest.skip(
            f"mona not reachable at {CONTROL_URL}",
            allow_module_level=True,
        )


@pytest.fixture
def client() -> Iterator[Client]:
    with Client(api_key=API_KEY, base_url=CONTROL_URL, query_base_url=EDGE_URL) as c:
        yield c


@pytest.fixture
def edge_client() -> Iterator[Client]:
    with Client(api_key=API_KEY, base_url=EDGE_URL) as c:
        yield c


@pytest.fixture
def async_client() -> Iterator[AsyncClient]:
    return AsyncClient(api_key=API_KEY, base_url=CONTROL_URL, query_base_url=EDGE_URL)


@pytest.fixture
def database_name() -> str:
    return f"sdk-it-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def database(client: Client, database_name: str) -> Iterator[str]:
    client.databases.create(name=database_name)
    try:
        yield database_name
    finally:
        with contextlib.suppress(Exception):
            client.databases.delete(database_name)
