"""Rédaction du dossier : CV et lettre en LaTeX, relecture stricte, compilation.

Garde-fous :
- le préambule (la mise en forme validée) doit être identique au modèle, au caractère près ;
- un relecteur indépendant traque les faits inventés avant que tu ne voies le dossier ;
- chaque PDF doit compiler et tenir sur une page (sauf si tes règles disent autrement).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .. import careerops, claude, config, db, latex, paths
from . import identity_block, models, profile_context, read
from .triage import analysis_of, job_text

LANG_NAMES = {"fr": "French", "en": "English", "de": "German", "es": "Spanish", "it": "Italian",
              "nl": "Dutch", "pt": "Portuguese"}

WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "cv_tex": {"type": "string"},
        "letter_tex": {"type": "string"},
        "letter_language": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["cv_tex", "letter_tex", "letter_language", "notes"],
}

PROOF_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}}},
    "required": ["ok", "issues"],
}

MAX_ROUNDS = 3


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "offre"


def _letter_language(offer) -> str:
    setting = config.load()["letter"]["language"]
    code = (offer["language"] or "en") if setting == "auto" else setting
    return LANG_NAMES.get(code[:2].lower(), code)


def _inputs(offer, feedback: str | None, previous_issues: list[str] | None) -> str:
    a = analysis_of(offer)
    blocks = [
        identity_block(),
        profile_context(),
        f"<cv_rules>\n{read(paths.CV_PREFS)}\n</cv_rules>",
        f"<letter_rules>\n{read(paths.LETTER_PREFS)}\n</letter_rules>",
        f"<writing_rules source=\"career-ops\">\n{careerops.writing_rules()}\n</writing_rules>",
        f"<cv_template>\n{read(paths.CV_TEMPLATE)}\n</cv_template>",
        f"<letter_template>\n{read(paths.LETTER_TEMPLATE)}\n</letter_template>",
        f"<job_posting url=\"{offer['url']}\" company=\"{offer['company']}\" title=\"{offer['title']}\" "
        f"location=\"{offer['location'] or ''}\">\n{job_text(offer) or ''}\n</job_posting>",
        f"<analyst_notes>\nScore: {offer['score']}/5\nSummary: {a.get('summary', '')}\n"
        f"Strengths: {a.get('strengths', [])}\nGaps: {a.get('gaps', [])}\nAngle: {a.get('angle', '')}\n"
        f"Company address: {a.get('company_address') or 'unknown'}\n</analyst_notes>",
        f"<parameters>\nToday: {date.today().isoformat()}\nCV language: English\n"
        f"Letter language: {_letter_language(offer)}\n"
        f"Signature image available: {'yes' if paths.SIGNATURE.exists() else 'no'}\n</parameters>",
    ]
    if paths.EXAMPLES_DIR.exists():
        voice = [p for p in paths.EXAMPLES_DIR.iterdir() if p.suffix.lower() in (".md", ".txt", ".tex")]
        for p in voice[:3]:
            blocks.append(f"<voice_reference file=\"{p.name}\">\n{read(p)[:6000]}\n</voice_reference>")
    if feedback:
        blocks.append(f"<candidate_feedback>\nThe candidate reviewed the previous version and asks:\n{feedback}\n"
                      "</candidate_feedback>")
    if previous_issues:
        blocks.append("<fix_these_issues>\n" + "\n".join(f"- {i}" for i in previous_issues) + "\n</fix_these_issues>")
    return "\n\n".join(blocks)


def _write_and_compile(folder: Path, name: str, tex: str, template: Path) -> tuple[Path | None, list[str]]:
    issues = []
    if not latex.same_preamble(tex, read(template)):
        issues.append(f"The {name} preamble differs from the template. Copy the template preamble exactly.")
        return None, issues
    path = folder / f"{name}.tex"
    path.write_text(tex, encoding="utf-8")
    try:
        pdf = latex.compile(path)
    except latex.LatexError as e:
        issues.append(f"The {name} does not compile with XeLaTeX. Log tail:\n{e.log[-1500:]}")
        return None, issues
    if latex.page_count(pdf) > 1 and "two pages" not in read(paths.CV_PREFS).lower():
        issues.append(f"The {name} is longer than one page. Make it fit on exactly one page.")
    return pdf, issues


def build(offer) -> bool:
    folder = paths.APPLICATIONS_DIR / f"{offer['id']:04d}-{_slug(offer['company'])}-{_slug(offer['title'])}"
    folder.mkdir(parents=True, exist_ok=True)
    issues: list[str] = []
    feedback = offer["user_feedback"]
    proofread = config.load()["pipeline"]["proofread"]
    notes = ""
    for _ in range(MAX_ROUNDS):
        res = claude.run(_inputs(offer, feedback, issues), system=claude.prompt_file("pipeline/writing.md"),
                         model=models()["writing"], schema=WRITE_SCHEMA, timeout=1200, effort="high")
        out = res.data
        notes = out["notes"]
        cv_pdf, cv_issues = _write_and_compile(folder, "cv", out["cv_tex"], paths.CV_TEMPLATE)
        letter_pdf, letter_issues = _write_and_compile(folder, "letter", out["letter_tex"], paths.LETTER_TEMPLATE)
        issues = cv_issues + letter_issues
        if not issues and proofread:
            review = claude.run(
                f"{identity_block()}\n\n{profile_context(brief=False)}\n\n<cv_rules>\n{read(paths.CV_PREFS)}\n</cv_rules>\n\n"
                f"<letter_rules>\n{read(paths.LETTER_PREFS)}\n</letter_rules>\n\n"
                f"<job company=\"{offer['company']}\" title=\"{offer['title']}\" />\n\n"
                f"<cv_tex>\n{out['cv_tex']}\n</cv_tex>\n\n<letter_tex>\n{out['letter_tex']}\n</letter_tex>",
                system=claude.prompt_file("pipeline/proofread.md"), model=models()["writing"],
                schema=PROOF_SCHEMA, timeout=600)
            if not review.data["ok"]:
                issues = review.data["issues"]
        if not issues:
            (folder / "notes.md").write_text(notes, encoding="utf-8")
            (folder / "letter.txt").write_text(_plain_letter(out["letter_tex"]), encoding="utf-8")
            db.set_offer(offer["id"], status="ready", dossier_dir=str(folder), cv_pdf=str(cv_pdf),
                         letter_pdf=str(letter_pdf), dossier_notes=notes, user_feedback=None)
            db.log("dossier", f"Dossier prêt, à valider : {offer['company']} — {offer['title']}", offer["id"])
            return True
    db.set_offer(offer["id"], status="failed", dossier_notes="Problèmes non résolus :\n- " + "\n- ".join(issues))
    db.log("dossier", f"Dossier impossible à finaliser : {offer['company']} — {offer['title']}", offer["id"])
    return False


def _plain_letter(tex: str) -> str:
    """Version texte de la lettre, pour les formulaires qui ont un champ « lettre »."""
    body = tex.split("\\begin{document}", 1)[-1].split("\\end{document}", 1)[0]
    m = re.search(r"\\subject\{.*?\}\s*(.*?)\\signoff", body, re.S)
    body = m.group(1) if m else body
    body = re.sub(r"\\(textbf|textit|emph|href\{[^}]*\})\{([^}]*)\}", r"\2", body)
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", "", body)
    body = body.replace("\\&", "&").replace("\\%", "%").replace("\\$", "$").replace("\\_", "_").replace("~", " ")
    body = re.sub(r"[{}]", "", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def run() -> int:
    limit = config.load()["pipeline"]["max_dossiers_per_cycle"]
    built = 0
    for o in db.offers("shortlisted", order="score DESC, found_at ASC", limit=limit):
        try:
            built += build(o)
        except claude.QuotaReached:
            raise
        except claude.ClaudeError as e:
            db.log("dossier", f"{o['company']} : rédaction interrompue ({e})", o["id"])
    return built
