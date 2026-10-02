#!/usr/bin/env bash
# Démarre l'agent et le dashboard en continu (ils redémarrent aussi avec le serveur).
# Les services ont été créés par deploy/setup-server.sh ; Joby doit être dans ~/joby.
set -euo pipefail

[ "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" = "/home/joby/joby" ] || {
  echo "Joby doit être installé dans /home/joby/joby (voir deploy/DEPLOY.md)."; exit 1; }
~/joby/joby doctor >/dev/null 2>&1 || echo "! joby doctor signale des points à régler : vérifie avec ~/joby/joby doctor"

sudo systemctl enable --now joby-agent joby-dashboard
echo "✔ Services actifs."
echo "  Logs de l'agent : journalctl -u joby-agent -f"
echo "  Dashboard       : depuis ton PC, ssh -N -L 8501:localhost:8501 joby@<ip>  puis http://localhost:8501"
