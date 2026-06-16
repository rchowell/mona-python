import httpx
import pytest

from mona import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    MonaError,
    NotFoundError,
)
from mona._errors import error_from_response


def _resp(status: int, *, json: object | None = None, text: str | None = None) -> httpx.Response:
    req = httpx.Request("POST", "https://example.test/v1/databases")
    if json is not None:
        return httpx.Response(status, json=json, request=req)
    return httpx.Response(status, text=text or "", request=req)


def test_control_plane_json_error_maps_to_subclass() -> None:
    err = error_from_response(_resp(404, json={"code": "not_found", "message": "no such db"}))
    assert isinstance(err, NotFoundError)
    assert isinstance(err, APIError)
    assert isinstance(err, MonaError)
    assert err.status_code == 404
    assert err.code == "not_found"
    assert err.message == "no such db"
    assert "no such db" in str(err)


def test_status_codes_map_to_distinct_subclasses() -> None:
    assert isinstance(
        error_from_response(_resp(400, json={"code": "x", "message": "m"})),
        BadRequestError,
    )
    assert isinstance(
        error_from_response(_resp(401, json={"code": "x", "message": "m"})),
        AuthenticationError,
    )
    assert isinstance(
        error_from_response(_resp(409, json={"code": "x", "message": "m"})),
        ConflictError,
    )


def test_problem_detail_error_maps_to_subclass() -> None:
    err = error_from_response(
        _resp(
            400,
            json={
                "type": "https://mona.dev/errors/validation",
                "title": "Validation failed",
                "status": 400,
                "detail": "region is invalid",
            },
        ),
    )
    assert isinstance(err, BadRequestError)
    assert err.code == "https://mona.dev/errors/validation"
    assert err.message == "region is invalid"


def test_edge_plain_text_error_uses_body_as_message() -> None:
    err = error_from_response(_resp(400, text="syntax error near SELCT"))
    assert isinstance(err, BadRequestError)
    assert err.status_code == 400
    assert err.message == "syntax error near SELCT"


def test_unmapped_status_falls_back_to_api_error() -> None:
    err = error_from_response(_resp(500, text="boom"))
    assert isinstance(err, APIError)
    assert not isinstance(err, (BadRequestError, NotFoundError, ConflictError, AuthenticationError))
    assert err.status_code == 500


def test_can_raise_and_catch_as_mona_error() -> None:
    with pytest.raises(MonaError):
        raise error_from_response(_resp(409, json={"code": "conflict", "message": "exists"}))
