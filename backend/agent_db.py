"""
Thin, safety-conscious data-access layer for the NL query agent.

The agent should NEVER get raw write access to the database. We:
  1) open the connection read-only,
  2) only permit statements that start with SELECT,
  3) run every query through sqlite3's parser so malformed/multi-statement
     injection attempts fail loudly instead of executing.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).parent.parent / "data" / "datahub.db"

SCHEMA_DESCRIPTION = """
Table: github_repos
Columns:
  repo_id      INTEGER, primary key
  full_name    TEXT   -- e.g. "huggingface/transformers"
  description  TEXT, nullable
  language     TEXT, nullable -- primary programming language
  stars        INTEGER
  forks        INTEGER
  open_issues  INTEGER
  created_at   TEXT   -- ISO 8601 timestamp
  pushed_at    TEXT   -- ISO 8601 timestamp, last push
  license      TEXT, nullable -- SPDX id, e.g. "MIT", "Apache-2.0"
  url          TEXT
"""


class UnsafeQueryError(Exception):
    pass


def _connect_readonly() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def is_select_only(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.lower().startswith("select"):
        return False
    forbidden = ("insert", "update", "delete", "drop", "alter", "attach", "pragma", "create", ";")
    lowered = stripped.lower()
    return not any(tok in lowered for tok in forbidden if tok != "select")


def run_safe_query(sql: str, row_limit: int = 200) -> List[Dict[str, Any]]:
    if not is_select_only(sql):
        raise UnsafeQueryError(f"Refusing to execute non-SELECT or multi-statement SQL: {sql!r}")
    conn = _connect_readonly()
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(row_limit)
        return [dict(r) for r in rows]
    finally:
        conn.close()
