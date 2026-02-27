# src/pipelines/load_staging_from_api.py
from __future__ import annotations

import logging
from typing import Final

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from src.ingestion.api_client import fetch_all
from src.utils.database import get_engine

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logger = logging.getLogger(__name__)

# If you already configure logging elsewhere (recommended), remove this block.
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------
DEFAULT_PAGE_SIZE: Final[int] = 500
DEFAULT_CHUNK_SIZE: Final[int] = 1000


def _split_schema_table(full_name: str) -> tuple[str, str]:
    """
    Splits 'schema.table' into ('schema', 'table').

    Raises ValueError if format is invalid.
    """
    parts = full_name.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Expected table_name in 'schema.table' format, got: {full_name!r}"
        )
    return parts[0], parts[1]


def _truncate_or_delete(conn: Connection, schema: str, table: str) -> None:
    """
    Try TRUNCATE first (fast). If not allowed (FK/permissions), fallback to DELETE.
    Uses specific SQLAlchemy/DB exceptions to avoid "too broad exception clause".
    """
    # NOTE: parameterizing identifiers isn't supported; these are internal constants
    # you control (not user input). Keep them controlled.
    truncate_sql = text(f"TRUNCATE TABLE [{schema}].[{table}];")
    delete_sql = text(f"DELETE FROM [{schema}].[{table}];")

    try:
        conn.execute(truncate_sql)
        logger.info("Truncated %s.%s", schema, table)
    except (DBAPIError, SQLAlchemyError) as exc:
        logger.warning(
            "TRUNCATE failed for %s.%s; falling back to DELETE. Reason: %s",
            schema,
            table,
            exc,
        )
        conn.execute(delete_sql)
        logger.info("Deleted rows from %s.%s", schema, table)


def load_table(
    table_name: str,
    endpoint: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """
    Pull data from a REST endpoint and load into a SQL Server staging table.

    Current strategy: full refresh (truncate/delete + append load).
    """
    schema, table = _split_schema_table(table_name)

    rows = fetch_all(endpoint, page_size=page_size)
    df = pd.DataFrame(rows)

    if df.empty:
        logger.warning("No rows returned for endpoint=%s. Skipping %s.", endpoint, table_name)
        return 0

    engine = get_engine()

    # Using engine.begin() returns a proper context manager and auto-commits/rolls back.
    with engine.connect() as conn:
        with conn.begin():
            _truncate_or_delete(conn, schema=schema, table=table)

        # pandas uses parameter name `chunk size` (no underscore)
        df.to_sql(
            name=table,
            schema=schema,
            con=conn,  # Connection is fine
            if_exists="append",
            index=False,
            chunksize=chunk_size,
            method="multi",
        )

    logger.info(
        "Loaded %s rows into %s from %s (cols=%s, chunk_size=%s)",
        f"{len(df):,}",
        table_name,
        endpoint,
        len(df.columns),
        chunk_size,
    )
    return int(len(df))


def main() -> None:
    load_table("staging.devices", "/devices", page_size=500, chunk_size=200)
    load_table("staging.incidents", "/incidents", page_size=500, chunk_size=250)
    load_table("staging.lifecycle_events", "/lifecycle-events", page_size=500, chunk_size=285)


if __name__ == "__main__":
    main()