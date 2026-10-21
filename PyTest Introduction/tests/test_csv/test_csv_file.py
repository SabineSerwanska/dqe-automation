import re

import pytest


def test_file_not_empty(csv_content):
    assert csv_content, "CSV file should contain at least one data row"


@pytest.mark.validate_csv
@pytest.mark.xfail(reason="The source CSV intentionally contains a duplicate row", strict=True)
def test_duplicates(csv_content):
    rows = [tuple(row.items()) for row in csv_content]
    assert len(rows) == len(set(rows)), "CSV file should not contain duplicate rows"


@pytest.mark.validate_csv
def test_validate_schema(actual_schema, expected_schema, schema_is_valid):
    assert schema_is_valid, (
        f"CSV schema mismatch: expected {expected_schema}, got {actual_schema}"
    )


@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age validation is intentionally skipped for this assignment")
def test_age_column_valid(csv_content):
    invalid_ages = [
        row["age"]
        for row in csv_content
        if not 0 <= int(row["age"]) <= 100
    ]
    assert not invalid_ages, f"Age values must be between 0 and 100: {invalid_ages}"


@pytest.mark.validate_csv
def test_email_column_valid(csv_content):
    invalid_emails = [
        row["email"]
        for row in csv_content
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", row["email"])
    ]
    assert not invalid_emails, f"Invalid email address(es): {invalid_emails}"


@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_active_players(csv_content, id, is_active):
    row = next((row for row in csv_content if int(row["id"]) == id), None)
    assert row is not None, f"CSV must contain a row with id={id}"
    assert row["is_active"].lower() == str(is_active).lower(), (
        f"Expected is_active={is_active} for id={id}, got {row['is_active']}"
    )


def test_active_player(csv_content):
    row = next((row for row in csv_content if int(row["id"]) == 2), None)
    assert row is not None, "CSV must contain a row with id=2"
    assert row["is_active"].lower() == "true", (
        f"Expected is_active=True for id=2, got {row['is_active']}"
    )
