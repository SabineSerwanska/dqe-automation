import csv
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def path_to_file():
	return Path(__file__).resolve().parents[1] / "src" / "data" / "data.csv"


@pytest.fixture(scope="session")
def csv_content(path_to_file):
	with path_to_file.open(newline="", encoding="utf-8") as csv_file:
		return list(csv.DictReader(csv_file))


@pytest.fixture(scope="session")
def actual_schema(path_to_file):
	with path_to_file.open(newline="", encoding="utf-8") as csv_file:
		return next(csv.reader(csv_file), [])


@pytest.fixture(scope="session")
def expected_schema():
	return ["id", "name", "age", "email", "is_active"]


@pytest.fixture(scope="session")
def schema_is_valid(actual_schema, expected_schema):
	return actual_schema == expected_schema


def pytest_collection_modifyitems(config, items):
	for item in items:
		if not list(item.iter_markers()):
			item.add_marker(pytest.mark.unmarked)
