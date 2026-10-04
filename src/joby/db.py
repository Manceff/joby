"""Base SQLite partagée entre l'agent et le dashboard (`user/joby.db`)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from . import paths

# Statut interne -> (libellé affiché, emoji). L'ordre est celui du parcours.
STATUSES: dict[str, tuple[str, str]] = {
    "new": ("Repérée", "🔎"),
    "shortlisted": ("Retenue, dossier en préparation", "✍️"),
    "ready": ("À valider", "👀"),
    "approved": ("Validée, envoi en cours", "🚀"),
    "needs_you": ("Action requise", "✋"),
    "applied": ("Envoyée", "📨"),
    "acknowledged": ("Accusé de réception", "📬"),
    "interview": ("Entretien", "🗓️"),
    "offer": ("Offre reçue", "🎉"),
    "rejected": ("Refus", "🌧️"),
    "discarded": ("Écartée par l'agent", "🗂️"),
    "declined": ("Écartée par toi", "🙅"),
    "expired": ("Expirée", "⌛"),
    "failed": ("Échec technique", "⚠️"),
}

# Après l'envoi, un statut ne peut qu'avancer dans ce sens (un mail ne fait pas reculer une candidature).
REPLY_RANK = {"applied": 0, "acknowledged": 1, "interview": 2, "rejected": 3, "offer": 4}

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id              INTEGER PRIMARY KEY,
    url             TEXT NOT NULL UNIQUE,
    company         TEXT,
    title           TEXT,
    location        TEXT,
    site            TEXT,
    source          TEXT,
    posted_at       TEXT,
    found_at        TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',
    prescreen       TEXT,
    prescreen_note  TEXT,
    jd_text         TEXT,
    score           REAL,
    fit_summary     TEXT,
    analysis        TEXT,
    language        TEXT,
    dossier_dir     TEXT,
    cv_pdf          TEXT,
    letter_pdf      TEXT,
    dossier_notes   TEXT,
    user_feedback   TEXT,
    approved_at     TEXT,
    applied_at      TEXT,
    apply_report    TEXT,
    pending_questions TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    sector          TEXT,
    had_interview   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS offers_status ON offers(status);

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY,
    ts        TEXT NOT NULL,
    offer_id  INTEGER REFERENCES offers(id),
    kind      TEXT NOT NULL,
    message   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS mails (
    id          INTEGER PRIMARY KEY,
    message_id  TEXT UNIQUE,
    offer_id    INTEGER REFERENCES offers(id),
    received_at TEXT,
    sender      TEXT,
    subject     TEXT,
    category    TEXT,
    summary     TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    ok          INTEGER,
    summary     TEXT
);

CREATE TABLE IF NOT EXISTS site_scans (
    site        TEXT PRIMARY KEY,
    last_scan   TEXT,
    last_count  INTEGER,
    last_error  TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# Colonnes ajoutées après la première version : les bases existantes sont mises à niveau en place.
MIGRATIONS = {
    "sector": "ALTER TABLE offers ADD COLUMN sector TEXT",
    "had_interview": "ALTER TABLE offers ADD COLUMN had_interview INTEGER NOT NULL DEFAULT 0",
}


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
    for col, sql in MIGRATIONS.items():
        if col not in cols:
            conn.execute(sql)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    paths.DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(paths.DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log(kind: str, message: str, offer_id: int | None = None) -> None:
    with connect() as c:
        c.execute("INSERT INTO events(ts, offer_id, kind, message) VALUES (?,?,?,?)",
                  (now(), offer_id, kind, message))


def upsert_offer(url: str, **fields: Any) -> tuple[int, bool]:
    """Insère une offre si l'URL est nouvelle. Renvoie (id, créée?)."""
    with connect() as c:
        row = c.execute("SELECT id FROM offers WHERE url=?", (url,)).fetchone()
        if row:
            return row["id"], False
        ts = now()
        cols = ["url", "found_at", "updated_at", *fields.keys()]
        vals = [url, ts, ts, *fields.values()]
        cur = c.execute(f"INSERT INTO offers({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
        return cur.lastrowid, True


def set_offer(offer_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = now()
    if fields.get("status") in ("interview", "offer"):
        fields["had_interview"] = 1  # un entretien reste acquis même si un refus suit
    for k, v in list(fields.items()):
        if isinstance(v, (dict, list)):
            fields[k] = json.dumps(v, ensure_ascii=False)
    sets = ", ".join(f"{k}=?" for k in fields)
    with connect() as c:
        c.execute(f"UPDATE offers SET {sets} WHERE id=?", [*fields.values(), offer_id])


def offers(status: str | tuple[str, ...] | None = None, limit: int | None = None,
           order: str = "found_at ASC") -> list[sqlite3.Row]:
    q, args = "SELECT * FROM offers", []
    if status:
        sts = (status,) if isinstance(status, str) else status
        q += f" WHERE status IN ({','.join('?' * len(sts))})"
        args.extend(sts)
    q += f" ORDER BY {order}"
    if limit:
        q += f" LIMIT {int(limit)}"
    with connect() as c:
        return c.execute(q, args).fetchall()


def offer(offer_id: int) -> sqlite3.Row | None:
    with connect() as c:
        return c.execute("SELECT * FROM offers WHERE id=?", (offer_id,)).fetchone()


def counts() -> dict[str, int]:
    with connect() as c:
        return {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM offers GROUP BY status")}


def label(status: str) -> str:
    name, emoji = STATUSES.get(status, (status, "•"))
    return f"{emoji} {name}"
