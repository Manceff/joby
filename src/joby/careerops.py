"""Intégration avec CareerOps (sous-module `vendor/career-ops`).

Joby réutilise le scanner de CareerOps (plus de 100 ATS lus via leurs API, sans
consommer un seul token), son extracteur d'offres et ses règles d'écriture.
Toutes les données CareerOps de l'utilisateur vivent dans `user/careerops/`.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from . import config, db, paths


class CareerOpsMissing(RuntimeError):
    pass


def _node_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["CAREER_OPS_ROOT"] = str(root)
    return env


def check_installed() -> None:
    if not (paths.CAREER_OPS / "scan.mjs").exists():
        raise CareerOpsMissing("CareerOps est absent. Lance : git submodule update --init")
    if not (paths.CAREER_OPS / "node_modules").exists():
        raise CareerOpsMissing("Dépendances CareerOps absentes. Lance : ./install.sh")


def sites() -> list[dict[str, Any]]:
    return (config.read_yaml(paths.SITES, {}) or {}).get("sites", [])


def _portals(entries: list[dict[str, Any]]) -> dict[str, Any]:
    kw = config.read_yaml(paths.SEARCH_KEYWORDS, {}) or {}
    portals: dict[str, Any] = {
        # Le tri fin est fait par l'IA ; ici on n'exclut que ce que tu as explicitement refusé.
        "title_filter": {"positive": [], "negative": kw.get("titles_negative", [])},
        "tracked_companies": [
            {"name": s["name"], "careers_url": s["url"], "enabled": True} for s in entries
        ],
    }
    return portals


def write_portals() -> Path:
    paths.CAREER_OPS_DATA.mkdir(parents=True, exist_ok=True)
    target = paths.CAREER_OPS_DATA / "portals.yml"
    ats = [s for s in sites() if s.get("kind") == "ats" and s.get("enabled", True)]
    target.write_text("# Généré par Joby à partir de user/profile/sites.yml — ne pas modifier.\n"
                      + yaml.safe_dump(_portals(ats), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return target


def _scan(root: Path, extra: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["node", "scan.mjs", "--json", "--quiet", *extra], cwd=paths.CAREER_OPS,
                          env=_node_env(root), capture_output=True, text=True, timeout=1800)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Le scanner CareerOps a échoué : {proc.stderr.strip()[-400:]}")


def probe(name: str, url: str) -> dict[str, Any]:
    """Teste un site : CareerOps sait-il le lire directement ? Combien d'offres ?"""
    check_installed()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "portals.yml").write_text(yaml.safe_dump(
            {"title_filter": {"positive": [], "negative": []},
             "tracked_companies": [{"name": name, "careers_url": url, "enabled": True}]}), encoding="utf-8")
        receipt = _scan(root, ["--dry-run"])
    supported = receipt.get("scanned", 0) > 0
    return {
        "name": name,
        "url": url,
        "kind": "ats" if supported else "browser",
        "offers_found": receipt.get("found", 0) if supported else None,
        "errors": receipt.get("errors", []),
    }


def scan() -> dict[str, Any]:
    """Scan sans IA de tous les sites « ats », puis import des nouvelles offres dans Joby."""
    check_installed()
    if not any(s.get("kind") == "ats" for s in sites()):
        return {"added": 0, "imported": 0}
    write_portals()
    receipt = _scan(paths.CAREER_OPS_DATA, [])
    receipt["imported"] = import_history()
    return receipt


def import_history() -> int:
    history = paths.CAREER_OPS_DATA / "data" / "scan-history.tsv"
    if not history.exists():
        return 0
    imported = 0
    with history.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("status") != "added" or not row.get("url"):
                continue
            _, created = db.upsert_offer(
                row["url"], company=row.get("company"), title=row.get("title"),
                location=(row.get("location") or "").replace(" | ", "; "), site=row.get("company"),
                source=row.get("portal") or "careerops", posted_at=row.get("posted_at") or None,
            )
            imported += created
    return imported


def fetch_jd(url: str) -> str | None:
    """Texte de l'offre via l'API publique de l'ATS (Greenhouse, Lever, Ashby, Workday...)."""
    try:
        proc = subprocess.run(["node", "fetch-jd.mjs", url], cwd=paths.CAREER_OPS, capture_output=True,
                              text=True, timeout=90, env=_node_env(paths.CAREER_OPS_DATA))
    except subprocess.TimeoutExpired:
        return None
    text = proc.stdout.strip()
    return text if proc.returncode == 0 and len(text) > 300 else None


def writing_rules() -> str:
    """Les règles anti-« texte d'IA » de CareerOps, injectées dans la rédaction."""
    f = paths.CAREER_OPS / "modes" / "_writing.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def chromium_path() -> str | None:
    """Le Chromium installé par Playwright (partagé par `joby login` et l'agent)."""
    proc = subprocess.run(["node", "-e", "console.log(require('playwright').chromium.executablePath())"],
                          cwd=paths.CAREER_OPS, capture_output=True, text=True)
    p = proc.stdout.strip()
    return p if p and Path(p).exists() else None
