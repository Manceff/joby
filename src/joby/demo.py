"""Données fictives pour découvrir le dashboard sans rien configurer (`joby demo`).

Scénario : une candidate en private equity, six semaines de recherche. Les sociétés
sont inventées. Tout vit dans `demo-data/`, jamais dans ton vrai dossier `user/`.
"""

from __future__ import annotations

import random
import shutil
from datetime import datetime, timedelta, timezone

import yaml

from . import db, latex, paths

TAXONOMY = {
    "dimension": "Spécialité",
    "categories": [
        {"name": "Buyout (LBO)", "description": "Fonds de rachat majoritaire, small à large cap"},
        {"name": "Growth equity", "description": "Minoritaire ou majoritaire dans des sociétés en forte croissance"},
        {"name": "Venture capital", "description": "Amorçage à série C"},
        {"name": "Private debt", "description": "Dette unitranche, mezzanine, direct lending"},
        {"name": "Infrastructure", "description": "Énergie, transport, télécoms, transition"},
        {"name": "Secondaries", "description": "Secondaire, fonds de fonds, co-investissement"},
        {"name": "M&A advisory", "description": "Banques d'affaires et boutiques de conseil"},
    ],
}

FIRMS = {
    "Buyout (LBO)": ["Harcourt Capital", "Vallon Partners", "Meridien Equity", "Saint-Clair Investissement"],
    "Growth equity": ["Altair Growth", "Corniche Capital", "Lumen Partners"],
    "Venture capital": ["Brisant Ventures", "Orée VC", "Kestrel Seed"],
    "Private debt": ["Tramontane Credit", "Arche Dette Privée"],
    "Infrastructure": ["Brume Infrastructure", "Pylône Capital"],
    "Secondaries": ["Second Souffle Partners", "Atlas Fund Solutions"],
    "M&A advisory": ["Maison Delorme", "Rivoli Conseil", "Quai Boutique M&A"],
}

TITLES = {
    "Buyout (LBO)": ["Investment Associate — Mid-cap LBO", "Analyste Private Equity Buyout", "Senior Associate Buyout"],
    "Growth equity": ["Growth Equity Associate", "Investment Manager Growth", "Analyste Growth Tech"],
    "Venture capital": ["VC Analyst — Seed & Series A", "Associate Venture Capital", "Investment Analyst Deeptech"],
    "Private debt": ["Analyste Dette Privée", "Private Debt Associate — Unitranche", "Direct Lending Analyst"],
    "Infrastructure": ["Infrastructure Investment Associate", "Analyste Infrastructure Énergie"],
    "Secondaries": ["Secondaries Associate", "Analyste Fonds de fonds", "Co-investment Analyst"],
    "M&A advisory": ["Analyste M&A", "M&A Associate — Healthcare", "Analyste Corporate Finance"],
}

# Poids : où se trouvent les offres (repérées) et la probabilité qu'elles collent au profil.
WEIGHT = {"Buyout (LBO)": 30, "Growth equity": 22, "Venture capital": 18, "Private debt": 14,
          "Infrastructure": 9, "Secondaries": 7, "M&A advisory": 26}
FIT = {"Buyout (LBO)": 0.35, "Growth equity": 0.4, "Venture capital": 0.12, "Private debt": 0.2,
       "Infrastructure": 0.1, "Secondaries": 0.15, "M&A advisory": 0.05}
CITIES = ["Paris", "Paris", "Paris", "Londres", "Lyon", "Luxembourg"]


def seed() -> None:
    rng = random.Random(11)
    if paths.USER.exists():
        shutil.rmtree(paths.USER)
    paths.ensure_user_dirs()
    paths.IDENTITY.write_text("first_name: Camille\nlast_name: Martin\n", encoding="utf-8")
    paths.TAXONOMY.write_text(yaml.safe_dump(TAXONOMY, allow_unicode=True, sort_keys=False), encoding="utf-8")
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
    sectors = list(WEIGHT)
    counter = 0
    for sector in sectors:
        for _ in range(WEIGHT[sector]):
            counter += 1
            firm = rng.choice(FIRMS[sector])
            title = rng.choice(TITLES[sector])
            found = now - timedelta(days=rng.uniform(0, 42))
            oid, _ = db.upsert_offer(f"https://example.com/jobs/{counter}", company=firm, title=title,
                                     location=rng.choice(CITIES), site=firm, source="démo",
                                     posted_at=(found - timedelta(days=rng.randint(0, 5))).date().isoformat())
            with db.connect() as c:
                c.execute("UPDATE offers SET found_at=? WHERE id=?", (found.replace(microsecond=0).isoformat(), oid))

            fits = rng.random() < FIT[sector]
            score = round(rng.uniform(4.0, 4.9), 1) if fits else round(rng.uniform(1.5, 3.8), 1)
            a = {"summary": f"{title} chez {firm} : {'très proche' if fits else 'éloigné'} de ce que tu cherches.",
                 "strengths": ["Deux stages en LBO mid-cap directement valorisables", "Modélisation financière solide"],
                 "gaps": ["Pas d'expérience en origination"], "angle": "Ton stage chez un fonds small-cap."}
            fields = dict(sector=sector, score=score, analysis=a, fit_summary=a["summary"], language="fr",
                          prescreen="keep" if fits or rng.random() < 0.5 else "drop")
            if not fits:
                fields["status"] = "discarded"
            else:
                age = (now - found).days
                applied = found + timedelta(days=rng.uniform(0.5, 2))
                fields.update(cv_pdf=str(cv_pdf) if cv_pdf else None, letter_pdf=str(letter_pdf) if letter_pdf else None,
                              dossier_dir=str(sample),
                              dossier_notes="J'ai mis en avant ton stage en LBO et ta note d'investissement sur le secteur santé.")
                if age < 2:
                    fields["status"] = rng.choice(["ready", "ready", "shortlisted"])
                elif age < 4:
                    fields["status"] = rng.choice(["needs_you", "approved", "applied"])
                else:
                    fields["status"] = "applied"
                    fields["applied_at"] = applied.replace(microsecond=0).isoformat()
                if fields["status"] == "needs_you":
                    fields["pending_questions"] = [f"Why {firm}? (500 characters max)"]
                    fields["apply_report"] = {"details": "Question obligatoire sans réponse dans tes données."}
            db.set_offer(oid, **fields)

            if fields.get("status") == "applied" and fields.get("applied_at"):
                r = rng.random()
                outcome = ("interview" if r < 0.22 else "rejected" if r < 0.5 else "acknowledged" if r < 0.8 else None)
                if outcome:
                    delay = timedelta(days=rng.uniform(1, 12))
                    received = applied + delay
                    if received < now:
                        db.set_offer(oid, status=outcome)
                        with db.connect() as c:
                            c.execute("INSERT INTO mails(message_id, offer_id, received_at, sender, subject, category, summary) "
                                      "VALUES (?,?,?,?,?,?,?)",
                                      (f"<demo-{oid}@example.com>", oid, received.isoformat(), f"recrutement@{firm.split()[0].lower()}.example",
                                       {"interview": "Invitation à un premier entretien", "rejected": "Votre candidature",
                                        "acknowledged": "Nous avons bien reçu votre candidature"}[outcome],
                                       outcome, {"interview": "Propose un entretien avec un associate la semaine prochaine.",
                                                 "rejected": "Refus poli, profil gardé en vivier.",
                                                 "acknowledged": "Accusé de réception automatique."}[outcome]))
                        db.log("mail", f"{db.label(outcome)} — {firm}", oid)
    # Une belle histoire pour finir : un entretien devenu offre, un autre devenu refus.
    interviews = db.offers("interview")
    if len(interviews) >= 2:
        db.set_offer(interviews[0]["id"], status="offer")
        db.log("mail", f"{db.label('offer')} — {interviews[0]['company']}", interviews[0]["id"])
        db.set_offer(interviews[1]["id"], status="rejected")
    with db.connect() as c:
        c.execute("INSERT INTO runs(started_at, finished_at, ok, summary) VALUES (?,?,1,?)",
                  ((now - timedelta(minutes=38)).isoformat(), (now - timedelta(minutes=29)).isoformat(),
                   '{"repérage": 7, "analyse": 3}'))
    for o in db.offers("ready"):
        db.log("dossier", f"Dossier prêt, à valider : {o['company']} — {o['title']}", o["id"])


if __name__ == "__main__":
    seed()
