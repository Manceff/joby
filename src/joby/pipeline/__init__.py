"""La pipeline continue : scan → tri → analyse → dossier → (validation) → envoi → suivi mail."""

from __future__ import annotations

from datetime import date

from .. import config, paths


def read(path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def profile_context(*, cv: bool = True, brief: bool = True) -> str:
    """Les documents validés à l'onboarding, prêts à être donnés à Claude."""
    parts = []
    if brief:
        parts.append(f"<search_brief>\n{read(paths.SEARCH_BRIEF)}\n</search_brief>")
    if cv:
        parts.append(f"<master_cv>\n{read(paths.CV_MASTER)}\n</master_cv>")
    return "\n\n".join(parts)


def identity_block() -> str:
    return f"<identity>\n{read(paths.IDENTITY)}\n</identity>"


def today() -> str:
    return date.today().isoformat()


def models() -> dict:
    return config.load()["models"]
