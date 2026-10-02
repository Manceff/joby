"""Configuration utilisateur (`user/config.yml`) et secrets (`user/.env`)."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

from . import paths

DEFAULTS: dict[str, Any] = {
    "cv": {
        # Le CV est toujours rédigé en anglais.
        "language": "en",
    },
    "letter": {
        # "auto" = la langue de l'offre ; sinon "fr", "en"...
        "language": "auto",
    },
    "pipeline": {
        "enabled": False,
        "cycle_hours": 3,
        "custom_sites_every_hours": 12,
        "min_score": 4.0,
        "max_offer_age_days": 30,
        "max_analyses_per_cycle": 20,
        "max_dossiers_per_cycle": 3,
        "proofread": True,
    },
    "models": {
        "onboarding": "opus",
        "prescreen": "haiku",
        "analysis": "sonnet",
        "writing": "opus",
        "apply": "sonnet",
        "browse": "sonnet",
        "mail": "haiku",
    },
    "browser": {
        "headless": True,
    },
    "mail": {
        # "imap" (serveur MCP intégré), "custom" (ton propre serveur MCP), "none"
        "mode": "none",
        "custom_server_name": "",
        "last_check": None,
    },
    "dashboard": {
        "port": 8501,
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict[str, Any]:
    data = {}
    if paths.CONFIG.exists():
        data = yaml.safe_load(paths.CONFIG.read_text(encoding="utf-8")) or {}
    return _merge(DEFAULTS, data)


def save(cfg: dict[str, Any]) -> None:
    paths.CONFIG.parent.mkdir(parents=True, exist_ok=True)
    header = "# Configuration de Joby. Modifiable à la main ; `joby doctor` vérifie qu'elle est valide.\n"
    paths.CONFIG.write_text(header + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")


def update(**sections: dict[str, Any]) -> dict[str, Any]:
    cfg = load()
    cfg = _merge(cfg, sections)
    save(cfg)
    return cfg


# --- Secrets -----------------------------------------------------------------

def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if paths.ENV_FILE.exists():
        for line in paths.ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')
    return env


def write_env(values: dict[str, str]) -> None:
    env = read_env()
    env.update(values)
    paths.ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    body = "# Secrets de Joby — ne jamais partager ce fichier.\n" + "".join(
        f'{k}="{v}"\n' for k, v in env.items()
    )
    paths.ENV_FILE.write_text(body, encoding="utf-8")
    os.chmod(paths.ENV_FILE, 0o600)


def read_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or default
