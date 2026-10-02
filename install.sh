#!/usr/bin/env bash
# Installation de Joby (macOS et Linux). Relançable sans risque.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

bold=$'\e[1m'; dim=$'\e[2m'; blue=$'\e[38;5;111m'; green=$'\e[32m'; yellow=$'\e[33m'; red=$'\e[31m'; reset=$'\e[0m'
step() { printf "\n${blue}${bold}▸ %s${reset}\n" "$1"; }
ok()   { printf "  ${green}✔${reset} %s\n" "$1"; }
warn() { printf "  ${yellow}!${reset} %s\n" "$1"; }
die()  { printf "  ${red}✖ %s${reset}\n" "$1"; exit 1; }

OS="$(uname -s)"
printf "\n${blue}${bold}  Joby${reset} ${dim}— installation${reset}\n"

step "Outils de base"
command -v git >/dev/null || die "git est requis."
ok "git"

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then PY="$c"; break; fi
done
[ -n "$PY" ] || die "Python 3.10+ est requis (macOS : brew install python · Linux : sudo apt install python3 python3-venv)."
ok "Python ($($PY --version 2>&1))"

command -v node >/dev/null || die "Node.js 20+ est requis (macOS : brew install node · Linux : voir deploy/DEPLOY.md)."
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] || die "Node.js 20+ est requis (version actuelle : $(node --version))."
ok "Node.js ($(node --version))"

step "CareerOps (le socle de Joby)"
if [ -d .git ]; then git submodule update --init --recursive; fi
[ -f vendor/career-ops/scan.mjs ] || die "vendor/career-ops est vide. Clone le repo avec : git clone --recursive <url>"
(cd vendor/career-ops && npm install --no-audit --no-fund --ignore-scripts --silent)
ok "CareerOps et ses dépendances"

step "Navigateur de l'agent (Chromium)"
(cd vendor/career-ops && npx --yes playwright install chromium)
[ "$OS" = "Linux" ] && warn "Sur Linux, les bibliothèques système de Chromium s'installent avec deploy/setup-server.sh (root)."
ok "Chromium"

step "LaTeX (Tectonic)"
if command -v tectonic >/dev/null; then
  ok "Tectonic déjà installé"
elif [ "$OS" = "Darwin" ] && command -v brew >/dev/null; then
  brew install tectonic && ok "Tectonic"
else
  mkdir -p "$HOME/.local/bin"
  (cd "$HOME/.local/bin" && curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh) \
    && ok "Tectonic (dans ~/.local/bin)" || warn "Installe Tectonic à la main : https://tectonic-typesetting.github.io"
  case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "Ajoute ~/.local/bin à ton PATH (echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc)";; esac
fi

step "Environnement Python"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .
ok "Dépendances Python"

step "Claude Code"
if command -v claude >/dev/null; then
  ok "Claude Code ($(claude --version 2>/dev/null | head -1))"
else
  warn "Claude Code n'est pas installé : curl -fsSL https://claude.ai/install.sh | bash"
  warn "Puis lance « claude » une fois pour te connecter avec ton abonnement."
fi

step "Commande joby"
mkdir -p "$HOME/.local/bin"
ln -sf "$DIR/joby" "$HOME/.local/bin/joby"
ok "joby → ~/.local/bin/joby"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "~/.local/bin n'est pas dans ton PATH : en attendant, utilise $DIR/joby";; esac

printf "\n${green}${bold}  Installation terminée.${reset}\n\n"
printf "  Lance ${bold}joby${reset} pour commencer ta configuration.\n"
printf "  ${dim}(ou ${bold}joby demo${reset}${dim} pour découvrir le dashboard avec des données fictives)${reset}\n\n"
