from collections import Counter
from pathlib import Path

import pandas as pd


REPORT_COLUMN_MAP = {
	"Facility Type": "facility_type",
	"Visit Date": "visit_date",
	"Average Time Spent": "avg_time_spent",
}
DATASET_COLUMNS = ["facility_type", "visit_date", "avg_time_spent"]


def get_file_uri(file_path):
	"""Return a browser-safe file URI for a local HTML report."""
	path = Path(file_path).expanduser().resolve()
	if not path.is_file():
		raise FileNotFoundError(f"HTML report does not exist: {path}")
	return path.as_uri()


def read_html_table_data(table_element):
	"""Read a Plotly-rendered HTML table WebElement into a DataFrame."""
	columns = table_element.find_elements("css selector", ".y-column")
	if not columns:
		raise ValueError("The located HTML table has no columns with class y-column")

	headers = []
	values_by_column = []
	for column in columns:
		header = column.find_element("id", "header").text.strip()
		headers.append(header)

		cells = column.find_elements("css selector", ".cell-text")
		values = []
		header_skipped = False
		for cell in cells:
			value = cell.text.strip()
			if not header_skipped and value == header:
				header_skipped = True
				continue
			values.append(value)
		values_by_column.append(values)

	row_counts = {len(values) for values in values_by_column}
	if len(row_counts) != 1:
		raise ValueError(
			"HTML table columns contain different numbers of rows: "
			f"{[len(values) for values in values_by_column]}"
		)

	return pd.DataFrame(
		{header: values for header, values in zip(headers, values_by_column)}
	)


def filter_dataframe_by_date(dataframe, filter_date, date_column="Visit Date"):
	"""Return rows matching YYYY-MM-DD in the selected date column."""
	column = (
		date_column
		if date_column in dataframe.columns
		else REPORT_COLUMN_MAP.get(date_column, date_column)
	)
	if column not in dataframe.columns:
		raise ValueError(
			f"Date column {date_column!r} was not found; "
			f"available columns: {list(dataframe.columns)}"
		)

	wanted_date = pd.to_datetime(filter_date, format="%Y-%m-%d", errors="raise").date()
	actual_dates = pd.to_datetime(dataframe[column], errors="coerce").dt.date
	return dataframe.loc[actual_dates == wanted_date].copy()


def read_partitioned_parquet(parquet_folder, filter_date=""):
	"""Read a partitioned Parquet dataset and optionally filter it by visit date."""
	dataset_path = Path(parquet_folder).expanduser().resolve()
	if not dataset_path.is_dir():
		raise FileNotFoundError(f"Parquet dataset folder does not exist: {dataset_path}")

	parquet_files = list(dataset_path.rglob("*.parquet"))
	if not parquet_files:
		raise FileNotFoundError(f"No Parquet files found under {dataset_path}")

	dataframe = pd.read_parquet(dataset_path, engine="pyarrow")
	if "partition_date" in dataframe.columns:
		dataframe = dataframe.drop(columns=["partition_date"])

	missing_columns = [
		column for column in DATASET_COLUMNS if column not in dataframe.columns
	]
	if missing_columns:
		raise ValueError(
			f"Parquet dataset is missing columns {missing_columns}; "
			f"available columns: {list(dataframe.columns)}"
		)

	if filter_date:
		dataframe = filter_dataframe_by_date(
			dataframe, filter_date, date_column="visit_date"
		)

	return dataframe[DATASET_COLUMNS].copy()


def compare_dataframes_exact(report_dataframe, parquet_dataframe):
	"""Compare report and Parquet rows as multisets; return mismatches."""
	report = report_dataframe.rename(columns=REPORT_COLUMN_MAP).copy()
	missing_report_columns = [
		column for column in DATASET_COLUMNS if column not in report.columns
	]
	missing_parquet_columns = [
		column for column in DATASET_COLUMNS if column not in parquet_dataframe.columns
	]
	if missing_report_columns or missing_parquet_columns:
		raise ValueError(
			"Column mismatch before comparison: "
			f"missing from report={missing_report_columns}; "
			f"missing from Parquet={missing_parquet_columns}"
		)

	report = report[DATASET_COLUMNS]
	parquet = parquet_dataframe[DATASET_COLUMNS].copy()

	for dataframe in (report, parquet):
		dataframe["facility_type"] = dataframe["facility_type"].astype("string").str.strip()
		dataframe["visit_date"] = (
			pd.to_datetime(dataframe["visit_date"], errors="raise")
			.dt.strftime("%Y-%m-%d")
		)
		dataframe["avg_time_spent"] = pd.to_numeric(
			dataframe["avg_time_spent"], errors="raise"
		).round(2)

	def row_counts(dataframe):
		return Counter(
			tuple(row)
			for row in dataframe.itertuples(index=False, name=None)
		)

	report_rows = row_counts(report)
	parquet_rows = row_counts(parquet)
	missing_rows = list((report_rows - parquet_rows).elements())
	unexpected_rows = list((parquet_rows - report_rows).elements())

	missing_dataframe = pd.DataFrame(missing_rows, columns=DATASET_COLUMNS)
	unexpected_dataframe = pd.DataFrame(unexpected_rows, columns=DATASET_COLUMNS)
	summary = (
		f"Exact match: {not missing_rows and not unexpected_rows}. "
		f"Rows missing from Parquet: {len(missing_rows)}; "
		f"unexpected Parquet rows: {len(unexpected_rows)}. "
		f"Missing examples: {missing_rows[:10]}. "
		f"Unexpected examples: {unexpected_rows[:10]}"
	)

	return {
		"matches": not missing_rows and not unexpected_rows,
		"missing_from_parquet": missing_dataframe,
		"unexpected_in_parquet": unexpected_dataframe,
		"summary": summary,
	}
