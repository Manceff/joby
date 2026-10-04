"""Identité visuelle du dashboard : « bureau de candidature ».

Bleu nuit profond, laiton (comme le gaufrage d'un papier à en-tête), ivoire.
Newsreader (serif à chiffres alignés) pour les titres et les chiffres,
Hanken Grotesk pour l'interface. Les PDF, en papier blanc, sont la vraie matière.
"""

from __future__ import annotations

import html

import altair as alt
import streamlit as st

# --- Jetons -----------------------------------------------------------------------
BG = "#121A2B"
SURFACE = "#18223A"
SURFACE_2 = "#1F2B47"
LINE = "#2B3858"
INK = "#ECE6D8"
INK_2 = "#A7B0C2"
MUTED = "#7D879C"
BRASS = "#C8A15A"
# Rampe séquentielle validée (dataviz) sur la surface #18223A : une teinte, du plus discret au plus vif.
RAMP = ["#6E5530", "#93733F", "#B78F50", "#D6B06B", "#EED7A6"]

# Statuts : couleurs réservées, toujours accompagnées d'un pictogramme et d'un libellé.
STATUS_TONE = {
    "good": "#7CC4A0",     # entretien, offre
    "pending": "#9DB4E0",  # en cours
    "warn": "#E58A5B",     # action requise
    "bad": "#D26A6A",      # refus, échec
    "quiet": MUTED,        # écartée, expirée
}
TONE_OF = {
    "new": "quiet", "shortlisted": "pending", "ready": "pending", "approved": "pending",
    "needs_you": "warn", "applied": "pending", "acknowledged": "pending", "interview": "good",
    "offer": "good", "rejected": "bad", "discarded": "quiet", "declined": "quiet",
    "expired": "quiet", "failed": "bad",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Hanken+Grotesk:wght@400;500;600&display=swap');

:root {{
  --bg: {BG}; --surface: {SURFACE}; --surface-2: {SURFACE_2}; --line: {LINE};
  --ink: {INK}; --ink-2: {INK_2}; --muted: {MUTED}; --brass: {BRASS};
  --serif: 'Newsreader', Georgia, serif; --sans: 'Hanken Grotesk', system-ui, sans-serif;
}}
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background: var(--bg); color: var(--ink); }}
.stApp {{ font-family: var(--sans); }}
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp td, .stApp th,
[data-testid="stSidebarNav"] a span:not([data-testid="stIconMaterial"]) {{ font-family: var(--sans); }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 5rem; max-width: 1180px; }}

/* Titres */
.stApp h1, .stApp h2, .stApp h3, .j-serif {{ font-family: var(--serif); font-weight: 500; letter-spacing: -0.01em; color: var(--ink); }}
.stApp h2 {{ font-size: 1.55rem; margin: 2.6rem 0 0.2rem; }}
.stApp h3 {{ font-size: 1.25rem; }}
.j-lede {{ color: var(--ink-2); font-size: 1.02rem; max-width: 62ch; margin: 0.15rem 0 1.4rem; line-height: 1.55; }}
.j-page-title {{ font-family: var(--serif); font-size: 2.6rem; line-height: 1.1; font-weight: 500; margin: 0; }}

/* Barre latérale */
[data-testid="stSidebar"] {{ background: #141D31; border-right: 1px solid var(--line); }}
[data-testid="stSidebarContent"] {{ display: flex !important; flex-direction: column !important; }}
[data-testid="stSidebarHeader"] {{ order: -2; }}
[data-testid="stSidebarUserContent"] {{ order: -1 !important; padding-top: 0.2rem !important; padding-bottom: 0.4rem !important; }}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
[data-testid="stSidebarNav"] {{ border-top: 1px solid var(--line); padding-top: 0.6rem; }}
[data-testid="stSidebarNavSeparator"] {{ display: none; }}
[data-testid="stSidebarNav"] a {{ border-radius: 8px; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: var(--surface-2); }}
.j-brand {{ font-family: var(--serif); font-size: 2rem; font-weight: 500; color: var(--ink); margin: 0 0 0.1rem; }}
.j-brand-dot {{ color: var(--brass); }}
.j-agent {{ font-size: 0.85rem; color: var(--ink-2); line-height: 1.5; margin-bottom: 1.2rem; }}
.j-pulse {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }}

/* Accroche de la vue d'ensemble */
.j-hero {{ font-family: var(--serif); font-size: clamp(1.8rem, 3.2vw, 2.55rem); line-height: 1.2; font-weight: 400;
          max-width: 30ch; margin: 0.2rem 0 2.2rem; color: var(--ink); }}
.j-hero b {{ font-weight: 500; color: var(--brass); font-variant-numeric: lining-nums tabular-nums; }}
.j-hello {{ color: var(--ink-2); font-size: 1rem; margin-bottom: 0.3rem; }}

/* Entonnoir : une seule animation, au chargement */
.j-funnel {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0; border-top: 1px solid var(--line);
            border-bottom: 1px solid var(--line); }}
.j-stage {{ padding: 1.1rem 1.1rem 1.2rem 0; position: relative; }}
.j-stage + .j-stage {{ padding-left: 1.1rem; border-left: 1px solid var(--line); }}
.j-stage-n {{ font-family: var(--serif); font-size: 2.5rem; line-height: 1; font-variant-numeric: lining-nums tabular-nums; }}
.j-stage-l {{ color: var(--ink-2); font-size: 0.92rem; margin-top: 0.35rem; }}
.j-stage-bar {{ height: 6px; border-radius: 3px; background: var(--brass); margin-top: 0.9rem; transform-origin: left;
               animation: j-grow 900ms cubic-bezier(.2,.7,.2,1) both; }}
.j-stage-rate {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.45rem; font-variant-numeric: tabular-nums; }}
@keyframes j-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .j-stage-bar {{ animation: none; }} }}
@media (max-width: 760px) {{
  .j-funnel {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .j-stage, .j-stage + .j-stage {{ padding: 0.9rem 0.8rem; border-left: none; border-top: 1px solid var(--line); }}
}}

/* Taux : une ligne de faits, pas des cartes */
.j-facts {{ display: flex; flex-wrap: wrap; gap: 0.6rem 2.4rem; margin: 1.4rem 0 0.4rem; }}
.j-fact-v {{ font-family: var(--serif); font-size: 1.6rem; font-variant-numeric: lining-nums tabular-nums; }}
.j-fact-l {{ color: var(--ink-2); font-size: 0.86rem; max-width: 22ch; }}

/* Bandeau « à faire » */
.j-todo {{ display: flex; gap: 1rem; align-items: baseline; padding: 0.95rem 1.2rem; border-radius: 10px;
          background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--tone); margin: 0.4rem 0; }}
.j-todo-n {{ font-family: var(--serif); font-size: 1.7rem; color: var(--ink); }}
.j-todo-t {{ color: var(--ink); }}
.j-todo-s {{ color: var(--ink-2); font-size: 0.9rem; }}

/* Étiquettes et statuts */
.j-tag {{ display: inline-block; padding: 0.12rem 0.6rem; border-radius: 999px; font-size: 0.8rem; color: var(--ink-2);
         border: 1px solid var(--line); margin-right: 0.35rem; }}
.j-tag-sector {{ color: var(--brass); border-color: rgba(200,161,90,0.45); }}
.j-status {{ display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: var(--ink); }}
.j-status i {{ width: 8px; height: 8px; border-radius: 50%; background: var(--tone); display: inline-block; }}

/* Offre */
.j-offer-title {{ font-family: var(--serif); font-size: 1.65rem; line-height: 1.2; margin: 0 0 0.45rem; color: var(--ink); }}
.j-offer-meta {{ color: var(--ink-2); font-size: 0.95rem; margin-bottom: 0.7rem; }}
.j-offer-meta a {{ color: var(--brass); text-decoration: none; border-bottom: 1px solid rgba(200,161,90,0.4); }}
.j-score {{ display: inline-flex; gap: 3px; vertical-align: -1px; margin-right: 0.45rem; }}
.j-score span {{ width: 18px; height: 6px; border-radius: 3px; background: var(--line); }}
.j-score span.on {{ background: var(--brass); }}
.j-why {{ font-size: 1.02rem; line-height: 1.55; max-width: 72ch; color: var(--ink); margin: 0.6rem 0 0.9rem; }}
.j-list-h {{ font-family: var(--serif); font-size: 1.05rem; margin-bottom: 0.2rem; }}
.j-paper img {{ border-radius: 4px; box-shadow: 0 18px 40px -18px rgba(0,0,0,0.65); }}
.j-doc-h {{ color: var(--ink-2); font-size: 0.9rem; margin: 0.8rem 0 0.4rem; }}

/* Tableau croisé */
.j-pivot {{ width: 100%; border-collapse: separate; border-spacing: 0 3px; font-variant-numeric: tabular-nums; }}
.j-pivot th {{ text-align: right; font-weight: 500; color: var(--ink-2); font-size: 0.85rem; padding: 0.4rem 0.7rem; }}
.j-pivot th:first-child, .j-pivot td:first-child {{ text-align: left; }}
.j-pivot td {{ padding: 0.55rem 0.7rem; text-align: right; font-size: 0.95rem; color: var(--ink); }}
.j-pivot td.cell {{ border-radius: 4px; }}
.j-pivot td.name {{ font-family: var(--serif); font-size: 1.05rem; }}
.j-pivot tr:hover td {{ background-color: rgba(255,255,255,0.025); }}

/* Activité */
.j-feed {{ border-left: 1px solid var(--line); padding-left: 1rem; }}
.j-feed-i {{ margin-bottom: 0.85rem; }}
.j-feed-t {{ color: var(--muted); font-size: 0.8rem; }}
.j-feed-m {{ color: var(--ink); font-size: 0.93rem; line-height: 1.4; }}

/* Composants natifs */
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] button {{
  border-radius: 8px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font-weight: 500; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: var(--brass); color: var(--ink); }}
.stButton > button[kind="primary"] {{ background: var(--brass); border-color: var(--brass); color: #1A1406; }}
.stButton > button[kind="primary"]:hover {{ background: #D6B06B; color: #1A1406; }}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{ outline: 2px solid var(--brass); outline-offset: 2px; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--line) !important; border-radius: 12px; background: var(--surface); }}
[data-testid="stExpander"] details {{ border-color: var(--line); border-radius: 10px; }}
hr {{ border-color: var(--line); }}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    alt.theme.register("joby", enable=True)(_altair_theme)


def _altair_theme():
    return {"config": {
        "background": "transparent",
        "font": "Hanken Grotesk",
        "view": {"stroke": None},
        "axis": {"labelColor": INK_2, "titleColor": INK_2, "domainColor": LINE, "tickColor": LINE,
                 "gridColor": "#24304D", "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500},
        "legend": {"labelColor": INK_2, "titleColor": INK_2, "labelFontSize": 12},
        "title": {"color": INK, "font": "Newsreader", "fontWeight": 500},
    }}


# --- Composants HTML ----------------------------------------------------------------------

def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def page_title(title: str, lede: str = "") -> None:
    st.markdown(f'<h1 class="j-page-title">{esc(title)}</h1>' + (f'<p class="j-lede">{esc(lede)}</p>' if lede else ""),
                unsafe_allow_html=True)


def status_chip(status: str, label: str) -> str:
    tone = STATUS_TONE[TONE_OF.get(status, "quiet")]
    return f'<span class="j-status" style="--tone:{tone}"><i></i>{esc(label)}</span>'


def score_pips(score) -> str:
    if score is None:
        return ""
    on = round(float(score))
    pips = "".join(f'<span class="{"on" if i < on else ""}"></span>' for i in range(5))
    return f'<span class="j-score" aria-label="Note {score:g} sur 5">{pips}</span><b>{f"{score:g}".replace(".", ",")}</b>/5'


def ramp_color(value: float, vmax: float) -> tuple[str, str]:
    """Couleur de fond (rampe laiton) et couleur de texte lisible pour une cellule."""
    if not vmax or value <= 0:
        return "transparent", INK_2
    idx = min(len(RAMP) - 1, int((value / vmax) * (len(RAMP) - 1) + 0.5))
    return RAMP[idx], ("#1A1406" if idx >= 3 else INK)
