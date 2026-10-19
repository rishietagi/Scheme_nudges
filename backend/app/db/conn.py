"""SQLite connections.

Main database = runs.sqlite (run tables, created by the app). The provided Day-0 world is ATTACHed read-only as `world`,
so app queries read `world.distributors` etc. and can join run tables in plain SQL. The world file is never written.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import settings

SCHEMA = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 4          # bump when run tables change shape: older runs.sqlite files are rebuilt (they hold only runs)


def connect(runs_db: Path | None = None) -> sqlite3.Connection:
    path = runs_db or settings.runs_db
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("ATTACH DATABASE ? AS world", (f"file:{settings.world_db.as_posix()}?mode=ro",))
    if con.execute("PRAGMA main.user_version").fetchone()[0] < SCHEMA_VERSION:
        for (name,) in con.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall():
            con.execute(f'DROP TABLE IF EXISTS main."{name}"')
        con.execute(f"PRAGMA main.user_version = {SCHEMA_VERSION}")
    if SCHEMA.exists():
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
    return con


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()
