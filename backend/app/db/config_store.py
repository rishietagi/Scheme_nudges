"""Business configuration saved from the Set-up pages (cohort rules, survey). The yaml rule files are the defaults;
a row here overrides them. Saved config applies from the next cycle: every run snapshots what it used at Reset."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def get_config(con: sqlite3.Connection, key: str) -> dict | None:
    row = con.execute("SELECT json FROM config WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def saved_at(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("SELECT saved_at FROM config WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def put_config(con: sqlite3.Connection, key: str, value: dict) -> None:
    con.execute("INSERT OR REPLACE INTO config VALUES (?,?,?)",
                (key, json.dumps(value, ensure_ascii=False, sort_keys=True), datetime.now(timezone.utc).isoformat()))


def clear_config(con: sqlite3.Connection, key: str) -> None:
    con.execute("DELETE FROM config WHERE key = ?", (key,))
