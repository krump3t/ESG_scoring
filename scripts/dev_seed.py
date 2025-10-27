from libs.data.schemas import chunks_schema
from libs.utils.io import write_parquet_table
import pyarrow as pa

def main():
    schema = chunks_schema()
    data = [
        ("Acme-2024-1","Acme Corp",2024,"Acme 2024 ESG strategy and targets.",1,1,"Executive Summary","https://example.com/acme-2024.pdf","md5a"),
        ("Acme-2024-2","Acme Corp",2024,"GHG inventory includes Scopes 1 and 2.",2,2,"GHG Accounting","https://example.com/acme-2024.pdf","md5b"),
    ]
    cols = list(zip(*data))
    table = pa.table(cols, schema=schema)
    write_parquet_table(table, "artifacts/chunks.parquet")

if __name__ == "__main__":
    main()
