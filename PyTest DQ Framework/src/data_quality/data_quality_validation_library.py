from collections import Counter
from datetime import date, datetime
from decimal import Decimal

import pandas as pd


class DataQualityLibrary:
    """Reusable assertions for source and target pandas DataFrames."""

    @staticmethod
    def _normalise_value(value):
        if pd.isna(value):
            return None
        if isinstance(value, (pd.Timestamp, datetime)):
            if (
                value.hour,
                value.minute,
                value.second,
                value.microsecond,
                getattr(value, "nanosecond", 0),
            ) == (0, 0, 0, 0, 0):
                return value.date().isoformat()
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "item"):
            return value.item()
        return value

    @classmethod
    def _rows_as_multiset(cls, dataframe):
        return Counter(
            tuple(cls._normalise_value(value) for value in row)
            for row in dataframe.itertuples(index=False, name=None)
        )

    @staticmethod
    def check_dataset_is_not_empty(dataframe):
        assert dataframe is not None and not dataframe.empty, (
            "Expected the Parquet dataset to contain at least one row"
        )

    @staticmethod
    def check_count(df_expected, df_actual):
        expected_count = len(df_expected)
        actual_count = len(df_actual)
        assert expected_count == actual_count, (
            f"Row count mismatch: expected {expected_count}, got {actual_count}"
        )

    @classmethod
    def check_data_completeness(cls, df_expected, df_actual):
        expected_columns = list(df_expected.columns)
        actual_columns = list(df_actual.columns)
        missing_columns = [
            column for column in expected_columns if column not in actual_columns
        ]
        unexpected_columns = [
            column for column in actual_columns if column not in expected_columns
        ]
        assert not missing_columns and not unexpected_columns, (
            f"Column mismatch: missing {missing_columns}; "
            f"unexpected {unexpected_columns}"
        )

        expected_rows = cls._rows_as_multiset(df_expected)
        actual_rows = cls._rows_as_multiset(df_actual[expected_columns])
        missing_rows = list((expected_rows - actual_rows).elements())[:5]
        unexpected_rows = list((actual_rows - expected_rows).elements())[:5]
        assert expected_rows == actual_rows, (
            "Data completeness mismatch: "
            f"missing rows (up to 5): {missing_rows}; "
            f"unexpected rows (up to 5): {unexpected_rows}"
        )

    @staticmethod
    def check_duplicates(dataframe, column_names=None):
        columns = column_names or list(dataframe.columns)
        missing_columns = [column for column in columns if column not in dataframe]
        assert not missing_columns, (
            f"Cannot check uniqueness; columns are missing: {missing_columns}"
        )

        duplicate_rows = dataframe[dataframe.duplicated(subset=columns, keep=False)]
        assert duplicate_rows.empty, (
            f"Duplicate values found for columns {columns}: "
            f"{duplicate_rows.head(5).to_dict(orient='records')}"
        )

    @staticmethod
    def check_not_null_values(dataframe, column_names=None):
        columns = column_names or list(dataframe.columns)
        missing_columns = [column for column in columns if column not in dataframe]
        assert not missing_columns, (
            f"Cannot check nulls; columns are missing: {missing_columns}"
        )

        null_counts = {
            column: int(dataframe[column].isna().sum())
            for column in columns
            if dataframe[column].isna().any()
        }
        assert not null_counts, f"Null values found by column: {null_counts}"
