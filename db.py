# db.py — SQLite persistence for submissions.
# Uses the stdlib sqlite3 module with hand-written SQL on purpose:
# this project doubles as a SQL exercise.
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")

COLUMNS = ("id", "original", "revised", "explanation", "model", "created_at")


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                original    TEXT NOT NULL,
                revised     TEXT NOT NULL,
                explanation TEXT NOT NULL,
                model       TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )


def save_submission(original: str, revised: str, explanation: str, model: str) -> int:
    created_at = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO submissions (original, revised, explanation, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (original, revised, explanation, model, created_at),
        )
        return cur.lastrowid


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(zip(COLUMNS, row)) for row in rows]


def list_submissions(limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT id, original, revised, explanation, model, created_at
            FROM submissions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return _rows_to_dicts(rows)


def get_submission(sub_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute(
            """
            SELECT id, original, revised, explanation, model, created_at
            FROM submissions
            WHERE id = ?
            """,
            (sub_id,),
        ).fetchone()
    return dict(zip(COLUMNS, row)) if row else None
