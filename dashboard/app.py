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

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from joby import config, db, paths  # noqa: E402

st.set_page_config(page_title="Joby", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .block-container {padding-top: 3.2rem; max-width: 1200px;}
  .joby-title {font-size: 2.4rem; line-height: 1.2; font-weight: 800; letter-spacing: -0.02em;
               background: linear-gradient(90deg, #7C9CFF, #D688D6); -webkit-background-clip: text;
               -webkit-text-fill-color: transparent; margin-bottom: 0;}
  .joby-sub {color: #8a8f98; margin-bottom: 1.4rem;}
  .chip {display: inline-block; padding: 0.1rem 0.6rem; border-radius: 999px; font-size: 0.8rem;
         background: rgba(124,156,255,0.14); color: #7C9CFF; margin-right: 0.3rem;}
  .score {font-weight: 700; font-size: 1.05rem;}
  div[data-testid="stMetricValue"] {font-size: 2rem;}
</style>
""", unsafe_allow_html=True)


# --- Accès protégé ----------------------------------------------------------------

def gate() -> None:
    secret = config.read_env().get("JOBY_DASHBOARD_PASSWORD")
    if not secret or st.session_state.get("auth"):
        return
    st.markdown('<div class="joby-title">Joby</div>', unsafe_allow_html=True)
    pwd = st.text_input("Mot de passe du dashboard", type="password")
    if pwd and hmac.compare_digest(pwd, secret):
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Mot de passe incorrect.")
    st.stop()


gate()


# --- Helpers ----------------------------------------------------------------------------

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
    st.download_button(f"⬇️ Télécharger {label.lower()}", p.read_bytes(), file_name=p.name,
                       mime="application/pdf", key=f"dl-{key}-{path}")


def analysis(o) -> dict:
    try:
        return json.loads(o["analysis"] or "{}")
    except json.JSONDecodeError:
        return {}


def ago(ts: str | None) -> str:
    if not ts:
        return "—"
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
    s = int(delta.total_seconds())
    if s < 3600:
        return f"il y a {max(1, s // 60)} min"
    if s < 86400:
        return f"il y a {s // 3600} h"
    return f"il y a {s // 86400} j"


def stars(score) -> str:
    if score is None:
        return ""
    return f'<span class="score">{"★" * round(score)}{"☆" * (5 - round(score))} {score:g}/5</span>'


def header(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="joby-title">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="joby-sub">{sub}</div>', unsafe_allow_html=True)


def offer_header(o) -> None:
    st.markdown(f"### {o['title']}")
    chips = [o["company"], o["location"], o["site"] and o["site"] != o["company"] and o["site"]]
    st.markdown(" ".join(f'<span class="chip">{c}</span>' for c in chips if c)
                + f" &nbsp; [Voir l'offre ↗]({o['url']})", unsafe_allow_html=True)


counts = db.counts()


# --- Pages -------------------------------------------------------------------------------

def page_overview() -> None:
    header("Joby", "Ton agent cherche pour toi, jour et nuit. Voici où tu en es.")

    applied_like = ("applied", "acknowledged", "interview", "offer", "rejected")
    c = st.columns(6)
    c[0].metric("Offres repérées", sum(counts.values()))
    c[1].metric("Retenues", sum(counts.get(s, 0) for s in ("shortlisted", "ready", "approved", "needs_you", *applied_like)))
    c[2].metric("À valider", counts.get("ready", 0))
    c[3].metric("Envoyées", sum(counts.get(s, 0) for s in applied_like))
    c[4].metric("Entretiens", counts.get("interview", 0))
    c[5].metric("Offres", counts.get("offer", 0))

    if counts.get("ready"):
        st.info(f"👀 **{counts['ready']} dossier(s)** t'attendent dans « À valider ».")
    if counts.get("needs_you"):
        st.warning(f"✋ **{counts['needs_you']} candidature(s)** ont besoin de toi dans « Action requise ».")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Où en sont les candidatures")
        order = ["shortlisted", "ready", "approved", "needs_you", "applied", "acknowledged", "interview", "offer", "rejected"]
        short = {"shortlisted": "En rédaction", "approved": "Envoi en cours", "acknowledged": "Accusé reçu"}
        names = [f"{db.STATUSES[s][1]} {short.get(s, db.STATUSES[s][0])}" for s in order]
        data = pd.DataFrame({"Statut": names, "Nombre": [counts.get(s, 0) for s in order]})
        st.bar_chart(data, x="Statut", y="Nombre", horizontal=True, sort=False, color="#7C9CFF", height=330)

        with db.connect() as conn:
            weekly = pd.read_sql_query(
                "SELECT substr(applied_at,1,10) AS jour, COUNT(*) AS n FROM offers WHERE applied_at IS NOT NULL "
                "GROUP BY jour ORDER BY jour", conn)
        if not weekly.empty:
            st.subheader("Candidatures envoyées")
            weekly["jour"] = pd.to_datetime(weekly["jour"])
            st.area_chart(weekly.set_index("jour")["n"].cumsum(), color="#D688D6", height=220)

    with right:
        st.subheader("L'agent")
        with db.connect() as conn:
            run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
            events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 12").fetchall()
        cfg = config.load()
        if run:
            state = "✅ dernier cycle réussi" if run["ok"] else ("⏳ cycle en cours" if not run["finished_at"] else "⚠️ dernier cycle incomplet")
            st.markdown(f"**{state}** · {ago(run['started_at'])}  \nUn cycle toutes les {cfg['pipeline']['cycle_hours']} h.")
        else:
            st.markdown("L'agent n'a pas encore tourné. Lance `joby agent`.")
        if st.button("🔄 Lancer un cycle maintenant", width="stretch"):
            paths.RUN_NOW.touch()
            st.toast("C'est noté : l'agent démarre un cycle dans la minute.")
        st.subheader("Activité récente")
        for e in events:
            st.markdown(f"<small style='color:#8a8f98'>{ago(e['ts'])}</small><br>{e['message']}", unsafe_allow_html=True)


def page_review() -> None:
    header("À valider", "Relis chaque dossier. Un clic sur « Valider » et l'agent envoie la candidature pour toi.")
    items = db.offers("ready", order="score DESC")
    if not items:
        st.success("Rien à valider pour l'instant. L'agent te prévient dès qu'un dossier est prêt. ☕")
        return
    for o in items:
        a = analysis(o)
        with st.container(border=True):
            offer_header(o)
            st.markdown(stars(o["score"]), unsafe_allow_html=True)
            st.markdown(f"**Pourquoi cette offre :** {o['fit_summary'] or ''}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Points forts**")
                for s in a.get("strengths", []):
                    st.markdown(f"- {s}")
            with c2:
                st.markdown("**Points de vigilance**")
                for g in a.get("gaps", []) or ["—"]:
                    st.markdown(f"- {g}")
            if o["dossier_notes"]:
                with st.expander("📝 Notes de rédaction"):
                    st.markdown(o["dossier_notes"])

            tab_cv, tab_letter = st.columns(2, gap="medium")
            tab_cv.markdown("**📄 CV**")
            tab_letter.markdown("**✉️ Lettre de motivation**")
            with tab_cv:
                show_pdf(o["cv_pdf"], "CV", key=f"rv{o['id']}")
            with tab_letter:
                show_pdf(o["letter_pdf"], "Lettre", key=f"rv{o['id']}")

            b1, b2, b3 = st.columns([2, 2, 1])
            if b1.button("✅ Valider et envoyer", key=f"ok-{o['id']}", type="primary", width="stretch"):
                db.set_offer(o["id"], status="approved", approved_at=db.now(), attempts=0)
                db.log("validation", f"Validée par toi : {o['company']} — {o['title']}", o["id"])
                st.toast("Validé ! L'agent s'occupe de l'envoi.")
                st.rerun()
            with b2.popover("✏️ Demander une retouche", width="stretch"):
                fb = st.text_area("Qu'est-ce qu'il faut changer ?", key=f"fb-{o['id']}",
                                  placeholder="Ex. : mets davantage en avant mon projet X, la lettre est trop longue…")
                if st.button("Envoyer la demande", key=f"fbok-{o['id']}") and fb.strip():
                    db.set_offer(o["id"], status="shortlisted", user_feedback=fb.strip())
                    db.log("validation", f"Retouche demandée : {o['company']} — {o['title']}", o["id"])
                    paths.RUN_NOW.touch()
                    st.rerun()
            if b3.button("🙅 Écarter", key=f"no-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="declined")
                db.log("validation", f"Écartée par toi : {o['company']} — {o['title']}", o["id"])
                st.rerun()


def page_needs_you() -> None:
    header("Action requise", "L'agent s'est arrêté avant l'envoi : il lui manque une info qu'il ne veut pas inventer.")
    items = db.offers("needs_you")
    if not items:
        st.success("Tout roule, l'agent n'a besoin de rien. 👌")
        return
    for o in items:
        with st.container(border=True):
            offer_header(o)
            report = json.loads(o["apply_report"] or "{}")
            if report.get("details"):
                st.caption(report["details"])
            questions = json.loads(o["pending_questions"] or "[]")
            answers = {}
            for i, q in enumerate(questions):
                answers[q] = st.text_area(q, key=f"q-{o['id']}-{i}")
            remember = st.checkbox("Mémoriser ces réponses pour les prochaines candidatures", value=True, key=f"rem-{o['id']}")
            c1, c2, c3 = st.columns(3)
            if c1.button("🚀 Relancer l'envoi", key=f"retry-{o['id']}", type="primary", width="stretch"):
                filled = {q: a.strip() for q, a in answers.items() if a.strip()}
                if filled and o["dossier_dir"]:
                    block = "".join(f"\n## {q}\n{a}\n" for q, a in filled.items())
                    with open(Path(o["dossier_dir"]) / "answers-extra.md", "a", encoding="utf-8") as f:
                        f.write(block)
                    if remember:
                        with open(paths.ANSWERS, "a", encoding="utf-8") as f:
                            f.write(block)
                db.set_offer(o["id"], status="approved", attempts=0, pending_questions=None)
                st.toast("C'est reparti.")
                st.rerun()
            if c2.button("📨 Je l'ai envoyée moi-même", key=f"manual-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="applied", applied_at=db.now(), pending_questions=None)
                db.log("envoi", f"Envoyée par toi : {o['company']} — {o['title']}", o["id"])
                st.rerun()
            if c3.button("🙅 Abandonner", key=f"drop-{o['id']}", width="stretch"):
                db.set_offer(o["id"], status="declined", pending_questions=None)
                st.rerun()


def page_applications() -> None:
    header("Candidatures", "Tout ce qui est parti, et ce que les recruteurs ont répondu.")
    sts = ("approved", "applied", "acknowledged", "interview", "offer", "rejected")
    items = db.offers(sts, order="COALESCE(applied_at, approved_at) DESC")
    if not items:
        st.info("Aucune candidature envoyée pour l'instant.")
        return
    df = pd.DataFrame([{
        "Entreprise": o["company"], "Poste": o["title"], "Statut": db.label(o["status"]),
        "Envoyée le": (o["applied_at"] or "")[:10], "Score": o["score"], "Offre": o["url"],
    } for o in items])
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={"Offre": st.column_config.LinkColumn("Offre", display_text="ouvrir ↗"),
                                "Score": st.column_config.NumberColumn(format="%.1f ★")})

    st.subheader("Détail")
    by_id = {o["id"]: o for o in items}
    choice = st.selectbox("Candidature", list(by_id), format_func=lambda i: f"{by_id[i]['company']} — {by_id[i]['title']}")
    if choice:
        o = by_id[choice]
        offer_header(o)
        with db.connect() as conn:
            mails = conn.execute("SELECT * FROM mails WHERE offer_id=? ORDER BY received_at DESC", (o["id"],)).fetchall()
            events = conn.execute("SELECT * FROM events WHERE offer_id=? ORDER BY id DESC", (o["id"],)).fetchall()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Historique**")
            for e in events:
                st.markdown(f"<small style='color:#8a8f98'>{e['ts'][:16].replace('T', ' ')}</small> — {e['message']}",
                            unsafe_allow_html=True)
            st.markdown("**Mails reçus**")
            for m in mails or []:
                st.markdown(f"- {db.label(m['category']) if m['category'] in db.STATUSES else '✉️'} "
                            f"**{m['subject']}** ({m['sender']}) — {m['summary']}")
            if not mails:
                st.caption("Aucun mail rattaché pour l'instant.")
            new = st.selectbox("Corriger le statut", sts, index=sts.index(o["status"]), format_func=db.label, key=f"st-{o['id']}")
            if new != o["status"] and st.button("Enregistrer", key=f"save-{o['id']}"):
                db.set_offer(o["id"], status=new)
                db.log("manuel", f"Statut changé en {db.label(new)} : {o['company']}", o["id"])
                st.rerun()
        with c2:
            t1, t2 = st.tabs(["📄 CV envoyé", "✉️ Lettre envoyée"])
            with t1:
                show_pdf(o["cv_pdf"], "CV", key=f"app{o['id']}")
            with t2:
                show_pdf(o["letter_pdf"], "Lettre", key=f"app{o['id']}")


def page_offers() -> None:
    header("Offres repérées", "Toutes les offres vues sur tes sites, et ce que l'agent en a pensé.")
    items = db.offers(order="found_at DESC")
    if not items:
        st.info("Aucune offre pour l'instant.")
        return
    statuses = sorted({o["status"] for o in items}, key=list(db.STATUSES).index)
    pick = st.multiselect("Filtrer par statut", statuses, format_func=db.label)
    q = st.text_input("Rechercher", placeholder="entreprise, poste…").lower()
    rows = [o for o in items if (not pick or o["status"] in pick)
            and (not q or q in f"{o['company']} {o['title']}".lower())]
    df = pd.DataFrame([{
        "Repérée": o["found_at"][:10], "Entreprise": o["company"], "Poste": o["title"], "Lieu": o["location"],
        "Statut": db.label(o["status"]), "Score": o["score"],
        "Avis de l'agent": o["fit_summary"] or o["prescreen_note"] or "", "Offre": o["url"],
    } for o in rows])
    st.dataframe(df, hide_index=True, width="stretch", height=520,
                 column_config={"Offre": st.column_config.LinkColumn("Offre", display_text="ouvrir ↗"),
                                "Score": st.column_config.NumberColumn(format="%.1f ★")})

    discarded = [o for o in rows if o["status"] in ("discarded", "declined")]
    if discarded:
        with st.expander("🎣 Repêcher une offre écartée"):
            by_id = {o["id"]: o for o in discarded}
            pick_id = st.selectbox("Offre", list(by_id), format_func=lambda i: f"{by_id[i]['company']} — {by_id[i]['title']}")
            o = by_id[pick_id]
            if st.button("Préparer un dossier pour celle-ci"):
                db.set_offer(o["id"], status="shortlisted", prescreen="keep")
                db.log("manuel", f"Repêchée par toi : {o['company']} — {o['title']}", o["id"])
                paths.RUN_NOW.touch()
                st.toast("L'agent va préparer le dossier.")
                st.rerun()


def page_templates() -> None:
    header("Mes modèles", "Les modèles de CV et de lettre validés pendant l'onboarding.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("CV")
        show_pdf(str(paths.PREVIEW_DIR / "cv.pdf"), "CV")
    with c2:
        st.subheader("Lettre")
        show_pdf(str(paths.PREVIEW_DIR / "letter.pdf"), "Lettre")
    st.caption("Pour les modifier : `joby setup --step cv_design` ou `joby setup --step letter_design`.")


def page_log() -> None:
    header("Journal", "Tout ce que l'agent a fait, dans l'ordre.")
    with db.connect() as conn:
        df = pd.read_sql_query("SELECT ts AS Date, kind AS Type, message AS Message FROM events ORDER BY id DESC LIMIT 500", conn)
    df["Date"] = df["Date"].str.slice(0, 16).str.replace("T", " ")
    st.dataframe(df, hide_index=True, width="stretch", height=600)


def badge(n: int) -> str:
    return f" ({n})" if n else ""


pages = [
    st.Page(page_overview, title="Vue d'ensemble", icon="🧭", default=True),
    st.Page(page_review, title="À valider" + badge(counts.get("ready", 0)), icon="👀", url_path="valider"),
    st.Page(page_needs_you, title="Action requise" + badge(counts.get("needs_you", 0)), icon="✋", url_path="action"),
    st.Page(page_applications, title="Candidatures", icon="📨", url_path="candidatures"),
    st.Page(page_offers, title="Offres repérées", icon="🔎", url_path="offres"),
    st.Page(page_templates, title="Mes modèles", icon="🎨", url_path="modeles"),
    st.Page(page_log, title="Journal", icon="🕒", url_path="journal"),
]
st.navigation(pages).run()
