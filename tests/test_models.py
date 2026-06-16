from mona import DatabaseRecord, ResolveDatabaseInstanceResponse, Result


def test_database_parses_full_record() -> None:
    db = DatabaseRecord.model_validate(
        {"name": "my-app", "region": "us-east", "created_at": "2024-01-01T00:00:00Z"},
    )
    assert db.name == "my-app"
    assert db.region == "us-east"
    assert db.created_at == "2024-01-01T00:00:00Z"


def test_database_parses_minimal_record() -> None:
    db = DatabaseRecord.model_validate({"name": "my-app"})
    assert db.name == "my-app"
    assert db.region is None
    assert db.created_at is None


def test_result_parses_wire_rows() -> None:
    result = Result.model_validate(
        {
            "rows": [{"name": "John"}, {"name": "Paul"}],
            "rows_affected": 0,
        },
    )
    assert result.rows_affected == 0
    assert result.rows == [{"name": "John"}, {"name": "Paul"}]


def test_result_normalizes_legacy_row_wrapper() -> None:
    result = Result.model_validate({"rows": [{"values": [{"x": 1}]}], "rows_affected": 0})
    assert result.rows == [{"x": 1}]


def test_resolve_database_instance_parses() -> None:
    resolved = ResolveDatabaseInstanceResponse.model_validate({"instance_id": "inst-abc"})
    assert resolved.instance_id == "inst-abc"
