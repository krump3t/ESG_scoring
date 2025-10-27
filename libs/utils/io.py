from typing import Dict, Any
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path

def write_parquet_table(table: pa.Table, path: str, partition_cols=None):
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    if partition_cols:
        pq.write_to_dataset(table, root_path=str(path_obj), partition_cols=partition_cols)
    else:
        pq.write_table(table, str(path_obj))

def dataframe_to_table(df: pd.DataFrame) -> pa.Table:
    return pa.Table.from_pandas(df, preserve_index=False)
