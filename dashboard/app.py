"""Joby — tableau de bord (Streamlit).

Lit et écrit la même base que l'agent (`user/joby.db`). Les seules actions possibles
ici sont les tiennes : valider, demander une retouche, écarter, répondre aux
questions de l'agent. L'agent fait le reste.
"""

from __future__ import annotations

import hmac
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analytics as an  # noqa: E402
import theme as th  # noqa: E402
from joby import config, db, paths  # noqa: E402
from joby.pipeline import sectors  # noqa: E402

st.set_page_config(page_title="Joby", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
th.inject()


# --- Accès protégé --------------------------------------------------------------------

def gate() -> None:
    secret = config.read_env().get("JOBY_DASHBOARD_PASSWORD")
    if not secret or st.session_state.get("auth"):
        return
    st.markdown('<div class="j-brand">Joby<span class="j-brand-dot">.</span></div>', unsafe_allow_html=True)
    pwd = st.text_input("Mot de passe du dashboard", type="password")
    if pwd and hmac.compare_digest(pwd, secret):
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Mot de passe incorrect.")
    st.stop()


gate()


# --- Outils --------------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def pdf_pages(path: str, mtime: float) -> list:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        return [doc[i].render(scale=1.6).to_pil() for i in range(len(doc))]
    finally:
        doc.close()


def show_pdf(path: str | None, label: str, key: str = "") -> None:
    if not path or not Path(path).exists():
        st.caption(f"{label} : pas encore généré.")
        return
    p = Path(path)
    for img in pdf_pages(str(p), p.stat().st_mtime):
        st.image(img, width="stretch")
    st.download_button(f"Télécharger {label if label == 'CV' else label.lower()}", p.read_bytes(), file_name=p.name,
                       mime="application/pdf", key=f"dl-{key}-{path}")


def analysis(o) -> dict:
    try:
        return json.loads(o["analysis"] or "{}")
    except json.JSONDecodeError:
        return {}


def ago(ts: str | None) -> str:
    if not ts:
        return "—"
    s = int((datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds())
    if s < 3600:
        return f"il y a {max(1, s // 60)} min"
    if s < 86400:
        return f"il y a {s // 3600} h"
    return f"il y a {s // 86400} j"


def pct(x: float | None) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:.0f} %"


def num(x: float | None, digits: int = 1) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.{digits}f}".replace(".", ",")


def fr_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def offer_header(o) -> None:
    sector = o["sector"] if "sector" in o.keys() else None
    tag = f'<span class="j-tag j-tag-sector">{th.esc(sector)}</span>' if sector else ""
    meta = ", ".join(th.esc(x) for x in (o["company"], o["location"]) if x)
    st.markdown(
        f'<div class="j-offer-title">{th.esc(o["title"])}</div>'
        f'<div class="j-offer-meta">{tag}{meta} &nbsp; <a href="{th.esc(o["url"])}" target="_blank">Voir l\'offre</a></div>',
        unsafe_allow_html=True)


def lede(text: str) -> None:
    st.markdown(f'<p class="j-lede">{th.esc(text)}</p>', unsafe_allow_html=True)


counts = db.counts()


# --- Barre latérale : la marque et l'état de l'agent -----------------------------------------

def sidebar() -> None:
    with db.connect() as conn:
        run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    cfg = config.load()
    if not run:
        state, tone = "L'agent n'a pas encore tourné", th.MUTED
    elif not run["finished_at"]:
        state, tone = "Cycle en cours", th.STATUS_TONE["pending"]
    elif run["ok"]:
        state, tone = f"Dernier cycle {ago(run['started_at'])}", th.STATUS_TONE["good"]
    else:
        state, tone = f"Cycle incomplet {ago(run['started_at'])}", th.STATUS_TONE["warn"]
    with st.sidebar:
        st.markdown(
            f'<div class="j-brand">Joby<span class="j-brand-dot">.</span></div>'
            f'<div class="j-agent"><span class="j-pulse" style="background:{tone}"></span>{th.esc(state)}<br>'
            f'Un cycle toutes les {cfg["pipeline"]["cycle_hours"]} h</div>', unsafe_allow_html=True)
        if st.button("Lancer un cycle maintenant", width="stretch"):
            paths.RUN_NOW.touch()
            st.toast("L'agent démarre un cycle dans la minute.")


# --- Vue d'ensemble ------------------------------------------------------------------------------

def page_overview() -> None:
    df = an.offers_frame()
    ident = config.read_yaml(paths.IDENTITY, {}) or {}
    hello = f'<div class="j-hello">Bonjour{" " + th.esc(ident["first_name"]) if ident.get("first_name") else ""}.</div>'
    if df.empty:
        st.markdown(hello + '<div class="j-hero">Joby n\'a encore lu aucune offre. Lance l\'agent : '
                    'les premières arrivent dès le premier cycle.</div>', unsafe_allow_html=True)
        st.code("joby agent", language="bash")
        return

    f = an.funnel(df)
    st.markdown(hello + f'<div class="j-hero">Sur <b>{fr_int(f.seen)}</b> offres lues, Joby en a retenu '
                f'<b>{f.retained}</b> et tu as envoyé <b>{f.sent}</b> candidatures.</div>', unsafe_allow_html=True)

    # Entonnoir proportionnel, échelle racine carrée : les petites étapes restent lisibles.
    stages = [("Offres lues", f.seen), ("Retenues par Joby", f.retained), ("Candidatures envoyées", f.sent),
              ("Entretiens obtenus", f.interviews), ("Offres d'embauche", f.offers)]
    top = max(f.seen, 1) ** 0.5
    cells = []
    for i, (label, n) in enumerate(stages):
        width = max(2.0, 100 * n ** 0.5 / top) if n else 0
        rate = "" if i == 0 else f'<div class="j-stage-rate">{pct(an.ratio(n, stages[i - 1][1]))} de l\'étape précédente</div>'
        cells.append(f'<div class="j-stage"><div class="j-stage-n">{fr_int(n)}</div><div class="j-stage-l">{label}</div>'
                     f'<div class="j-stage-bar" style="width:{width:.1f}%;animation-delay:{i * 90}ms"></div>{rate}</div>')
    st.markdown(f'<div class="j-funnel">{"".join(cells)}</div>', unsafe_allow_html=True)

    median = an.median_reply_days()
    avg_score = df.loc[df["retained"], "score"].mean()
    facts = [
        (pct(an.ratio(f.retained, f.seen)), "des offres lues sont jugées à ta hauteur"),
        (pct(an.ratio(f.replied, f.sent)), "de réponses d'un recruteur, hors accusés automatiques"),
        (pct(an.ratio(f.interviews, f.sent)), "des candidatures mènent à un entretien"),
        ("—" if median is None else f"{median:.0f} jours", "délai médian avant une réponse"),
        (num(avg_score), "note moyenne des offres retenues, sur 5"),
    ]
    st.markdown('<div class="j-facts">' + "".join(
        f'<div><div class="j-fact-v">{v}</div><div class="j-fact-l">{l}</div></div>' for v, l in facts) + "</div>",
        unsafe_allow_html=True)

    todo = []
    if counts.get("ready"):
        n = counts["ready"]
        todo.append(("valider", n, "dossier à relire" if n == 1 else "dossiers à relire",
                     "CV et lettre prêts : un clic pour envoyer.", th.BRASS))
    if counts.get("needs_you"):
        n = counts["needs_you"]
        todo.append(("action", n, "candidature attend une réponse de ta part" if n == 1
                     else "candidatures attendent une réponse de ta part",
                     "L'agent s'est arrêté avant l'envoi.", th.STATUS_TONE["warn"]))
    if todo:
        st.markdown("## À faire")
        for page, n, title, sub, tone in todo:
            c1, c2 = st.columns([6, 1], vertical_alignment="center")
            c1.markdown(f'<div class="j-todo" style="--tone:{tone}"><span class="j-todo-n">{n}</span>'
                        f'<span><span class="j-todo-t">{title}</span><br><span class="j-todo-s">{sub}</span></span></div>',
                        unsafe_allow_html=True)
            c2.page_link(PAGES[page], label="Ouvrir")

    sector_section(df)
    rhythm_section(df)


def sector_section(df: pd.DataFrame) -> None:
    dim = sectors.dimension()
    st.markdown("## Où se trouvent les opportunités")
    if not sectors.taxonomy() and (df["sector"] == "Non classée").all():
        lede("La ventilation par spécialité apparaîtra après le prochain cycle : Joby conçoit d'abord "
             "une grille adaptée à ta recherche.")
        return
    lede(f"Les offres de tes sites, ventilées par {dim.lower()} selon une grille que Joby a construite "
         "à partir de ce que tu cherches.")

    table = an.by_sector(df)
    metric = st.segmented_control("Mesure affichée", ["Repérées", "Retenues", "Envoyées", "Entretiens"],
                                  default="Repérées", label_visibility="collapsed") or "Repérées"
    data = table.reset_index().rename(columns={"sector": dim})
    base = alt.Chart(data).encode(
        y=alt.Y(f"{dim}:N", sort="-x", title=None,
                axis=alt.Axis(labelFontSize=13, labelColor=th.INK, labelLimit=240, ticks=False, domain=False)),
        x=alt.X(f"{metric}:Q", title=None, axis=alt.Axis(tickMinStep=1, tickCount=5, format="d", grid=True, domain=False)),
        tooltip=[alt.Tooltip(f"{dim}:N"), alt.Tooltip("Repérées:Q"), alt.Tooltip("Retenues:Q"),
                 alt.Tooltip("Envoyées:Q"), alt.Tooltip("Entretiens:Q"),
                 alt.Tooltip("Sélection:Q", format=".0%", title="Taux de sélection")],
    )
    bars = base.mark_bar(color=th.BRASS, cornerRadiusEnd=4, height={"band": 0.6})
    labels = base.mark_text(align="left", dx=6, color=th.INK_2, fontSize=12).encode(text=alt.Text(f"{metric}:Q"))
    st.altair_chart((bars + labels).properties(height=max(220, 40 * len(data))), width="stretch")

    st.markdown(f"### Tableau croisé par {dim.lower()}")
    count_cols = ["Repérées", "Retenues", "Envoyées", "Réponses", "Entretiens"]
    head = "".join(f"<th>{c}</th>" for c in [dim, *count_cols, "Sélection", "Note moy."])
    rows = []
    for name, r in table.iterrows():
        tds = [f'<td class="name">{th.esc(name)}</td>']
        for c in count_cols:
            bg, fg = th.ramp_color(r[c], table[c].max())
            tds.append(f'<td class="cell" style="background:{bg};color:{fg}">{int(r[c])}</td>')
        tds.append(f"<td>{pct(r['Sélection'])}</td><td>{num(r['Note moyenne'])}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    st.markdown(f'<table class="j-pivot"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>',
                unsafe_allow_html=True)
    st.caption("Plus la case est claire, plus la valeur est élevée dans sa colonne. "
               "Pour changer de grille : `joby sectors --regenerate`.")


def rhythm_section(df: pd.DataFrame) -> None:
    w = an.weekly(df)
    if w.empty:
        return
    st.markdown("## Le rythme de ta recherche")
    w = w.rename_axis("Semaine").reset_index()
    c1, c2, c3 = st.columns([1, 1, 1.05], gap="large")
    for col, field, color in ((c1, "Offres lues", th.RAMP[2]), (c2, "Candidatures envoyées", th.BRASS)):
        with col:
            st.markdown(f"### {field}")
            w["Semaine du"] = pd.to_datetime(w["Semaine"]).dt.strftime("%d/%m")
            ch = (alt.Chart(w).mark_bar(color=color, cornerRadiusEnd=4, width={"band": 0.7})
                  .encode(x=alt.X("Semaine du:O", title=None, sort=None, axis=alt.Axis(labelAngle=0, ticks=False)),
                          y=alt.Y(f"{field}:Q", title=None, axis=alt.Axis(tickMinStep=1, tickCount=4, format="d", domain=False)),
                          tooltip=[alt.Tooltip("Semaine du:O"), alt.Tooltip(f"{field}:Q")])
                  .properties(height=220))
            st.altair_chart(ch, width="stretch")
    with c3:
        st.markdown("### Dernières actions")
        with db.connect() as conn:
            events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 7").fetchall()
        st.markdown('<div class="j-feed">' + "".join(
            f'<div class="j-feed-i"><div class="j-feed-t">{ago(e["ts"])}</div>'
            f'<div class="j-feed-m">{th.esc(e["message"])}</div></div>' for e in events) + "</div>",
            unsafe_allow_html=True)
        st.page_link(PAGES["journal"], label="Tout le journal")


# --- À valider ------------------------------------------------------------------------------------

def page_review() -> None:
    th.page_title("À valider", "Relis chaque dossier. « Valider et envoyer », et l'agent postule pour toi.")
    items = db.offers("ready", order="score DESC")
    if not items:
        lede("Aucun dossier en attente. L'agent t'en préparera un dès qu'une offre mérite ta candidature.")
        return
    for o in items:
        a = analysis(o)
        with st.container(border=True):
            offer_header(o)
            st.markdown(f'<div>{th.score_pips(o["score"])}</div><p class="j-why">{th.esc(o["fit_summary"] or "")}</p>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="large")
            c1.markdown('<div class="j-list-h">Ce qui joue pour toi</div>' + "".join(
                f"<div>• {th.esc(s)}</div>" for s in a.get("strengths", [])), unsafe_allow_html=True)
            c2.markdown('<div class="j-list-h">Points de vigilance</div>' + "".join(
                f"<div>• {th.esc(g)}</div>" for g in a.get("gaps", []) or ["Aucun"]), unsafe_allow_html=True)
            if o["dossier_notes"]:
                with st.expander("Notes de rédaction de l'agent"):
                    st.markdown(o["dossier_notes"])
            d1, d2 = st.columns(2, gap="medium")
            with d1:
                st.markdown('<div class="j-doc-h">CV</div>', unsafe_allow_html=True)
                show_pdf(o["cv_pdf"], "CV", key=f"rv{o['id']}")
            with d2:
                st.markdown('<div class="j-doc-h">Lettre de motivation</div>', unsafe_allow_html=True)
                show_pdf(o["letter_pdf"], "Lettre", key=f"rv{o['id']}")

            b1, b2, b3 = st.columns([2, 2, 1])
            if b1.button("Valider et envoyer", key=f"ok-{o['id']}", type="primary", width="stretch"):
                db.set_offer(o["id"], status="approved", approved_at=db.now(), attempts=0)
                db.log("validation", f"Validée par toi : {o['company']} — {o['title']}", o["id"])
                st.toast("Validée. L'agent envoie la candidature.")
                st.rerun()
            with b2.popover("Demander une retouche", width="stretch"):
                fb = st.text_area("Qu'est-ce qu'il faut changer ?", key=f"fb-{o['id']}",
                                  placeholder="Ex. : mets davantage en avant mon stage en LBO, la lettre est trop longue…")
                if st.button("Envoyer la demande", key=f"fbok-{o['id']}") and fb.strip():
                    db.set_offer(o["id"], status="shortlisted", user_feedback=fb.strip())
                    db.log("validation", f"Retouche demandée : {o['company']} — {o['title']}", o["id"])
                    paths.RUN_NOW.touch()
                    st.rerun()
            if b3.button("Écarter", key=f"no-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="declined")
                db.log("validation", f"Écartée par toi : {o['company']} — {o['title']}", o["id"])
                st.rerun()


# --- Action requise ------------------------------------------------------------------------------

def page_needs_you() -> None:
    th.page_title("Action requise", "L'agent s'est arrêté avant l'envoi : il lui manque une information qu'il ne veut pas inventer.")
    items = db.offers("needs_you")
    if not items:
        lede("Rien ne t'attend ici : l'agent a tout ce qu'il lui faut.")
        return
    for o in items:
        with st.container(border=True):
            offer_header(o)
            report = json.loads(o["apply_report"] or "{}")
            if report.get("details"):
                st.caption(report["details"])
            questions = json.loads(o["pending_questions"] or "[]")
            answers = {q: st.text_area(q, key=f"q-{o['id']}-{i}") for i, q in enumerate(questions)}
            remember = st.checkbox("Mémoriser ces réponses pour les prochaines candidatures", value=True, key=f"rem-{o['id']}")
            c1, c2, c3 = st.columns(3)
            if c1.button("Relancer l'envoi", key=f"retry-{o['id']}", type="primary", width="stretch"):
                filled = {q: a.strip() for q, a in answers.items() if a.strip()}
                if filled and o["dossier_dir"]:
                    block = "".join(f"\n## {q}\n{a}\n" for q, a in filled.items())
                    with open(Path(o["dossier_dir"]) / "answers-extra.md", "a", encoding="utf-8") as fh:
                        fh.write(block)
                    if remember:
                        with open(paths.ANSWERS, "a", encoding="utf-8") as fh:
                            fh.write(block)
                db.set_offer(o["id"], status="approved", attempts=0, pending_questions=None)
                st.toast("Envoi relancé.")
                st.rerun()
            if c2.button("Je l'ai envoyée moi-même", key=f"manual-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="applied", applied_at=db.now(), pending_questions=None)
                db.log("envoi", f"Envoyée par toi : {o['company']} — {o['title']}", o["id"])
                st.rerun()
            if c3.button("Abandonner", key=f"drop-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="declined", pending_questions=None)
                st.rerun()


# --- Candidatures ---------------------------------------------------------------------------------

def page_applications() -> None:
    th.page_title("Candidatures", "Tout ce qui est parti, et ce que les recruteurs ont répondu.")
    sts = ("approved", "applied", "acknowledged", "interview", "offer", "rejected")
    items = db.offers(sts, order="COALESCE(applied_at, approved_at) DESC")
    if not items:
        lede("Aucune candidature envoyée pour l'instant. Elles apparaîtront ici dès ta première validation.")
        return
    dim = sectors.dimension()
    df = pd.DataFrame([{
        "Entreprise": o["company"], "Poste": o["title"], dim: o["sector"],
        "Statut": db.STATUSES.get(o["status"], (o["status"],))[0],
        "Envoyée le": pd.to_datetime(o["applied_at"]).date() if o["applied_at"] else None,
        "Note": o["score"], "Offre": o["url"],
    } for o in items])
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={"Offre": st.column_config.LinkColumn("Offre", display_text="ouvrir"),
                                "Note": st.column_config.ProgressColumn("Note", min_value=0, max_value=5, format="%.1f"),
                                "Envoyée le": st.column_config.DateColumn(format="DD/MM/YYYY")})

    st.markdown("## Détail d'une candidature")
    by_id = {o["id"]: o for o in items}
    choice = st.selectbox("Candidature", list(by_id), format_func=lambda i: f"{by_id[i]['company']} — {by_id[i]['title']}",
                          label_visibility="collapsed")
    if not choice:
        return
    o = by_id[choice]
    offer_header(o)
    st.markdown(th.status_chip(o["status"], db.STATUSES[o["status"]][0]), unsafe_allow_html=True)
    with db.connect() as conn:
        mails = conn.execute("SELECT * FROM mails WHERE offer_id=? ORDER BY received_at DESC", (o["id"],)).fetchall()
        events = conn.execute("SELECT * FROM events WHERE offer_id=? ORDER BY id DESC", (o["id"],)).fetchall()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("### Mails reçus")
        if mails:
            for m in mails:
                st.markdown(f'<div class="j-feed-i"><div class="j-feed-t">{th.esc((m["received_at"] or "")[:10])}, '
                            f'{th.esc(m["sender"])}</div><div class="j-feed-m"><b>{th.esc(m["subject"])}</b><br>'
                            f'{th.esc(m["summary"])}</div></div>', unsafe_allow_html=True)
        else:
            st.caption("Aucun mail rattaché pour l'instant.")
        st.markdown("### Historique")
        st.markdown('<div class="j-feed">' + "".join(
            f'<div class="j-feed-i"><div class="j-feed-t">{e["ts"][:16].replace("T", " ")}</div>'
            f'<div class="j-feed-m">{th.esc(e["message"])}</div></div>' for e in events) + "</div>", unsafe_allow_html=True)
        new = st.selectbox("Corriger le statut", sts, index=sts.index(o["status"]),
                           format_func=lambda s: db.STATUSES[s][0], key=f"st-{o['id']}")
        if new != o["status"] and st.button("Enregistrer le statut", key=f"save-{o['id']}"):
            db.set_offer(o["id"], status=new)
            db.log("manuel", f"Statut changé en « {db.STATUSES[new][0]} » : {o['company']}", o["id"])
            st.rerun()
    with c2:
        t1, t2 = st.tabs(["CV envoyé", "Lettre envoyée"])
        with t1:
            show_pdf(o["cv_pdf"], "CV", key=f"app{o['id']}")
        with t2:
            show_pdf(o["letter_pdf"], "Lettre", key=f"app{o['id']}")


# --- Offres repérées --------------------------------------------------------------------------------

def page_offers() -> None:
    th.page_title("Offres repérées", "Tout ce que l'agent a lu sur tes sites, et ce qu'il en a pensé.")
    items = db.offers(order="found_at DESC")
    if not items:
        lede("Aucune offre pour l'instant.")
        return
    dim = sectors.dimension()
    c1, c2, c3 = st.columns([2, 2, 3])
    statuses = sorted({o["status"] for o in items}, key=list(db.STATUSES).index)
    pick = c1.multiselect("Statut", statuses, format_func=lambda s: db.STATUSES[s][0])
    pick_sec = c2.multiselect(dim, sorted({o["sector"] for o in items if o["sector"]}))
    q = c3.text_input("Rechercher", placeholder="entreprise, poste…").lower()
    rows = [o for o in items if (not pick or o["status"] in pick) and (not pick_sec or o["sector"] in pick_sec)
            and (not q or q in f"{o['company']} {o['title']}".lower())]
    st.caption(f"{len(rows)} offre(s)")
    df = pd.DataFrame([{
        "Repérée": pd.to_datetime(o["found_at"]).date(), "Entreprise": o["company"], "Poste": o["title"],
        dim: o["sector"], "Statut": db.STATUSES.get(o["status"], (o["status"],))[0], "Note": o["score"],
        "Avis de l'agent": o["fit_summary"] or o["prescreen_note"] or "", "Offre": o["url"],
    } for o in rows])
    st.dataframe(df, hide_index=True, width="stretch", height=560,
                 column_config={"Offre": st.column_config.LinkColumn("Offre", display_text="ouvrir"),
                                "Note": st.column_config.ProgressColumn("Note", min_value=0, max_value=5, format="%.1f"),
                                "Repérée": st.column_config.DateColumn(format="DD/MM/YYYY")})

    discarded = [o for o in rows if o["status"] in ("discarded", "declined")]
    if discarded:
        with st.expander("Repêcher une offre écartée"):
            by_id = {o["id"]: o for o in discarded}
            pick_id = st.selectbox("Offre", list(by_id), format_func=lambda i: f"{by_id[i]['company']} — {by_id[i]['title']}")
            if st.button("Préparer un dossier pour cette offre"):
                o = by_id[pick_id]
                db.set_offer(o["id"], status="shortlisted", prescreen="keep")
                db.log("manuel", f"Repêchée par toi : {o['company']} — {o['title']}", o["id"])
                paths.RUN_NOW.touch()
                st.toast("L'agent va préparer le dossier.")
                st.rerun()


# --- Modèles et journal ---------------------------------------------------------------------------------

def page_templates() -> None:
    th.page_title("Mes modèles", "Les modèles de CV et de lettre validés pendant ta configuration.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="j-doc-h">CV</div>', unsafe_allow_html=True)
        show_pdf(str(paths.PREVIEW_DIR / "cv.pdf"), "CV", key="tpl")
    with c2:
        st.markdown('<div class="j-doc-h">Lettre de motivation</div>', unsafe_allow_html=True)
        show_pdf(str(paths.PREVIEW_DIR / "letter.pdf"), "Lettre", key="tpl")
    st.caption("Pour les modifier : `joby setup --step cv_design` ou `joby setup --step letter_design`.")


def page_log() -> None:
    th.page_title("Journal", "Tout ce que l'agent a fait, du plus récent au plus ancien.")
    with db.connect() as conn:
        df = pd.read_sql_query("SELECT ts AS Date, kind AS Étape, message AS Message FROM events ORDER BY id DESC LIMIT 500", conn)
    df["Date"] = pd.to_datetime(df["Date"], format="ISO8601")
    st.dataframe(df, hide_index=True, width="stretch", height=620,
                 column_config={"Date": st.column_config.DatetimeColumn(format="DD/MM HH:mm")})


def badge(n: int) -> str:
    return f" ({n})" if n else ""


PAGES = {
    "overview": st.Page(page_overview, title="Vue d'ensemble", icon=":material/space_dashboard:", default=True),
    "valider": st.Page(page_review, title="À valider" + badge(counts.get("ready", 0)), icon=":material/fact_check:",
                       url_path="valider"),
    "action": st.Page(page_needs_you, title="Action requise" + badge(counts.get("needs_you", 0)),
                      icon=":material/pan_tool:", url_path="action"),
    "candidatures": st.Page(page_applications, title="Candidatures", icon=":material/send:", url_path="candidatures"),
    "offres": st.Page(page_offers, title="Offres repérées", icon=":material/travel_explore:", url_path="offres"),
    "modeles": st.Page(page_templates, title="Mes modèles", icon=":material/description:", url_path="modeles"),
    "journal": st.Page(page_log, title="Journal", icon=":material/history:", url_path="journal"),
}
sidebar()
st.navigation(list(PAGES.values())).run()
