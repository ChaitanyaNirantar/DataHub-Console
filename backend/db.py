"""
Storage layer for DataHub. SQLite for simplicity/portability; swapping
in Postgres later would only mean changing this module.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "datahub.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS github_repos (
    repo_id     INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    description TEXT,
    language    TEXT,
    stars       INTEGER NOT NULL,
    forks       INTEGER NOT NULL,
    open_issues INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    pushed_at   TEXT NOT NULL,
    license     TEXT,
    url         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repos_language ON github_repos(language);
CREATE INDEX IF NOT EXISTS idx_repos_stars ON github_repos(stars);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


def upsert_records(records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
    conn = get_conn()
    cols = list(records[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "repo_id")
    sql = f"""
        INSERT INTO github_repos ({', '.join(cols)}) VALUES ({placeholders})
        ON CONFLICT(repo_id) DO UPDATE SET {updates}
    """
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in records])
    conn.commit()
    n = conn.total_changes
    conn.close()
    return n


def query_repos(language: Optional[str] = None, min_stars: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM github_repos WHERE stars >= ?"
    params: List[Any] = [min_stars]
    if language:
        sql += " AND language = ?"
        params.append(language)
    sql += " ORDER BY stars DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def distinct_languages() -> List[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT language FROM github_repos WHERE language IS NOT NULL ORDER BY language"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def row_count() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM github_repos").fetchone()[0]
    conn.close()
    return n
