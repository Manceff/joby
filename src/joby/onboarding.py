"""L'onboarding : 9 étapes, menées par Claude Opus quand il s'agit de discuter,
et par Joby lui-même quand il s'agit de secrets (connexions, mail) ou de validation.

Chaque étape conversationnelle est une vraie session Claude Code, centrée sur un
seul sujet. Joby reprend la main entre deux étapes pour afficher la progression.
On peut s'arrêter à tout moment : `joby setup` reprend là où on en était.
"""

from __future__ import annotations

import getpass
import json
import os
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import questionary
from rich.table import Table
from rich.text import Text

from . import careerops, claude, config, latex, paths, ui


@dataclass
class Step:
    key: str
    title: str
    outputs: list[Path] = field(default_factory=list)
    prompt: str | None = None           # étape conversationnelle (Claude)
    native: Callable[[], bool] | None = None  # étape gérée par Joby
    kickoff: str = "Commence l'étape."


# --- État -----------------------------------------------------------------------

def load_state() -> dict:
    if paths.ONBOARDING_STATE.exists():
        return json.loads(paths.ONBOARDING_STATE.read_text(encoding="utf-8"))
    return {"done": []}


def save_state(state: dict) -> None:
    paths.ONBOARDING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def mark_done(key: str) -> None:
    state = load_state()
    if key not in state["done"]:
        state["done"].append(key)
    save_state(state)


def unmark(key: str) -> None:
    state = load_state()
    state["done"] = [k for k in state["done"] if k != key]
    save_state(state)


# --- Étapes gérées par Joby -------------------------------------------------------

def step_logins() -> bool:
    sites = careerops.sites()
    need = [s for s in sites if s.get("needs_account") and s.get("enabled", True)]
    ui.section("Étape 5 · Tes connexions aux sites carrières")
    if not need:
        ui.success("Aucun de tes sites ne demande de compte pour postuler. Rien à faire ici !")
        return True

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Site")
    table.add_column("Page de connexion", style=ui.MUTED)
    for s in need:
        table.add_row(s["name"], s.get("login_url") or s["url"])
    ui.console.print(table)
    ui.console.print()
    ui.card(Text.from_markup(
        "Je vais ouvrir un navigateur [bold]réservé à Joby[/], avec un onglet par site.\n\n"
        "  1. Crée ton compte (ou connecte-toi) sur chaque site, comme d'habitude.\n"
        "  2. Coche « rester connecté » quand c'est proposé.\n"
        "  3. Ferme la fenêtre quand tu as fini.\n\n"
        "[dim]Tes mots de passe restent dans ce navigateur : ni Claude ni Joby ne les voient.\n"
        "L'agent réutilisera simplement ta session pour postuler.[/]"), title="🔐 Comment ça marche")

    if not questionary.confirm("On ouvre le navigateur ?", default=True).ask():
        return False
    ok = open_login_browser([s.get("login_url") or s["url"] for s in need])
    if ok:
        ui.success("Sessions enregistrées. Tu pourras relancer cette étape avec `joby login`.")
    return ok


def _agent_running() -> bool:
    import fcntl
    if not paths.LOCK.exists():
        return False
    with open(paths.LOCK) as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True


def open_login_browser(urls: list[str]) -> bool:
    paths.BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    if _agent_running():
        ui.warn("L'agent tourne et utilise le navigateur : arrête-le le temps de te connecter "
                "(Ctrl+C dans son terminal, ou `sudo systemctl stop joby-agent` sur un serveur).")
        return False
    if platform.system() == "Linux" and not os.environ.get("DISPLAY"):
        ui.warn("Pas d'écran détecté sur cette machine.")
        ui.info("Sur un serveur, lance d'abord le navigateur distant : voir deploy/DEPLOY.md, « Se connecter aux sites ».")
        return False
    env = {**os.environ, "JOBY_CAREER_OPS": str(paths.CAREER_OPS)}
    ui.info("Navigateur ouvert. J'attends que tu le fermes…")
    code = subprocess.call(["node", str(paths.PACKAGE / "browser" / "login.mjs"), str(paths.BROWSER_PROFILE), *urls],
                           env=env)
    return code == 0


PROVIDERS = {
    "Gmail": ("imap.gmail.com", "https://myaccount.google.com/apppasswords",
              "Gmail demande un « mot de passe d'application » (validation en 2 étapes requise)."),
    "Outlook / Hotmail": ("outlook.office365.com", "https://account.live.com/proofs/AppPassword",
                          "Outlook demande un « mot de passe d'application »."),
    "iCloud": ("imap.mail.me.com", "https://appleid.apple.com",
               "iCloud demande un « mot de passe pour app » (Identifiant Apple → Connexion et sécurité)."),
    "Yahoo": ("imap.mail.yahoo.com", "https://login.yahoo.com/account/security",
              "Yahoo demande un « mot de passe d'application »."),
}


def step_mail() -> bool:
    ui.section("Étape 8 · Ta boîte mail")
    ui.card(Text.from_markup(
        "Les recruteurs répondent presque toujours par mail : accusé de réception,\n"
        "proposition d'entretien, refus… En connectant ta boîte, Joby rattache chaque\n"
        "réponse à la bonne candidature et met ton dashboard à jour tout seul.\n\n"
        "[bold]Accès en lecture seule[/] : Joby ne peut ni envoyer, ni supprimer, ni même\n"
        "marquer un mail comme lu."), title="📬 Pourquoi")

    choice = questionary.select(
        "Quelle est ta boîte mail ?",
        choices=[*PROVIDERS.keys(), "Autre (IMAP)", "J'ai déjà mon propre serveur MCP mail", "Plus tard"],
    ).ask()
    if choice in (None, "Plus tard"):
        config.update(mail={"mode": "none"})
        ui.warn("Pas de suivi des mails pour l'instant. Tu pourras le faire avec `joby setup --step mail`.")
        return True

    if choice == "J'ai déjà mon propre serveur MCP mail":
        return _custom_mail_mcp()

    if choice in PROVIDERS:
        host, help_url, help_text = PROVIDERS[choice]
        ui.info(help_text)
        ui.info(f"Crée-le ici : [link={help_url}]{help_url}[/link]")
    else:
        host = questionary.text("Serveur IMAP (ex. imap.ovh.net) :").ask()
        if not host:
            return False
    port = "993"
    user = questionary.text("Adresse mail :", default=(config.read_yaml(paths.IDENTITY, {}) or {}).get("email", "")).ask()
    if not user:
        return False
    password = getpass.getpass("Mot de passe d'application (invisible à la saisie) : ").replace(" ", "")
    config.write_env({"JOBY_IMAP_HOST": host, "JOBY_IMAP_PORT": port, "JOBY_IMAP_USER": user,
                      "JOBY_IMAP_PASSWORD": password})

    from .mail_mcp import check_connection
    with ui.console.status("Test de la connexion…"):
        ok, msg = check_connection()
    if not ok:
        ui.error(f"Connexion impossible : {msg}")
        ui.info("Vérifie l'adresse et le mot de passe d'application, puis réessaie.")
        return False
    config.update(mail={"mode": "imap"})
    ui.success("Boîte mail connectée, en lecture seule.")
    return True


def _custom_mail_mcp() -> bool:
    ui.info(f"Ajoute ton serveur dans [bold]{paths.MCP_CONFIG}[/] au format Claude Code :")
    ui.console.print('  {"mcpServers": {"monmail": {"command": "...", "args": ["..."]}}}', style=ui.MUTED)
    if not paths.MCP_CONFIG.exists():
        paths.MCP_CONFIG.write_text(json.dumps({"mcpServers": {}}, indent=2), encoding="utf-8")
    questionary.press_any_key_to_continue("Appuie sur une touche quand c'est fait…").ask()
    try:
        servers = json.loads(paths.MCP_CONFIG.read_text(encoding="utf-8")).get("mcpServers", {})
    except json.JSONDecodeError:
        ui.error("Le fichier n'est pas du JSON valide.")
        return False
    if not servers:
        ui.error("Aucun serveur trouvé dans le fichier.")
        return False
    name = questionary.select("Lequel est ta boîte mail ?", choices=list(servers)).ask()
    config.update(mail={"mode": "custom", "custom_server_name": name})
    ui.success(f"Serveur « {name} » enregistré. Il doit permettre de lister et lire les mails.")
    return True


def step_recap() -> bool:
    ui.section("Étape 9 · Récapitulatif")
    ident = config.read_yaml(paths.IDENTITY, {}) or {}
    sites = careerops.sites()
    cfg = config.load()

    summary = ""
    if paths.SEARCH_BRIEF.exists():
        text = paths.SEARCH_BRIEF.read_text(encoding="utf-8")
        if "## Validated summary" in text:
            summary = text.split("## Validated summary", 1)[1].split("\n## ", 1)[0].strip()

    ui.card(Text(f"{ident.get('first_name', '')} {ident.get('last_name', '')}\n"
                 f"{ident.get('email', '')} · {ident.get('phone', '')} · {ident.get('city', '')}"),
            title="👤 Profil")
    if summary:
        ui.card(Text(summary), title="🎯 Ce que tu cherches")

    table = Table(box=None, padding=(0, 2), show_header=True, header_style="bold")
    table.add_column("Site")
    table.add_column("Lecture")
    table.add_column("Compte")
    for s in sites:
        table.add_row(s["name"], "API (rapide)" if s.get("kind") == "ats" else "navigateur",
                      "oui" if s.get("needs_account") else "non")
    ui.card(table, title=f"🌐 Sites ciblés ({len(sites)})")

    mail_mode = {"imap": "connectée (lecture seule)", "custom": "ton serveur MCP", "none": "non connectée"}
    checks = [
        ("Modèle de CV", (paths.PREVIEW_DIR / "cv.pdf").exists(), str(paths.PREVIEW_DIR / "cv.pdf")),
        ("Modèle de lettre", (paths.PREVIEW_DIR / "letter.pdf").exists(), str(paths.PREVIEW_DIR / "letter.pdf")),
        ("Signature", paths.SIGNATURE.exists(), "en bas de chaque lettre"),
        ("Boîte mail", cfg["mail"]["mode"] != "none", mail_mode[cfg["mail"]["mode"]]),
    ]
    t2 = Table.grid(padding=(0, 2))
    for name, ok, detail in checks:
        t2.add_row(Text("✔" if ok else "–", style=ui.OK if ok else ui.MUTED), name, Text(detail, style=ui.MUTED))
    ui.card(t2, title="📄 Documents et connexions")

    ui.card(Text.from_markup(
        f"• Un cycle toutes les [bold]{cfg['pipeline']['cycle_hours']} h[/] : scan de tes sites, tri, analyse.\n"
        f"• Seules les offres notées [bold]{cfg['pipeline']['min_score']}/5[/] ou plus reçoivent un dossier.\n"
        f"• CV en [bold]anglais[/], lettre dans la langue de l'offre.\n"
        "• Chaque dossier t'attend dans le dashboard : tu valides en un clic,\n"
        "  et l'agent remplit le formulaire et envoie la candidature pour toi."), title="⚙️  Comment l'agent va travailler")

    if not questionary.confirm("Tout est bon pour toi ?", default=True).ask():
        ui.info("Pas de souci. Relance l'étape à corriger avec `joby setup --step <étape>`.")
        return False
    config.update(pipeline={"enabled": True})
    ui.console.print()
    ui.say(f"[bold {ui.ACCENT}]Joby :[/] Parfait, laisse-moi aller chercher. 🚀")
    return True


# --- Définition du parcours -----------------------------------------------------------

STEPS: list[Step] = [
    Step("profile", "Faisons connaissance", [paths.IDENTITY, paths.ANSWERS], prompt="1-profile.md",
         kickoff="Bonjour !"),
    Step("cv", "Ton CV : lecture et analyse", [paths.CV_MASTER], prompt="2-cv.md"),
    Step("search", "Le poste que tu cherches", [paths.SEARCH_BRIEF, paths.SEARCH_KEYWORDS], prompt="3-search.md"),
    Step("sites", "Tes sites carrières", [paths.SITES], prompt="4-sites.md"),
    Step("logins", "Tes connexions aux sites", native=step_logins),
    Step("cv_design", "La mise en forme de ton CV", [paths.CV_PREFS, paths.PREVIEW_DIR / "cv.pdf"],
         prompt="6-cv-design.md"),
    Step("letter_design", "Ta lettre de motivation", [paths.LETTER_PREFS, paths.PREVIEW_DIR / "letter.pdf"],
         prompt="7-letter-design.md"),
    Step("mail", "Ta boîte mail", native=step_mail),
    Step("recap", "Récapitulatif et lancement", native=step_recap),
]
STEP_KEYS = [s.key for s in STEPS]


def _system_prompt(step: Step) -> str:
    joby_cmd = str(paths.REPO / "joby")
    text = claude.prompt_file("onboarding/_guidelines.md") + "\n\n---\n\n" + claude.prompt_file(f"onboarding/{step.prompt}")
    return text.replace("{USER}", str(paths.USER)).replace("{JOBY}", joby_cmd)


ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
           "Bash(cp:*)", "Bash(mkdir:*)", "Bash(ls:*)", "Bash(cd:*)", "Bash(tectonic:*)",
           "Bash(open:*)", "Bash(xdg-open:*)", "Bash(sips:*)", "Bash(convert:*)", "Bash(magick:*)",
           f"Bash({paths.REPO / 'joby'}:*)"]


def run_claude_step(step: Step) -> bool:
    if step.key in ("cv_design", "letter_design"):
        latex.install_default_templates()
    model = config.load()["models"]["onboarding"]
    claude.interactive(step.kickoff, system=_system_prompt(step), model=model, cwd=paths.USER, allowed=ALLOWED)
    missing = [p for p in step.outputs if not p.exists()]
    if missing:
        ui.warn("Cette étape ne semble pas terminée (rien n'a encore été validé).")
        return False
    return True


def welcome() -> None:
    ui.console.clear()
    ui.banner()
    ui.card(Text.from_markup(
        "Bienvenue ! 👋\n\n"
        "On va configurer ensemble ta recherche d'emploi. Je vais te poser des questions,\n"
        "lire ton CV, comprendre précisément ce que tu cherches et préparer avec toi\n"
        "des modèles de CV et de lettre qui te ressemblent.\n\n"
        "[bold]Prends ton temps :[/] plus tu es précis maintenant, meilleures seront tes\n"
        "candidatures. Tu peux t'arrêter quand tu veux, on reprendra au même endroit.\n\n"
        "[dim]Prévois environ 45 minutes, ton CV, et si tu en as, des exemples de CV et\n"
        "de lettres que tu aimes.[/]"), title="✨ Joby")


def run(only: str | None = None) -> None:
    paths.ensure_user_dirs()
    welcome()
    steps = STEPS if not only else [s for s in STEPS if s.key == only]
    if only and not steps:
        ui.error(f"Étape inconnue : {only}. Étapes : {', '.join(STEP_KEYS)}")
        return
    if only:
        unmark(only)

    for step in steps:
        state = load_state()
        done = set(state["done"])
        if step.key in done and not only:
            continue
        ui.console.print()
        ui.console.print(ui.step_board([(s.key, s.title) for s in STEPS], done, step.key))
        ui.console.print()

        if step.prompt:
            ui.info(f"[bold]{step.title}[/] — je te passe Claude pour cette étape.")
            ui.info("Quand il te le dira, tape [bold]/exit[/] pour revenir ici.")
            if not questionary.confirm("Prêt ?", default=True).ask():
                ui.info("À plus tard ! Relance `joby setup` pour reprendre.")
                return
            ok = run_claude_step(step)
        else:
            ok = step.native()

        if not ok:
            if questionary.confirm("Reprendre cette étape maintenant ?", default=True).ask():
                return run(only)
            ui.info("À plus tard ! Relance `joby setup` pour reprendre.")
            return
        mark_done(step.key)
        ui.success(f"{step.title} : c'est fait.")

    done = set(load_state()["done"])
    ui.console.print()
    ui.console.print(ui.step_board([(s.key, s.title) for s in STEPS], done))
    if set(STEP_KEYS) <= done:
        _after_onboarding()


def _after_onboarding() -> None:
    ui.console.print()
    ui.card(Text.from_markup(
        "Ta configuration est complète. 🎉\n\n"
        "  [bold]joby agent[/]       lance l'agent (il tourne en continu)\n"
        "  [bold]joby dashboard[/]   ouvre ton tableau de bord\n"
        "  [bold]joby status[/]      résumé rapide dans le terminal\n\n"
        "[dim]Pour le faire tourner 24h/24 sur un serveur : deploy/DEPLOY.md[/]"), title="🚀 Et maintenant", style=ui.OK)
    if questionary.confirm("Lancer l'agent maintenant sur cette machine ?", default=True).ask():
        from .pipeline import runner
        runner.agent_loop()


def is_complete() -> bool:
    return set(STEP_KEYS) <= set(load_state()["done"])
