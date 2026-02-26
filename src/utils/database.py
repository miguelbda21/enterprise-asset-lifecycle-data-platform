# src/db_connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def get_engine() -> Engine:
    """
    Returns a singleton SQLAlchemy engine for SQL Server.
    """
    global _engine
    if _engine is not None:
        return _engine

    load_dotenv()  # loads .env

    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    driver = os.getenv("DB_DRIVER")

    if not all([server, database, username, password, driver]):
        raise ValueError("❌ Missing DB_SERVER/DB_NAME/DB_USERNAME/DB_PASSWORD/DB_DRIVER in .env")

    conn_str = (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}"
        f"?driver={driver.replace(' ', '+')}"
    )

    _engine = create_engine(conn_str, fast_executemany=True)
    return _engine