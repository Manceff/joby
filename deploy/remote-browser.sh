#!/usr/bin/env bash
# Ouvre le navigateur de Joby sur le serveur, affiché dans TON navigateur via un tunnel SSH,
# pour te connecter à tes sites carrières (les sessions restent sur le serveur).
#
# Sur ton PC :      ssh -L 6080:localhost:6080 joby@<ip>
# Sur le serveur :  ./deploy/remote-browser.sh
# Puis ouvre :      http://localhost:6080/vnc.html  et clique « Connect »
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISPLAY_NUM=":99"

# L'agent et toi ne pouvez pas utiliser le même navigateur en même temps : on le met en pause.
AGENT_WAS_ACTIVE=0
if systemctl is-active --quiet joby-agent 2>/dev/null; then
  AGENT_WAS_ACTIVE=1
  sudo systemctl stop joby-agent
fi

cleanup() {
  kill "${XVFB_PID:-}" "${VNC_PID:-}" "${WS_PID:-}" 2>/dev/null || true
  [ "$AGENT_WAS_ACTIVE" = 1 ] && sudo systemctl start joby-agent && echo "Agent relancé."
}
trap cleanup EXIT

Xvfb "$DISPLAY_NUM" -screen 0 1440x900x24 >/dev/null 2>&1 & XVFB_PID=$!
sleep 1
x11vnc -display "$DISPLAY_NUM" -localhost -nopw -forever -quiet >/dev/null 2>&1 & VNC_PID=$!
websockify --web /usr/share/novnc 127.0.0.1:6080 127.0.0.1:5900 >/dev/null 2>&1 & WS_PID=$!
sleep 1

echo "Navigateur distant prêt : ouvre http://localhost:6080/vnc.html sur ton PC (tunnel SSH actif)."
echo "Connecte-toi à tes sites, puis ferme la fenêtre du navigateur pour terminer."
DISPLAY="$DISPLAY_NUM" "$DIR/joby" login
