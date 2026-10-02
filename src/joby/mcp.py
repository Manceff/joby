"""Serveurs MCP donnés à Claude selon l'étape : navigateur (Playwright) et boîte mail."""

from __future__ import annotations

import json
import sys
from typing import Any

from . import careerops, config, paths

PLAYWRIGHT_MCP = "@playwright/mcp@0.0.83"


def browser(headless: bool | None = None) -> dict[str, Any]:
    """Navigateur persistant : il réutilise les sessions ouvertes avec `joby login`."""
    cfg = config.load()
    if headless is None:
        headless = cfg["browser"]["headless"]
    args = ["-y", PLAYWRIGHT_MCP, "--user-data-dir", str(paths.BROWSER_PROFILE),
            "--output-dir", str(paths.WORK / "browser"), "--viewport-size", "1366,900",
            "--image-responses", "omit"]
    exe = careerops.chromium_path()
    if exe:
        args += ["--executable-path", exe]
    if headless:
        args.append("--headless")
    return {"browser": {"command": "npx", "args": args}}


def mail() -> dict[str, Any]:
    cfg = config.load()["mail"]
    if cfg["mode"] == "imap":
        return {"mail": {"command": sys.executable, "args": ["-m", "joby.mail_mcp"],
                         "env": {"JOBY_USER_DIR": str(paths.USER)}}}
    if cfg["mode"] == "custom" and paths.MCP_CONFIG.exists():
        servers = json.loads(paths.MCP_CONFIG.read_text(encoding="utf-8")).get("mcpServers", {})
        name = cfg.get("custom_server_name")
        if name in servers:
            return {"mail": servers[name]}
    return {}


BROWSER_TOOLS = ["mcp__browser"]
MAIL_TOOLS = ["mcp__mail"]
