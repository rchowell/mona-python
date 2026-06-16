from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._errors import error_from_response

if TYPE_CHECKING:
    import httpx


@dataclass(frozen=True)
class Config:
    """Resolved client configuration."""

    api_key: str
    base_url: str
    query_base_url: str
    timeout: float
    max_retries: int
    default_database: str | None


def resolve_config(
    api_key: str | None,
    base_url: str | None,
    query_base_url: str | None,
    timeout: float,
    max_retries: int,
    default_database: str | None,
) -> Config:
    """Resolve constructor args against environment variables and validate them."""
    api_key = api_key or os.environ.get("MONA_API_KEY")
    if not api_key:
        msg = "api_key is required: pass api_key=... or set the MONA_API_KEY environment variable"
        raise ValueError(
            msg,
        )

    base_url = base_url or os.environ.get("MONA_BASE_URL")
    if not base_url:
        msg = (
            "base_url is required: pass base_url=... or set the MONA_BASE_URL environment variable"
        )
        raise ValueError(
            msg,
        )
    base_url = base_url.rstrip("/")

    resolved_query = (query_base_url or base_url).rstrip("/")
    resolved_default_database = default_database or os.environ.get("MONA_DEFAULT_DATABASE")
    return Config(
        api_key=api_key,
        base_url=base_url,
        query_base_url=resolved_query,
        timeout=timeout,
        max_retries=max_retries,
        default_database=resolved_default_database,
    )


def default_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def raise_for_status(response: httpx.Response) -> httpx.Response:
    """Return the response if successful, otherwise raise a typed APIError."""
    if response.is_success:
        return response
    raise error_from_response(response)
