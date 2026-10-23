---
name: generate-parquet-dq-tests
description: "Use when explicitly asked to generate a PyTest DQ module for a Parquet dataset from the project mapping. Creates one dataset test module and refuses to rewrite framework, Jenkins, or pytest configuration."
disable-model-invocation: true
---

# Generate Parquet DQ tests

Complete this skill as **Step 2** of the PyTest DQ assignment. Read first:

- `PyTest DQ Framework/docs/test-automation-strategy.md` — **§5 Skill contract**, **§6 Test design standard**
- `docs/parquet-aggregated-data-mapping.md` — dataset definitions (expected SQL comes from here)

**Do not** paste expected SQL for the three named datasets into this skill.  
**Do not** instruct the agent to copy SQL from `data_dev/`.

Before using the skill to generate tests, run the **Skill review** checklist.

## When this skill applies

Invoke this skill explicitly in Copilot Agent for **Step 3** of the PyTest DQ assignment, after the framework and this skill have been reviewed. It generates exactly one dataset test module at `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`.

The framework must already provide the fixtures and library methods listed in the test design standard. Do not edit framework modules, `conftest.py`, `pytest.ini`, requirements, Jenkins, or files outside the output module. If the mapping is missing, incomplete, or does not define the requested dataset, stop and ask for clarification instead of guessing.

## Inputs you must have

1. Dataset name, matching a folder under `/parquet_data/` and a section in `docs/parquet-aggregated-data-mapping.md`.
2. Mapping details for that dataset: target columns, grain, source tables and columns, joins, measures, and any stated filters.
3. Author and requirement identifier for the module header, when provided. Otherwise keep explicit neutral placeholders rather than inventing a person or ticket.

Read `PyTest DQ Framework/docs/test-automation-strategy.md` sections 5 and 6, the framework design, and the mapping before writing the module. If any required mapping detail is absent, ask instead of consulting ETL implementation code.

## Hard rules

1. Create exactly one file at `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`; do not combine datasets.
2. Treat PostgreSQL as `source_data` (expected) and Parquet as `target_data` (actual). Never reverse these roles.
3. Derive expected SQL only from `docs/parquet-aggregated-data-mapping.md`. Do not read or copy SQL from `data_dev/`, `queries.py`, or Parquet loader code.
4. Keep this skill dataset-agnostic. Never put concrete expected SQL for any named dataset in this file.
5. Match every selected source column, alias, join, grouping dimension, measure, and mapping-defined filter to the mapping. Do not add pipeline-only filters, unions, case expressions, or sign changes.
6. Use the existing fixtures `db_connection`, `parquet_reader`, and `data_quality_library` and only the library methods in TAS §6.4. Do not reimplement pandas checks inside a generated test.
7. Read the target from `/parquet_data/<dataset_name>` with `include_subfolders=True`.
8. Generate smoke, completeness, count, uniqueness, and not-null tests. Use grain columns for uniqueness and all mapped target columns for not-null checks.
9. Mark every generated test with `parquet_data` and the dataset-specific mark. Add `smoke` only to the non-empty smoke test.
10. Never weaken or change expected SQL to make a test pass. Report mismatches as mapping-versus-Parquet or transformation defects.

## Workflow

1. Confirm the dataset name and find its mapping section; stop if it is absent.
2. Extract its target schema, grain, source tables, join keys, measures, and only the filters written in the mapping.
3. Independently derive a PostgreSQL `SELECT`: join the mapped tables, select each target dimension and measure, alias columns to target names, and group by the mapped grain.
4. Create the module using the template below. Replace every placeholder for the selected dataset without changing the fixture direction or library API.
5. Set the target path to `/parquet_data/<dataset_name>`, pass `include_subfolders=True`, and use mapped grain columns and target column names in the DQ calls.
6. Add all required markers and descriptive assertion context through the library methods.
7. Review the generated SQL and module against the mapping and self-review checklist. Do not edit any other file.

## Template

Use this full module skeleton. The SQL placeholder is intentionally generic; derive the actual query only from the selected mapping.

```python
"""
Description: Data Quality checks for <dataset_name> dataset.
Requirement(s): <requirement_id>
Author(s): <author>
"""

import pytest


@pytest.fixture(scope="module")
def source_data(db_connection):
  source_query = """
  -- Derive this query from the selected mapping only.
  """
  return db_connection.get_data_sql(source_query)


@pytest.fixture(scope="module")
def target_data(parquet_reader):
  target_path = "/parquet_data/<dataset_name>"
  return parquet_reader.process(target_path, include_subfolders=True)


@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.<dataset_name>
def test_check_dataset_is_not_empty(target_data, data_quality_library):
  data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_data_completeness(source_data, target_data, data_quality_library):
  data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_count(source_data, target_data, data_quality_library):
  data_quality_library.check_count(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_uniqueness(target_data, data_quality_library):
  data_quality_library.check_duplicates(target_data, ["<grain_column_1>"])


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_not_null_values(target_data, data_quality_library):
  data_quality_library.check_not_null_values(
    target_data, ["<mapped_column_1>", "<mapped_column_2>"]
  )
```

## SQL derivation (generic)

Use mapping-defined source tables and join keys. Select the mapped dimensions at the mapped grain, derive measures with the stated aggregate, and alias every expression to its target column name. Apply rounding, date conversion, name formatting, or filters only when explicitly required by the mapping. Group by all mapped dimensions. Keep this guidance generic; dataset-specific SQL belongs only in its generated test module.

## After generation

Run pytest only when asked or when execution is part of the active assignment. A missing local dataset or unavailable database is an environment blocker, not permission to replace source or target data with mocks. Preserve failed DQ results and explain them against the mapping; never rewrite expected SQL just to obtain a green run.

---

## Skill review (self-check before Step 3)

- [x] Contains no concrete expected SQL for any named dataset.
- [x] Does not tell the agent to use `data_dev/` or Parquet loader SQL.
- [x] Requires completeness, count, uniqueness, not-null, and smoke checks.
- [x] Keeps PostgreSQL as expected source and Parquet as actual target; checks use the shared DQ library.
- [x] Contains no unfinished placeholder sections.
