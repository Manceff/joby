"""Calcul des métriques du dashboard (entonnoir, taux, ventilation par spécialité)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from joby import db

RETAINED = ("shortlisted", "ready", "approved", "needs_you", "applied", "acknowledged",
            "interview", "offer", "rejected", "declined")
SENT = ("applied", "acknowledged", "interview", "offer", "rejected")
HUMAN_REPLY = ("interview", "offer", "rejected")


def offers_frame() -> pd.DataFrame:
    with db.connect() as c:
        df = pd.read_sql_query("SELECT * FROM offers", c)
    df["sector"] = df["sector"].fillna("Non classée")
    df["retained"] = df["status"].isin(RETAINED)
    df["sent"] = df["status"].isin(SENT) | df["applied_at"].notna()
    df["replied"] = df["status"].isin(HUMAN_REPLY) | (df["had_interview"] == 1)
    df["interviewed"] = (df["had_interview"] == 1) | df["status"].isin(("interview", "offer"))
    df["got_offer"] = df["status"] == "offer"
    return df


def mails_frame() -> pd.DataFrame:
    with db.connect() as c:
        return pd.read_sql_query(
            "SELECT m.*, o.applied_at FROM mails m LEFT JOIN offers o ON o.id = m.offer_id", c)


@dataclass
class Funnel:
    seen: int
    retained: int
    sent: int
    interviews: int
    offers: int
    replied: int


def funnel(df: pd.DataFrame) -> Funnel:
    return Funnel(len(df), int(df["retained"].sum()), int(df["sent"].sum()), int(df["interviewed"].sum()),
                  int(df["got_offer"].sum()), int(df["replied"].sum()))


def ratio(a: int, b: int) -> float | None:
    return a / b if b else None


def median_reply_days() -> float | None:
    m = mails_frame()
    m = m[m["category"].isin(HUMAN_REPLY) & m["applied_at"].notna() & m["received_at"].notna()]
    if m.empty:
        return None
    delay = pd.to_datetime(m["received_at"], utc=True, format="ISO8601") - pd.to_datetime(m["applied_at"], utc=True, format="ISO8601")
    return float(delay.dt.total_seconds().median() / 86400)


def by_sector(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("sector")
    out = pd.DataFrame({
        "Repérées": g.size(),
        "Retenues": g["retained"].sum(),
        "Envoyées": g["sent"].sum(),
        "Réponses": g["replied"].sum(),
        "Entretiens": g["interviewed"].sum(),
    }).astype(int)
    out["Sélection"] = out["Retenues"] / out["Repérées"]
    out["Note moyenne"] = df[df["retained"]].groupby("sector")["score"].mean()
    return out.sort_values(["Repérées", "Retenues"], ascending=False)


def weekly(df: pd.DataFrame) -> pd.DataFrame:
    seen = pd.to_datetime(df["found_at"], utc=True, format="ISO8601").dt.tz_localize(None).dt.to_period("W").dt.start_time
    sent = pd.to_datetime(df["applied_at"].dropna(), utc=True, format="ISO8601").dt.tz_localize(None).dt.to_period("W").dt.start_time
    w = pd.DataFrame({"Offres lues": seen.value_counts(), "Candidatures envoyées": sent.value_counts()}).fillna(0).astype(int)
    return w.sort_index()
