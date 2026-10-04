"""La boucle de l'agent.

- Toutes les `cycle_hours` heures : scan → présélection → analyse → dossiers → suivi mail.
- Chaque minute : envoie les candidatures que tu viens de valider (pas besoin d'attendre le cycle).
- Si l'abonnement Claude atteint sa limite, l'agent se met en pause et reprend tout seul.
"""

from __future__ import annotations

import fcntl
import json
import logging
import signal
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .. import claude, config, db, paths, ui
from . import apply, dossier, mail, scan, sectors, triage

log = logging.getLogger("joby")

QUOTA_PAUSE = timedelta(minutes=45)


def _setup_logging() -> None:
    paths.LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=paths.LOG, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")


@contextmanager
def lock():
    paths.LOCK.parent.mkdir(parents=True, exist_ok=True)
    f = open(paths.LOCK, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise RuntimeError("L'agent tourne déjà (un autre processus Joby est actif).")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def _stage(name: str, fn, summary: dict) -> None:
    ui.info(f"{name}…")
    try:
        summary[name] = fn()
    except claude.QuotaReached:
        raise
    except Exception as e:  # une étape en échec ne bloque pas les suivantes
        log.exception("Étape %s en échec", name)
        db.log("agent", f"Étape « {name} » en échec : {e}")
        summary[name] = f"erreur : {e}"


def run_cycle() -> dict:
    started = db.now()
    with db.connect() as c:
        run_id = c.execute("INSERT INTO runs(started_at) VALUES (?)", (started,)).lastrowid
    summary: dict = {}
    ok = True
    try:
        _stage("repérage", scan.run, summary)
        _stage("classement", sectors.run, summary)
        _stage("présélection", lambda: triage.prescreen()[0], summary)
        _stage("analyse", lambda: triage.analyse()[1], summary)
        _stage("dossiers", dossier.run, summary)
        _stage("envoi", apply.run, summary)
        _stage("mails", mail.run, summary)
    except claude.QuotaReached as e:
        ok = False
        summary["pause"] = "limite d'usage Claude atteinte"
        db.log("agent", f"Limite d'usage Claude atteinte, pause automatique ({e})")
        raise
    finally:
        with db.connect() as c:
            c.execute("UPDATE runs SET finished_at=?, ok=?, summary=? WHERE id=?",
                      (db.now(), int(ok), json.dumps(summary, ensure_ascii=False), run_id))
    db.log("agent", "Cycle terminé : " + ", ".join(f"{k} {v}" for k, v in summary.items()))
    return summary


def _last_cycle() -> datetime | None:
    with db.connect() as c:
        row = c.execute("SELECT started_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    return datetime.fromisoformat(row["started_at"]) if row else None


def agent_loop(once: bool = False) -> None:
    _setup_logging()
    cfg = config.load()
    if not cfg["pipeline"]["enabled"]:
        ui.warn("L'onboarding n'est pas terminé : lance d'abord `joby setup`.")
        return
    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))

    with lock():
        ui.success("Agent démarré. Ctrl+C pour l'arrêter." if not once else "Cycle unique.")
        db.log("agent", "Agent démarré")
        paused_until: datetime | None = None
        while not stop["now"]:
            now = datetime.now(timezone.utc)
            try:
                if paused_until and now < paused_until:
                    pass
                else:
                    paused_until = None
                    last = _last_cycle()
                    every = timedelta(hours=config.load()["pipeline"]["cycle_hours"])
                    if once or paths.RUN_NOW.exists() or not last or now - last >= every:
                        paths.RUN_NOW.unlink(missing_ok=True)
                        ui.section(f"Cycle du {now.astimezone():%d/%m à %H:%M}")
                        summary = run_cycle()
                        ui.success("Cycle terminé : " + ", ".join(f"{k} {v}" for k, v in summary.items()))
                    elif db.offers("approved"):
                        apply.run()
            except claude.QuotaReached:
                paused_until = now + QUOTA_PAUSE
                paths.RUN_NOW.touch()  # le cycle interrompu reprendra juste après la pause
                ui.warn(f"Limite d'usage Claude atteinte : pause jusqu'à {paused_until.astimezone():%H:%M}.")
            except KeyboardInterrupt:
                break
            if once:
                break
            try:
                time.sleep(60)
            except KeyboardInterrupt:
                break
        db.log("agent", "Agent arrêté")
        ui.info("Agent arrêté.")
