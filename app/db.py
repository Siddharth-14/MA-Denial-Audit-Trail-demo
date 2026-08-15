"""SQLite connection and read helpers for the claims decision-trace store."""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "claims.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_claims(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM claims", conn)


def get_claim_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT claim_id FROM claims ORDER BY claim_id").fetchall()
    return [r["claim_id"] for r in rows]


def get_claim_by_id(conn: sqlite3.Connection, claim_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    return dict(row) if row else None
