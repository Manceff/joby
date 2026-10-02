"""Où vit chaque chose. Tout ce qui est personnel est sous `user/`, jamais versionné."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("JOBY_HOME", PACKAGE.parent.parent)).resolve()

CAREER_OPS = REPO / "vendor" / "career-ops"
PROMPTS = PACKAGE / "prompts"
DEFAULT_TEMPLATES = PACKAGE / "templates" / "latex"

USER = Path(os.environ.get("JOBY_USER_DIR", REPO / "user")).resolve()
CONFIG = USER / "config.yml"
ENV_FILE = USER / ".env"
DB = USER / "joby.db"
LOCK = USER / ".agent.lock"
RUN_NOW = USER / ".run-now"
LOG = USER / "logs" / "agent.log"

PROFILE = USER / "profile"
IDENTITY = PROFILE / "identity.yml"
CV_SOURCE_DIR = PROFILE / "cv-source"
CV_MASTER = PROFILE / "cv.md"
SEARCH_BRIEF = PROFILE / "search.md"
SEARCH_KEYWORDS = PROFILE / "keywords.yml"
SITES = PROFILE / "sites.yml"
CV_PREFS = PROFILE / "cv-preferences.md"
LETTER_PREFS = PROFILE / "letter-preferences.md"
ANSWERS = PROFILE / "answers.md"
SIGNATURE = PROFILE / "signature.png"
EXAMPLES_DIR = PROFILE / "examples"

TEMPLATES = USER / "templates"
CV_TEMPLATE = TEMPLATES / "cv.tex"
LETTER_TEMPLATE = TEMPLATES / "letter.tex"
PREVIEW_DIR = TEMPLATES / "preview"

BROWSER_PROFILE = USER / "browser"
MCP_CONFIG = USER / "mcp.json"
CAREER_OPS_DATA = USER / "careerops"
APPLICATIONS_DIR = USER / "applications"
WORK = USER / "work"
ONBOARDING_STATE = USER / "onboarding.json"


def ensure_user_dirs() -> None:
    for d in (USER, PROFILE, CV_SOURCE_DIR, EXAMPLES_DIR, TEMPLATES, PREVIEW_DIR,
              BROWSER_PROFILE, CAREER_OPS_DATA, APPLICATIONS_DIR, WORK, LOG.parent):
        d.mkdir(parents=True, exist_ok=True)
