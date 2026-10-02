"""Envoi des candidatures que tu as validées dans le dashboard.

Claude pilote le navigateur persistant de Joby (tes sessions sont déjà ouvertes),
remplit le formulaire avec tes données validées, joint ton CV et ta lettre, et
clique sur « Envoyer ». S'il tombe sur une question à laquelle tu n'as jamais
répondu, un captcha ou une connexion expirée, il s'arrête AVANT l'envoi et te
demande la main dans le dashboard.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import claude, config, db, mcp, paths
from . import identity_block, models, read

APPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["submitted", "needs_input", "login_required", "closed", "failed"]},
        "details": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "string"}},
        "confirmation": {"type": "string"},
    },
    "required": ["outcome", "details"],
}

MAX_ATTEMPTS = 3


def _uploads(offer) -> tuple[Path, Path]:
    """Le navigateur ne peut joindre que des fichiers du dossier de travail : on y copie les PDF,
    avec des noms propres (c'est ce que le recruteur verra)."""
    ident = config.read_yaml(paths.IDENTITY, {}) or {}
    name = f"{ident.get('first_name', '')} {ident.get('last_name', '')}".strip() or "Candidate"
    folder = paths.WORK / "uploads" / str(offer["id"])
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    cv = folder / f"CV - {name}.pdf"
    letter = folder / f"Cover letter - {name}.pdf"
    shutil.copy(offer["cv_pdf"], cv)
    shutil.copy(offer["letter_pdf"], letter)
    return cv, letter


def _prompt(offer) -> str:
    folder = Path(offer["dossier_dir"])
    extra = read(folder / "answers-extra.md")
    cv, letter = _uploads(offer)
    return "\n\n".join([
        f"<job url=\"{offer['url']}\" company=\"{offer['company']}\" title=\"{offer['title']}\" />",
        identity_block(),
        f"<form_answers>\n{read(paths.ANSWERS)}\n{extra}\n</form_answers>",
        f"<documents>\nCV PDF (absolute path): {cv}\n"
        f"Cover letter PDF (absolute path): {letter}\n</documents>",
        f"<cover_letter_text>\n{read(folder / 'letter.txt')}\n</cover_letter_text>",
    ])


def submit(offer) -> str:
    db.set_offer(offer["id"], attempts=offer["attempts"] + 1)
    res = claude.run(_prompt(offer), system=claude.prompt_file("pipeline/apply.md"), model=models()["apply"],
                     schema=APPLY_SCHEMA, tools=mcp.BROWSER_TOOLS, mcp=mcp.browser(), timeout=1800)
    r = res.data
    outcome = r["outcome"]
    label = f"{offer['company']} — {offer['title']}"
    if outcome == "submitted":
        db.set_offer(offer["id"], status="applied", applied_at=db.now(), apply_report=r, pending_questions=None)
        db.log("envoi", f"Candidature envoyée : {label}", offer["id"])
    elif outcome == "closed":
        db.set_offer(offer["id"], status="expired", apply_report=r)
        db.log("envoi", f"Offre fermée entre-temps : {label}", offer["id"])
    elif outcome in ("needs_input", "login_required"):
        questions = r.get("questions") or []
        if outcome == "login_required":
            questions = ["Ta session sur ce site a expiré : reconnecte-toi avec `joby login`, puis relance l'envoi."]
        db.set_offer(offer["id"], status="needs_you", apply_report=r, pending_questions=questions)
        db.log("envoi", f"J'ai besoin de toi pour finir : {label}", offer["id"])
    else:
        status = "needs_you" if offer["attempts"] + 1 >= MAX_ATTEMPTS else "approved"
        db.set_offer(offer["id"], status=status, apply_report=r,
                     pending_questions=[f"L'envoi a échoué : {r['details']}"] if status == "needs_you" else None)
        db.log("envoi", f"Échec de l'envoi ({r['details'][:120]}) : {label}", offer["id"])
    return outcome


def run() -> int:
    sent = 0
    for o in db.offers("approved", order="approved_at ASC"):
        try:
            sent += submit(o) == "submitted"
        except claude.QuotaReached:
            raise
        except claude.ClaudeError as e:
            db.log("envoi", f"{o['company']} : envoi interrompu ({e})", o["id"])
    return sent
