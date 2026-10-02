"""Données fictives pour découvrir le dashboard sans rien configurer (`joby demo`).

Elles vivent dans `demo-data/`, jamais dans ton vrai dossier `user/`.
"""

from __future__ import annotations

import json
import random
import shutil
from datetime import datetime, timedelta, timezone

from . import db, latex, paths

COMPANIES = [
    ("Qonto", "Product Manager — Payments", "Paris", 4.6),
    ("Doctolib", "Senior Product Manager, Patient Experience", "Paris", 4.4),
    ("Alan", "Product Manager — Health Services", "Paris / Remote", 4.8),
    ("Back Market", "Product Manager, Logistics", "Paris", 4.1),
    ("Mirakl", "Product Manager — Marketplace Platform", "Paris", 4.2),
    ("Pennylane", "Product Manager, Accounting", "Paris", 4.5),
    ("Swile", "Product Owner — Benefits", "Montpellier", 3.2),
    ("Contentsquare", "Product Manager, AI Insights", "Paris", 4.7),
    ("Ledger", "Product Manager — Wallet", "Paris", 3.6),
    ("BlaBlaCar", "Product Manager, Trust & Safety", "Paris", 4.3),
    ("Lydia", "Growth Product Manager", "Paris", 2.4),
    ("Spendesk", "Product Manager — Integrations", "Paris / Remote", 4.0),
]

FLOW = ["offer", "interview", "interview", "rejected", "acknowledged", "applied",
        "applied", "needs_you", "approved", "ready", "ready", "discarded"]


def seed() -> None:
    random.seed(7)
    if paths.USER.exists():
        shutil.rmtree(paths.USER)
    paths.ensure_user_dirs()
    latex.install_default_templates()
    sample = paths.APPLICATIONS_DIR / "demo"
    sample.mkdir(parents=True, exist_ok=True)
    cv_pdf = letter_pdf = None
    if latex.engine():
        for name in ("cv", "letter"):
            shutil.copy(paths.TEMPLATES / f"{name}.tex", sample / f"{name}.tex")
        cv_pdf, letter_pdf = latex.compile(sample / "cv.tex"), latex.compile(sample / "letter.tex")
        shutil.copy(cv_pdf, paths.PREVIEW_DIR / "cv.pdf")
        shutil.copy(letter_pdf, paths.PREVIEW_DIR / "letter.pdf")

    now = datetime.now(timezone.utc)
    for i, ((company, title, city, score), status) in enumerate(zip(COMPANIES, FLOW)):
        found = now - timedelta(days=14 - i, hours=random.randint(0, 20))
        oid, _ = db.upsert_offer(f"https://example.com/jobs/{company.lower().replace(' ', '-')}-{i}",
                                 company=company, title=title, location=city, site=company, source="démo",
                                 posted_at=(found - timedelta(days=2)).date().isoformat())
        a = {"summary": f"Poste produit dans une scale-up {company}, missions très proches de ce que tu cherches.",
             "strengths": ["Expérience produit B2C directement transférable", "Environnement scale-up recherché"],
             "gaps": ["Pas d'expérience dans ce secteur précis"], "angle": "Ton projet de refonte du parcours de paiement."}
        fields = dict(status=status, score=score, fit_summary=a["summary"], analysis=a, language="fr",
                      prescreen="keep", cv_pdf=str(cv_pdf) if cv_pdf else None,
                      letter_pdf=str(letter_pdf) if letter_pdf else None, dossier_dir=str(sample),
                      dossier_notes="J'ai mis en avant ton projet de refonte du paiement, qui répond au cœur de l'offre.")
        if status in ("applied", "acknowledged", "interview", "rejected", "offer"):
            fields["applied_at"] = (found + timedelta(days=1)).replace(microsecond=0).isoformat()
        if status == "needs_you":
            fields["pending_questions"] = [f"Why do you want to join {company}? (300 characters max)"]
            fields["apply_report"] = {"details": "Question obligatoire sans réponse dans tes données."}
        if status == "discarded":
            fields["fit_summary"] = "Poste growth très orienté acquisition payante : c'est dans tes « à éviter »."
        db.set_offer(oid, **fields)
        db.log("démo", f"{db.label(status)} : {company} — {title}", oid)
    with db.connect() as c:
        c.execute("INSERT INTO runs(started_at, finished_at, ok, summary) VALUES (?,?,1,?)",
                  ((now - timedelta(minutes=40)).isoformat(), (now - timedelta(minutes=31)).isoformat(),
                   json.dumps({"repérage": 3, "analyse": 2})))


if __name__ == "__main__":
    seed()
