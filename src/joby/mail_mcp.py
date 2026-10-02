"""Serveur MCP intégré : accès en LECTURE SEULE à ta boîte mail via IMAP.

Il fonctionne avec Gmail, Outlook, iCloud, Proton (Bridge), OVH, Free... tout
fournisseur IMAP. Aucun outil n'envoie, ne supprime ni ne modifie de mail : la
boîte est ouverte en mode `readonly` et les messages ne sont même pas marqués
comme lus.

Identifiants : `user/.env` (JOBY_IMAP_HOST, JOBY_IMAP_PORT, JOBY_IMAP_USER,
JOBY_IMAP_PASSWORD). Lancement : `python -m joby.mail_mcp`.
"""

from __future__ import annotations

import email
import imaplib
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from mcp.server.mcpserver import MCPServer

from . import config

server = MCPServer("joby-mail", instructions="Accès en lecture seule à la boîte mail du candidat.")

MAX_BODY = 6000


def _connect() -> imaplib.IMAP4_SSL:
    env = config.read_env()
    conn = imaplib.IMAP4_SSL(env["JOBY_IMAP_HOST"], int(env.get("JOBY_IMAP_PORT", "993")))
    conn.login(env["JOBY_IMAP_USER"], env["JOBY_IMAP_PASSWORD"])
    return conn


def _dec(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _body(msg: email.message.Message) -> str:
    parts = msg.walk() if msg.is_multipart() else [msg]
    plain, html = "", ""
    for part in parts:
        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/plain" and not plain:
            plain = text
        elif part.get_content_type() == "text/html" and not html:
            html = text
    if not plain and html:
        import re
        plain = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", html))
        plain = re.sub(r"\s+", " ", plain)
    return plain.strip()[:MAX_BODY]


def _fetch(conn: imaplib.IMAP4_SSL, uid: bytes, with_body: bool) -> dict:
    what = "(BODY.PEEK[])" if with_body else "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])"
    _, data = conn.uid("fetch", uid, what)
    raw = data[0][1] if data and isinstance(data[0], tuple) else b""
    msg = email.message_from_bytes(raw)
    try:
        date = parsedate_to_datetime(msg.get("Date")).isoformat()
    except Exception:
        date = msg.get("Date", "")
    item = {"uid": uid.decode(), "message_id": msg.get("Message-ID", "").strip(), "date": date,
            "from": _dec(msg.get("From")), "subject": _dec(msg.get("Subject"))}
    if with_body:
        item["body"] = _body(msg)
    return item


@server.tool(description="Liste les mails reçus depuis une date (YYYY-MM-DD) dans la boîte de réception : "
                         "expéditeur, objet, date, uid. Ne modifie rien.")
def list_emails(since: str, limit: int = 100) -> list[dict]:
    try:
        day = datetime.fromisoformat(since)
    except ValueError:
        day = datetime.now() - timedelta(days=3)
    conn = _connect()
    try:
        conn.select("INBOX", readonly=True)
        _, data = conn.uid("search", None, "SINCE", day.strftime("%d-%b-%Y"))
        uids = (data[0] or b"").split()[-limit:]
        return [_fetch(conn, u, with_body=False) for u in reversed(uids)]
    finally:
        conn.logout()


@server.tool(description="Lit le contenu texte d'un mail à partir de son uid. Ne modifie rien.")
def read_email(uid: str) -> dict:
    conn = _connect()
    try:
        conn.select("INBOX", readonly=True)
        return _fetch(conn, uid.encode(), with_body=True)
    finally:
        conn.logout()


def check_connection() -> tuple[bool, str]:
    try:
        conn = _connect()
        conn.select("INBOX", readonly=True)
        conn.logout()
        return True, "Connexion réussie"
    except Exception as e:  # message affiché tel quel à l'utilisateur
        return False, str(e)


if __name__ == "__main__":
    server.run("stdio")
