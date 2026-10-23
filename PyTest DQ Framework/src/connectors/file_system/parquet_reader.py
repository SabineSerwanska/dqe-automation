from pathlib import Path

import pandas as pd


class ParquetReader:
	def process(self, path, include_subfolders=False):
		dataset_path = Path(path)
		if not dataset_path.exists():
			raise FileNotFoundError(f"Parquet path does not exist: {dataset_path}")

		if dataset_path.is_file():
			return pd.read_parquet(dataset_path, engine="pyarrow", partitioning=None)

		pattern = "**/*.parquet" if include_subfolders else "*.parquet"
		parquet_files = sorted(dataset_path.glob(pattern))
		if not parquet_files:
			raise FileNotFoundError(
				f"No Parquet files found under {dataset_path}"
			)

		if include_subfolders:
			return pd.read_parquet(dataset_path, engine="pyarrow", partitioning=None)

		return pd.concat(
			[pd.read_parquet(file_path, engine="pyarrow", partitioning=None) for file_path in parquet_files],
			ignore_index=True,
		)
