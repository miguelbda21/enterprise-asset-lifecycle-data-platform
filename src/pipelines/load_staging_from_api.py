# src/pipelines/load_staging_from_api.py
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.ingestion.api_client import fetch_all
from src.utils.database import get_engine


def _auto_chunk_size(df: pd.DataFrame, max_params: int = 2000, min_chunk: int = 1) -> int:
    """
    SQL Server has ~2100 parameter limit per statement.
    With pandas.to_sql(method="multi"), params ~= rows_in_chunk * num_columns.
    We pick: floor(max_params / num_columns), with some headroom.
    """
    num_cols = int(df.shape[1])
    if num_cols <= 0:
        return min_chunk

    chunk = max_params // num_cols
    return max(min_chunk, int(chunk))


def load_table(table_name: str, endpoint: str, page_size: int = 500) -> int:
    """
    Pulls data from REST endpoint and loads into a SQL Server staging table.
    Full refresh approach: TRUNCATE (or DELETE fallback) + INSERT.
    """
    rows = fetch_all(endpoint, page_size=page_size)
    df = pd.DataFrame(rows)

    if df.empty:
        print(f"⚠️ No rows returned for {endpoint}. Skipping {table_name}.")
        return 0

    # Automatic chunk sizing to avoid SQL Server parameter-limit failures
    chunk_size = _auto_chunk_size(df, max_params=2000, min_chunk=1)

    # Expect "schema.table"
    schema, tbl = table_name.split(".", 1)

    engine = get_engine()

    # Use engine.connect() + conn.begin() to keep typing/lint happy
    with engine.connect() as conn:
        with conn.begin():
            try:
                conn.execute(text(f"TRUNCATE TABLE {schema}.{tbl};"))
            except (ProgrammingError, DBAPIError):
                conn.execute(text(f"DELETE FROM {schema}.{tbl};"))

            df.to_sql(
                name=tbl,
                schema=schema,
                con=conn,
                if_exists="append",
                index=False,
                chunksize=chunk_size,
                method="multi",
            )

    print(
        f"✅ Loaded {len(df):,} rows into {table_name} from {endpoint} "
        f"(cols={df.shape[1]}, chunk_size={chunk_size})"
    )
    return int(len(df))


def main() -> None:
    load_table("staging.devices", "/devices")
    load_table("staging.incidents", "/incidents")
    load_table("staging.lifecycle_events", "/lifecycle-events")


if __name__ == "__main__":
    main()