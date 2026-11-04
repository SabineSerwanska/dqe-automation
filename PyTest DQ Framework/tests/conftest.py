import os

import pytest

from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import (
    PostgresConnectorContextManager,
)
from src.data_quality.data_quality_validation_library import DataQualityLibrary


def pytest_addoption(parser):
    parser.addoption(
        "--db_host",
        action="store",
        default=os.getenv("DB_HOST", "localhost"),
        help="PostgreSQL host",
    )
    parser.addoption(
        "--db_port",
        action="store",
        default=os.getenv("DB_PORT", "5434"),
        help="PostgreSQL port",
    )
    parser.addoption(
        "--db_name",
        action="store",
        default=os.getenv("DB_NAME", "mydatabase"),
        help="PostgreSQL database name",
    )
    parser.addoption(
        "--db_user",
        action="store",
        default=os.getenv("DB_USER"),
        help="PostgreSQL username",
    )
    parser.addoption(
        "--db_password",
        action="store",
        default=os.getenv("DB_PASSWORD"),
        help="PostgreSQL password",
    )


@pytest.fixture(scope="session")
def db_connection(request):
    db_user = request.config.getoption("--db_user")
    db_password = request.config.getoption("--db_password")
    if not db_user or not db_password:
        pytest.fail(
            "PostgreSQL credentials are required; provide --db_user and "
            "--db_password or set DB_USER and DB_PASSWORD."
        )

    connector = PostgresConnectorContextManager(
        db_user=db_user,
        db_password=db_password,
        db_host=request.config.getoption("--db_host"),
        db_name=request.config.getoption("--db_name"),
        db_port=request.config.getoption("--db_port"),
    )
    try:
        with connector as connection:
            yield connection
    except Exception as error:
        pytest.fail(f"Could not initialize PostgreSQL connection: {error}")


@pytest.fixture(scope="session")
def parquet_reader():
    return ParquetReader()


@pytest.fixture(scope="session")
def data_quality_library():
    return DataQualityLibrary()