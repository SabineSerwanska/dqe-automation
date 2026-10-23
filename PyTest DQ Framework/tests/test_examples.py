"""Fast examples of the framework's reusable data quality assertions."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import (
    PostgresConnectorContextManager,
)
from src.data_quality.data_quality_validation_library import DataQualityLibrary


@pytest.fixture
def data_quality_library():
    return DataQualityLibrary()


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "record_id": [1, 2],
            "category": ["alpha", "beta"],
        }
    )


@pytest.mark.example
def test_check_dataset_is_not_empty(sample_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(sample_data)


@pytest.mark.example
def test_check_count(sample_data, data_quality_library):
    data_quality_library.check_count(sample_data, sample_data.copy())


@pytest.mark.example
def test_check_data_completeness_ignores_row_order(
    sample_data, data_quality_library
):
    actual_data = sample_data.iloc[::-1][["category", "record_id"]].reset_index(
        drop=True
    )
    data_quality_library.check_data_completeness(sample_data, actual_data)


@pytest.mark.example
def test_check_data_completeness_matches_date_and_midnight_timestamp(
    data_quality_library,
):
    expected_data = pd.DataFrame({"visit_date": [date(2025, 9, 22)]})
    actual_data = pd.DataFrame(
        {"visit_date": pd.to_datetime(["2025-09-22T00:00:00"])}
    )

    data_quality_library.check_data_completeness(expected_data, actual_data)


@pytest.mark.example
def test_check_uniqueness(sample_data, data_quality_library):
    data_quality_library.check_duplicates(sample_data, ["record_id"])


@pytest.mark.example
def test_check_not_null_values(sample_data, data_quality_library):
    data_quality_library.check_not_null_values(
        sample_data, ["record_id", "category"]
    )


@pytest.mark.example
def test_check_dataset_is_not_empty_rejects_empty_dataframe(data_quality_library):
    with pytest.raises(AssertionError, match="at least one row"):
        data_quality_library.check_dataset_is_not_empty(pd.DataFrame())


@pytest.mark.example
def test_check_count_rejects_different_row_counts(sample_data, data_quality_library):
    with pytest.raises(AssertionError, match="Row count mismatch"):
        data_quality_library.check_count(sample_data, sample_data.iloc[:1])


@pytest.mark.example
def test_check_data_completeness_reports_mismatched_rows(
    sample_data, data_quality_library
):
    actual_data = sample_data.copy()
    actual_data.loc[0, "category"] = "changed"

    with pytest.raises(AssertionError, match="Data completeness mismatch"):
        data_quality_library.check_data_completeness(sample_data, actual_data)


@pytest.mark.example
def test_check_duplicates_rejects_repeated_grain(sample_data, data_quality_library):
    duplicate_data = pd.concat([sample_data, sample_data.iloc[[0]]], ignore_index=True)

    with pytest.raises(AssertionError, match="Duplicate values found"):
        data_quality_library.check_duplicates(duplicate_data, ["record_id"])


@pytest.mark.example
def test_check_not_null_values_reports_null_columns(
    sample_data, data_quality_library
):
    data_with_null = sample_data.copy()
    data_with_null.loc[0, "category"] = None

    with pytest.raises(AssertionError, match="Null values found"):
        data_quality_library.check_not_null_values(data_with_null, ["category"])


@pytest.mark.example
def test_parquet_reader_loads_nested_partition_files(tmp_path):
    partition_path = tmp_path / "category=alpha"
    partition_path.mkdir()
    pd.DataFrame({"record_id": [1, 2]}).to_parquet(
        partition_path / "part-0.parquet", index=False
    )

    actual_data = ParquetReader().process(tmp_path, include_subfolders=True)

    assert actual_data["record_id"].tolist() == [1, 2]


@pytest.mark.example
def test_postgres_connector_returns_dataframe_and_closes_connection():
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.description = [("record_id",), ("category",)]
    cursor.fetchall.return_value = [(1, "alpha")]
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with patch("psycopg2.connect", return_value=connection) as connect:
        with PostgresConnectorContextManager(
            db_user="user",
            db_password="password",
            db_host="localhost",
            db_name="database",
            db_port=5432,
        ) as connector:
            actual_data = connector.get_data_sql("SELECT 1")

    connect.assert_called_once_with(
        host="localhost",
        dbname="database",
        port=5432,
        user="user",
        password="password",
    )
    assert actual_data.to_dict(orient="records") == [
        {"record_id": 1, "category": "alpha"}
    ]
    connection.close.assert_called_once_with()


@pytest.mark.example
def test_postgres_connector_rolls_back_failed_query():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = RuntimeError("Query failed")
    connector = PostgresConnectorContextManager(
        db_user="user", db_password="unused", db_host="localhost",
        db_name="database", db_port=5432,
    )
    connector.connection = connection

    with pytest.raises(RuntimeError, match="Query failed"):
        connector.get_data_sql("SELECT invalid_column")

    connection.rollback.assert_called_once_with()
