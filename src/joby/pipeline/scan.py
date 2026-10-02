"""Repérage des offres, uniquement sur les sites choisis par l'utilisateur.

- Sites « ats » : scanner CareerOps (API publiques, zéro token).
- Sites « browser » : Claude navigue sur la page comme un humain (moins souvent, c'est plus coûteux).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from .. import careerops, claude, config, db, mcp, paths
from . import models

BROWSE_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "url": {"type": "string"},
                           "location": {"type": "string"}},
            "required": ["title", "url"]}},
        "note": {"type": "string"},
    },
    "required": ["jobs"],
}


def _due(site: str, every_hours: float) -> bool:
    with db.connect() as c:
        row = c.execute("SELECT last_scan FROM site_scans WHERE site=?", (site,)).fetchone()
    if not row or not row["last_scan"]:
        return True
    last = datetime.fromisoformat(row["last_scan"])
    return datetime.now(timezone.utc) - last >= timedelta(hours=every_hours)


def _record(site: str, count: int, error: str | None = None) -> None:
    with db.connect() as c:
        c.execute("INSERT INTO site_scans(site, last_scan, last_count, last_error) VALUES (?,?,?,?) "
                  "ON CONFLICT(site) DO UPDATE SET last_scan=excluded.last_scan, last_count=excluded.last_count, "
                  "last_error=excluded.last_error", (site, db.now(), count, error))


def scan_ats() -> int:
    receipt = careerops.scan()
    for err in receipt.get("errors", []) or []:
        db.log("scan", f"Erreur de lecture : {err}")
    return receipt.get("imported", 0)


def scan_browser_sites() -> int:
    cfg = config.load()["pipeline"]
    total = 0
    for site in careerops.sites():
        if site.get("kind") != "browser" or not site.get("enabled", True):
            continue
        if not _due(site["name"], cfg["custom_sites_every_hours"]):
            continue
        try:
            res = claude.run(
                f"Careers page of {site['name']}: {site['url']}",
                system=claude.prompt_file("pipeline/browse.md"), model=models()["browse"],
                schema=BROWSE_SCHEMA, tools=mcp.BROWSER_TOOLS, mcp=mcp.browser(), timeout=1200)
        except claude.QuotaReached:
            raise
        except claude.ClaudeError as e:
            _record(site["name"], 0, str(e))
            db.log("scan", f"{site['name']} : lecture impossible ({e})")
            continue
        new = 0
        for job in res.data.get("jobs", []):
            url = urljoin(site["url"], job["url"])
            _, created = db.upsert_offer(url, company=site["name"], title=job["title"],
                                         location=job.get("location"), site=site["name"], source="navigateur")
            new += created
        _record(site["name"], len(res.data.get("jobs", [])), res.data.get("note"))
        total += new
    return total


def expire_old() -> int:
    """Les offres trop anciennes sont mises de côté sans dépenser de tokens."""
    max_days = config.load()["pipeline"]["max_offer_age_days"]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_days)).date().isoformat()
    with db.connect() as c:
        cur = c.execute("UPDATE offers SET status='expired', updated_at=? WHERE status='new' "
                        "AND posted_at IS NOT NULL AND posted_at <> '' AND posted_at < ?", (db.now(), cutoff))
        return cur.rowcount


def run() -> int:
    paths.CAREER_OPS_DATA.mkdir(parents=True, exist_ok=True)
    added = scan_ats() + scan_browser_sites()
    expired = expire_old()
    if added:
        db.log("scan", f"{added} nouvelle(s) offre(s) repérée(s)" + (f", {expired} trop ancienne(s)" if expired else ""))
    return added
