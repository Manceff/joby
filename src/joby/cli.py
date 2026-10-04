"""La commande `joby`.

  joby                 accueil (et onboarding s'il n'est pas fini)
  joby setup           onboarding complet (reprend là où tu t'étais arrêté)
  joby setup --step X  refaire une étape (profile, cv, search, sites, logins, cv_design, letter_design, mail, recap)
  joby agent           lance l'agent en continu      (--once : un seul cycle)
  joby dashboard       ouvre le tableau de bord
  joby status          résumé dans le terminal
  joby login           rouvrir le navigateur pour te (re)connecter à tes sites
  joby sectors         ta grille de spécialités (--regenerate, --reclassify)
  joby doctor          vérifie l'installation
  joby demo            essayer le dashboard avec des données fictives
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

from rich.table import Table
from rich.text import Text

from . import careerops, config, db, onboarding, paths, ui


def cmd_home(_args) -> None:
    if not onboarding.is_complete():
        onboarding.run()
        return
    ui.console.clear()
    ui.banner()
    cmd_status(_args, header=False)
    ui.console.print()
    ui.info("[bold]joby agent[/] pour lancer l'agent · [bold]joby dashboard[/] pour le tableau de bord · "
            "[bold]joby --help[/] pour tout le reste")


def cmd_setup(args) -> None:
    onboarding.run(only=args.step)


def cmd_agent(args) -> None:
    from .pipeline import runner
    paths.ensure_user_dirs()
    try:
        runner.agent_loop(once=args.once)
    except RuntimeError as e:
        ui.error(str(e))
        sys.exit(1)


def cmd_dashboard(args, user_dir=None) -> None:
    app = paths.REPO / "dashboard" / "app.py"
    port = str(args.port or config.load()["dashboard"]["port"])
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", port,
           "--server.address", args.host, "--browser.gatherUsageStats", "false"]
    if args.headless:
        cmd += ["--server.headless", "true"]
    ui.info(f"Dashboard sur http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{port}")
    os.chdir(app.parent)  # pour le thème (dashboard/.streamlit/config.toml)
    os.execvpe(cmd[0], cmd, {**os.environ, "JOBY_USER_DIR": str(user_dir or paths.USER)})


def cmd_status(_args, header: bool = True) -> None:
    if header:
        ui.banner()
    counts = db.counts()
    table = Table(box=None, padding=(0, 3), show_header=False)
    table.add_column(justify="right", style="bold")
    table.add_column()
    for status in db.STATUSES:
        if counts.get(status):
            table.add_row(str(counts[status]), db.label(status))
    if not counts:
        table.add_row("0", "Aucune offre pour l'instant : lance `joby agent`.")
    ui.card(table, title="📊 Tes candidatures")

    with db.connect() as c:
        events = c.execute("SELECT ts, message FROM events ORDER BY id DESC LIMIT 6").fetchall()
    if events:
        t = Table.grid(padding=(0, 2))
        for e in events:
            t.add_row(Text(e["ts"][5:16].replace("T", " "), style=ui.MUTED), e["message"])
        ui.card(t, title="🕒 Dernières actions")
    if counts.get("ready"):
        ui.warn(f"{counts['ready']} dossier(s) t'attendent pour validation dans le dashboard.")
    if counts.get("needs_you"):
        ui.warn(f"{counts['needs_you']} candidature(s) ont besoin de toi dans le dashboard.")


def cmd_login(_args) -> None:
    sites = careerops.sites()
    urls = [s.get("login_url") or s["url"] for s in sites if s.get("needs_account")] or [s["url"] for s in sites]
    if not urls:
        ui.warn("Aucun site configuré. Lance `joby setup --step sites`.")
        return
    onboarding.open_login_browser(urls)


def cmd_sites(args) -> None:
    if args.action == "probe":
        result = careerops.probe(args.name, args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_sectors(args) -> None:
    from .pipeline import sectors
    with ui.console.status("Conception de ta grille de spécialités…"):
        sectors.ensure_taxonomy(force=args.regenerate)
    t = sectors.taxonomy()
    if not t:
        ui.warn("Termine d'abord l'étape « Le poste que tu cherches » (joby setup --step search).")
        return
    if args.reclassify:
        with db.connect() as c:
            c.execute("UPDATE offers SET sector=NULL")
    with ui.console.status("Classement des offres…"):
        n = sectors.classify_missing()
    table = Table(box=None, padding=(0, 2), show_header=False)
    for c in t["categories"]:
        table.add_row(f"[bold]{c['name']}[/]", Text(c["description"], style=ui.MUTED))
    ui.card(table, title=f"🧭 {t['dimension']}")
    ui.success(f"{n} offre(s) classée(s).")


def cmd_doctor(_args) -> None:
    ui.banner("Vérification de l'installation")
    checks = []

    def check(name: str, ok: bool, fix: str = "") -> None:
        checks.append(ok)
        ui.console.print(f"  {'[green]✔[/]' if ok else '[red]✖[/]'} {name}" + (f"  [dim]→ {fix}[/]" if not ok and fix else ""))

    check(f"Python {platform.python_version()}", sys.version_info >= (3, 10), "Python 3.10+ requis")
    check("Node.js", bool(shutil.which("node")), "installe Node.js 20+")
    check("Claude Code (CLI)", bool(shutil.which("claude")), "https://claude.com/claude-code")
    check("Tectonic (LaTeX)", bool(shutil.which("tectonic")), "voir README, section Installation")
    check("CareerOps", (paths.CAREER_OPS / "scan.mjs").exists(), "git submodule update --init")
    check("Dépendances CareerOps", (paths.CAREER_OPS / "node_modules").exists(), "./install.sh")
    check("Navigateur Chromium", bool(careerops.chromium_path()), "cd vendor/career-ops && npx playwright install chromium")
    if shutil.which("claude"):
        from . import claude
        with ui.console.status("Test de la connexion à ton abonnement Claude…"):
            ok = claude.logged_in()
        check("Connexion Claude", ok, "lance `claude` une fois et connecte-toi (ou `claude setup-token` sur un serveur)")
    check("Onboarding terminé", onboarding.is_complete(), "joby setup")
    ui.console.print()
    if all(checks):
        ui.success("Tout est prêt.")
    else:
        ui.warn("Quelques points à régler (voir ci-dessus).")


def cmd_demo(args) -> None:
    demo_dir = paths.REPO / "demo-data"
    with ui.console.status("Préparation des données de démonstration…"):
        subprocess.run([sys.executable, "-m", "joby.demo"], check=True,
                       env={**os.environ, "JOBY_USER_DIR": str(demo_dir)})
    ui.success("Démo prête (données fictives, dans demo-data/). Ouverture du dashboard…")
    cmd_dashboard(argparse.Namespace(port=args.port, host="127.0.0.1", headless=False), user_dir=demo_dir)


def cmd_reset(_args) -> None:
    import questionary
    ui.warn(f"Ceci supprime TOUTES tes données Joby ({paths.USER}) : profil, modèles, candidatures, sessions.")
    if questionary.text("Tape « supprimer » pour confirmer :").ask() == "supprimer":
        for child in paths.USER.iterdir():
            if child.name == "README.md":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        ui.success("Tout est effacé. `joby setup` pour recommencer.")


def main() -> None:
    p = argparse.ArgumentParser(prog="joby", description="Joby, ton agent de recherche d'emploi.")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("setup", help="onboarding (reprend là où tu t'étais arrêté)")
    s.add_argument("--step", choices=onboarding.STEP_KEYS, help="refaire une seule étape")
    s.set_defaults(fn=cmd_setup)

    s = sub.add_parser("agent", help="lance l'agent en continu")
    s.add_argument("--once", action="store_true", help="un seul cycle, puis s'arrête")
    s.set_defaults(fn=cmd_agent)

    s = sub.add_parser("dashboard", help="ouvre le tableau de bord")
    s.add_argument("--port", type=int)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--headless", action="store_true", help="ne pas ouvrir de navigateur (serveur)")
    s.set_defaults(fn=cmd_dashboard)

    sub.add_parser("status", help="résumé rapide").set_defaults(fn=cmd_status)
    sub.add_parser("login", help="te (re)connecter à tes sites carrières").set_defaults(fn=cmd_login)
    sub.add_parser("doctor", help="vérifie l'installation").set_defaults(fn=cmd_doctor)
    s = sub.add_parser("demo", help="essayer le dashboard avec des données fictives")
    s.add_argument("--port", type=int, default=8502)
    s.set_defaults(fn=cmd_demo)
    sub.add_parser("reset", help="efface toutes tes données").set_defaults(fn=cmd_reset)

    s = sub.add_parser("sectors", help="ta grille de spécialités (ventilation des offres)")
    s.add_argument("--regenerate", action="store_true", help="redemander une grille au LLM")
    s.add_argument("--reclassify", action="store_true", help="reclasser toutes les offres")
    s.set_defaults(fn=cmd_sectors)

    s = sub.add_parser("sites", help="outils sur les sites carrières")
    s.add_argument("action", choices=["probe"])
    s.add_argument("name")
    s.add_argument("url")
    s.set_defaults(fn=cmd_sites)

    args = p.parse_args()
    paths.ensure_user_dirs()
    try:
        (getattr(args, "fn", None) or cmd_home)(args)
    except KeyboardInterrupt:
        ui.console.print()
        ui.info("À plus tard !")


if __name__ == "__main__":
    main()
