"""Suivi des réponses : Claude lit ta boîte (lecture seule) et rattache chaque mail à sa candidature."""

from __future__ import annotations

from datetime import date, timedelta

from .. import claude, config, db, mcp
from . import models

MAIL_SCHEMA = {
    "type": "object",
    "properties": {"emails": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "application_id": {"type": ["integer", "null"]},
            "category": {"type": "string", "enum": ["acknowledged", "interview", "rejected", "offer", "other"]},
            "message_id": {"type": "string"},
            "date": {"type": "string"},
            "sender": {"type": "string"},
            "subject": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["application_id", "category", "message_id", "sender", "subject", "summary"]}}},
    "required": ["emails"],
}

TRACKED = ("applied", "acknowledged", "interview", "needs_you", "approved")


def run() -> int:
    cfg = config.load()
    server = mcp.mail()
    if not server:
        return 0
    apps = db.offers(TRACKED)
    if not apps:
        return 0
    since = cfg["mail"].get("last_check") or (date.today() - timedelta(days=7)).isoformat()
    listing = "\n".join(f"- id {o['id']}: {o['company']} — {o['title']} (applied {(o['applied_at'] or '')[:10]})"
                        for o in apps)
    res = claude.run(f"Check emails received since {since}.\n\n<applications>\n{listing}\n</applications>",
                     system=claude.prompt_file("pipeline/mail.md"), model=models()["mail"], schema=MAIL_SCHEMA,
                     tools=mcp.MAIL_TOOLS, mcp=server, timeout=900)
    ids = {o["id"]: o for o in apps}
    matched = 0
    for m in res.data["emails"]:
        with db.connect() as c:
            if c.execute("SELECT 1 FROM mails WHERE message_id=?", (m["message_id"],)).fetchone():
                continue
            c.execute("INSERT INTO mails(message_id, offer_id, received_at, sender, subject, category, summary) "
                      "VALUES (?,?,?,?,?,?,?)", (m["message_id"], m["application_id"] if m["application_id"] in ids else None,
                                                 m.get("date"), m["sender"], m["subject"], m["category"], m["summary"]))
        o = ids.get(m["application_id"])
        if not o:
            continue
        matched += 1
        new = m["category"]
        if new in db.REPLY_RANK and db.REPLY_RANK[new] > db.REPLY_RANK.get(o["status"], -1):
            db.set_offer(o["id"], status=new)
        db.log("mail", f"{db.label(new) if new != 'other' else '✉️ Mail'} — {o['company']} : {m['summary']}", o["id"])
    config.update(mail={"last_check": date.today().isoformat()})
    return matched
