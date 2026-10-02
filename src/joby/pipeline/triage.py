"""Tri en deux temps : présélection rapide sur l'intitulé, puis analyse complète de l'offre."""

from __future__ import annotations

import json
import re
import urllib.request

from .. import careerops, claude, config, db
from . import models, profile_context

PRESCREEN_BATCH = 60

PRESCREEN_SCHEMA = {
    "type": "object",
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object",
        "properties": {"n": {"type": "integer"}, "decision": {"type": "string", "enum": ["keep", "drop"]},
                       "reason": {"type": "string"}},
        "required": ["n", "decision", "reason"]}}},
    "required": ["decisions"],
}

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_open": {"type": "boolean"},
        "score": {"type": "number", "minimum": 1, "maximum": 5},
        "language": {"type": "string"},
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "dealbreaker": {"type": ["string", "null"]},
        "angle": {"type": "string"},
        "company_address": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
    },
    "required": ["is_open", "score", "language", "summary", "strengths", "gaps", "angle"],
}


def prescreen() -> tuple[int, int]:
    pending = [o for o in db.offers("new") if o["prescreen"] is None]
    kept = dropped = 0
    for i in range(0, len(pending), PRESCREEN_BATCH):
        batch = pending[i:i + PRESCREEN_BATCH]
        listing = "\n".join(f"{n}. {o['title']} — {o['company']} — {o['location'] or 'n/a'}"
                            for n, o in enumerate(batch, 1))
        res = claude.run(f"{profile_context(cv=False)}\n\n<postings>\n{listing}\n</postings>",
                         system=claude.prompt_file("pipeline/prescreen.md"), model=models()["prescreen"],
                         schema=PRESCREEN_SCHEMA, timeout=600)
        decided = {d["n"]: d for d in res.data["decisions"]}
        for n, o in enumerate(batch, 1):
            d = decided.get(n, {"decision": "keep", "reason": "non évaluée, gardée par prudence"})
            if d["decision"] == "drop":
                db.set_offer(o["id"], prescreen="drop", prescreen_note=d["reason"], status="discarded")
                dropped += 1
            else:
                db.set_offer(o["id"], prescreen="keep", prescreen_note=d["reason"])
                kept += 1
    if pending:
        db.log("tri", f"Présélection : {kept} gardée(s), {dropped} écartée(s) sur l'intitulé")
    return kept, dropped


def _fetch_page_text(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Joby job-search agent)"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
    except Exception:
        return None
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    return text[:20000] if len(text) > 800 else None


def job_text(offer) -> str | None:
    if offer["jd_text"]:
        return offer["jd_text"]
    text = careerops.fetch_jd(offer["url"]) or _fetch_page_text(offer["url"])
    if text:
        db.set_offer(offer["id"], jd_text=text)
    return text


def analyse() -> tuple[int, int]:
    cfg = config.load()["pipeline"]
    todo = [o for o in db.offers("new", order="posted_at DESC, found_at ASC") if o["prescreen"] == "keep"]
    todo = todo[: cfg["max_analyses_per_cycle"]]
    retained = 0
    for o in todo:
        text = job_text(o)
        tools: list[str] = []
        if not text:
            # Page rendue en JavaScript : Claude va la lire lui-même.
            text = f"(The posting text could not be extracted automatically. Read it with WebFetch: {o['url']})"
            tools = ["WebFetch"]
        prompt = (f"{profile_context()}\n\n<job_posting url=\"{o['url']}\" company=\"{o['company']}\" "
                  f"title=\"{o['title']}\">\n{text}\n</job_posting>")
        try:
            res = claude.run(prompt, system=claude.prompt_file("pipeline/analysis.md"), model=models()["analysis"],
                             schema=ANALYSIS_SCHEMA, tools=tools, timeout=600)
        except claude.QuotaReached:
            raise
        except claude.ClaudeError as e:
            db.log("analyse", f"{o['company']} — {o['title']} : analyse impossible ({e})", o["id"])
            continue
        a = res.data
        if not a.get("is_open", True):
            db.set_offer(o["id"], status="expired", analysis=a, fit_summary=a.get("summary"))
            continue
        score = float(a["score"])
        good = score >= cfg["min_score"] and not a.get("dealbreaker")
        db.set_offer(o["id"], score=score, analysis=a, fit_summary=a["summary"], language=a.get("language"),
                     location=a.get("location") or o["location"], status="shortlisted" if good else "discarded")
        if good:
            retained += 1
            db.log("analyse", f"Retenue ({score:g}/5) : {o['company']} — {o['title']}", o["id"])
    return len(todo), retained


def analysis_of(offer) -> dict:
    try:
        return json.loads(offer["analysis"] or "{}")
    except json.JSONDecodeError:
        return {}
