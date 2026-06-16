from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


class MonaError(Exception):
    """Base class for all errors raised by the Mona SDK.

    Examples:
        Catch any SDK error::

            from mona import Client, MonaError

            try:
                client.databases.get("missing")
            except MonaError:
                ...

    """


class APIError(MonaError):
    """An error response returned by the Mona API.

    ``code`` is the machine-readable error code from the control plane
    (for example ``"not_found"``). For data-plane errors, which return a
    plain-text body, it falls back to a code derived from the HTTP status.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the response.
        code: Machine-readable error code.
        response: Original :class:`httpx.Response` that triggered the error.

    Examples:
        Inspect error details::

            from mona import Client, NotFoundError

            try:
                client.databases.get("missing")
            except NotFoundError as exc:
                print(exc.status_code, exc.code, exc.message)

    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str,
        response: httpx.Response,
    ) -> None:
        """Initialize an API error.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code from the response.
            code: Machine-readable error code.
            response: Original HTTP response.

        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.response = response


class BadRequestError(APIError):
    """HTTP 400 — the request was malformed or invalid.

    Examples:
        Handle validation failures::

            from mona import BadRequestError

            try:
                client.databases.create(name="")
            except BadRequestError as exc:
                print(exc.message)

    """


class AuthenticationError(APIError):
    """HTTP 401 — the API key is missing or invalid.

    Examples:
        Detect auth problems::

            from mona import AuthenticationError

            try:
                client.databases.list()
            except AuthenticationError:
                print("Check MONA_API_KEY")

    """


class NotFoundError(APIError):
    """HTTP 404 — the requested resource does not exist.

    Examples:
        Handle a missing database::

            from mona import NotFoundError

            try:
                client.databases.get("unknown")
            except NotFoundError as exc:
                assert exc.code == "not_found"

    """


class ConflictError(APIError):
    """HTTP 409 — the request conflicts with the current state.

    Examples:
        Handle duplicate database creation::

            from mona import ConflictError

            try:
                client.databases.create(name="existing")
            except ConflictError as exc:
                print(exc.message)

    """


_STATUS_TO_CLASS: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    404: NotFoundError,
    409: ConflictError,
}


def error_from_response(response: httpx.Response) -> APIError:
    """Build the appropriate :class:`APIError` from an HTTP error response.

    Handles both the control plane's JSON ``{"code", "message"}`` body and the
    data plane's plain-text error body.

    Args:
        response: HTTP response with a non-success status code.

    Returns:
        A typed :class:`APIError` subclass when the status code is recognized,
        otherwise a base :class:`APIError`.

    """
    status = response.status_code
    code = f"http_{status}"
    message = response.text

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            if "code" in body and "message" in body:
                code = str(body["code"])
                message = str(body["message"])
            elif "title" in body and "status" in body:
                code = str(body.get("type", code))
                message = str(body.get("detail") or body["title"])

    cls = _STATUS_TO_CLASS.get(status, APIError)
    return cls(message, status_code=status, code=code, response=response)
