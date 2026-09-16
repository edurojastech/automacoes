"""Historico de conversas por paciente, em SQLite local.

Guarda so o necessario para dar contexto de curto prazo ao agente (as
ultimas N mensagens). O Google Calendar continua sendo a fonte da verdade
para agendamentos.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import config

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id TEXT NOT NULL,
    wa_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_clinic_wa
    ON messages (clinic_id, wa_id, id);
"""


def _connect() -> sqlite3.Connection:
    db_path = Path(config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(_SCHEMA)


def append_message(clinic_id: str, wa_id: str, role: str, content: str) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO messages (clinic_id, wa_id, role, content) VALUES (?, ?, ?, ?)",
            (clinic_id, wa_id, role, content),
        )


def get_recent_history(clinic_id: str, wa_id: str, limit: int = 20) -> list[dict]:
    """Retorna as ultimas `limit` mensagens (role, content) em ordem cronologica."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, id FROM messages
                WHERE clinic_id = ? AND wa_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (clinic_id, wa_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)
