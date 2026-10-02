"""Pont vers le CLI Claude Code : sessions interactives (onboarding) et appels headless (pipeline).

La pipeline n'utilise jamais `--dangerously-skip-permissions`. Chaque étape reçoit
uniquement les outils dont elle a besoin : aucun pour l'analyse et la rédaction,
le navigateur pour candidater, la boîte mail (lecture seule) pour le suivi. Le
contenu des pages web et des mails est traité comme de la donnée, jamais comme
des instructions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config, paths

QUOTA_MARKERS = ("usage limit", "limit reached", "rate limit", "rate_limit", "quota", "credit balance")


class ClaudeError(RuntimeError):
    pass


class QuotaReached(ClaudeError):
    """L'abonnement Claude a atteint sa limite d'usage : on réessaiera au prochain cycle."""


@dataclass
class Result:
    data: Any
    text: str
    cost_usd: float
    raw: dict


def binary() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise ClaudeError("Le CLI `claude` est introuvable. Installe Claude Code : https://claude.com/claude-code")
    return exe


def _env() -> dict[str, str]:
    env = dict(os.environ)
    token = config.read_env().get("CLAUDE_CODE_OAUTH_TOKEN")
    if token and not env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    return env


def prompt_file(name: str) -> str:
    return (paths.PROMPTS / name).read_text(encoding="utf-8")


def run(prompt: str, *, system: str, model: str, schema: dict | None = None,
        tools: list[str] | None = None, mcp: dict | None = None,
        add_dirs: list[Path] | None = None, timeout: int = 900, effort: str | None = None) -> Result:
    """Appel headless. `tools` = outils autorisés (built-in ou mcp__*). Rien d'autre n'est permis."""
    paths.WORK.mkdir(parents=True, exist_ok=True)
    tools = tools or []
    builtin = [t for t in tools if not t.startswith("mcp__")]
    cmd = [
        binary(), "-p",
        "--model", model,
        "--output-format", "json",
        "--no-session-persistence",
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--permission-prompts", "none",
        "--append-system-prompt", system,
        "--tools", ",".join(builtin) if builtin else "",
    ]
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    if mcp:
        cmd += ["--mcp-config", json.dumps({"mcpServers": mcp})]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    if effort:
        cmd += ["--effort", effort]
    for d in add_dirs or []:
        cmd += ["--add-dir", str(d)]

    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              cwd=paths.WORK, env=_env(), timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ClaudeError(f"Claude n'a pas répondu en {timeout // 60} min") from e

    out = proc.stdout.strip()
    try:
        raw = json.loads(out) if out else {}
    except json.JSONDecodeError:
        raw = {}
    text = str(raw.get("result") or out or proc.stderr)
    if proc.returncode != 0 or raw.get("is_error"):
        blob = f"{text}\n{proc.stderr}".lower()
        if any(m in blob for m in QUOTA_MARKERS):
            raise QuotaReached(text.strip()[:300])
        raise ClaudeError(text.strip()[:500] or f"code de sortie {proc.returncode}")

    data: Any = raw.get("structured_output")
    if schema and data is None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ClaudeError("Réponse JSON invalide de Claude") from e
    return Result(data=data, text=text, cost_usd=float(raw.get("total_cost_usd") or 0), raw=raw)


def interactive(first_message: str, *, system: str, model: str, cwd: Path,
                allowed: list[str] | None = None, mcp: dict | None = None) -> int:
    """Ouvre une vraie conversation Claude Code dans le terminal (utilisée par l'onboarding)."""
    cmd = [binary(), "--model", model, "--append-system-prompt", system,
           "--permission-mode", "acceptEdits", "-n", "Joby · onboarding"]
    if allowed:
        cmd += ["--allowedTools", ",".join(allowed)]
    if mcp:
        cmd += ["--mcp-config", json.dumps({"mcpServers": mcp})]
    cmd.append(first_message)
    return subprocess.call(cmd, cwd=cwd, env=_env())


def logged_in() -> bool:
    """Vérifie, sans rien consommer de notable, que le CLI est authentifié."""
    try:
        run("Réponds uniquement: ok", system="Réponds en un mot.", model="haiku", timeout=120)
        return True
    except ClaudeError:
        return False
