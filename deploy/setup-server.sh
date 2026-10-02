#!/usr/bin/env bash
# Prépare un serveur Ubuntu 24.04 tout neuf pour Joby. À lancer UNE fois, en root :
#   curl -fsSL https://raw.githubusercontent.com/<toi>/joby/main/deploy/setup-server.sh | bash
# ou, après avoir cloné le repo : sudo bash deploy/setup-server.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "À lancer en root (sudo)."; exit 1; }

echo "▸ Mises à jour et outils système"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip unzip ufw \
  xvfb x11vnc novnc websockify fonts-dejavu >/dev/null

echo "▸ Node.js 22"
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi

echo "▸ Utilisateur « joby » (l'agent ne tourne jamais en root)"
if ! id joby >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" joby
  if [ -f /root/.ssh/authorized_keys ]; then
    mkdir -p /home/joby/.ssh
    cp /root/.ssh/authorized_keys /home/joby/.ssh/
    chown -R joby:joby /home/joby/.ssh
    chmod 700 /home/joby/.ssh && chmod 600 /home/joby/.ssh/authorized_keys
  fi
fi
loginctl enable-linger joby || true

echo "▸ Droits limités : « joby » peut gérer ses propres services, et rien d'autre"
cat > /etc/sudoers.d/joby <<'SUDO'
joby ALL=(root) NOPASSWD: /usr/bin/systemctl enable --now joby-agent joby-dashboard
joby ALL=(root) NOPASSWD: /usr/bin/systemctl start joby-agent, /usr/bin/systemctl stop joby-agent, /usr/bin/systemctl restart joby-agent
joby ALL=(root) NOPASSWD: /usr/bin/systemctl start joby-dashboard, /usr/bin/systemctl stop joby-dashboard, /usr/bin/systemctl restart joby-dashboard
joby ALL=(root) NOPASSWD: /usr/bin/systemctl restart joby-agent joby-dashboard
SUDO
chmod 440 /etc/sudoers.d/joby
visudo -cf /etc/sudoers.d/joby >/dev/null

echo "▸ Services Joby (activés plus tard, une fois Joby installé et configuré)"
cat > /etc/systemd/system/joby-agent.service <<'UNIT'
[Unit]
Description=Joby — agent de recherche d'emploi
After=network-online.target
Wants=network-online.target

[Service]
User=joby
WorkingDirectory=/home/joby/joby
Environment=PATH=/home/joby/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/joby
ExecStart=/home/joby/joby/joby agent
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/systemd/system/joby-dashboard.service <<'UNIT'
[Unit]
Description=Joby — dashboard
After=network-online.target

[Service]
User=joby
WorkingDirectory=/home/joby/joby
Environment=PATH=/home/joby/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/joby
ExecStart=/home/joby/joby/joby dashboard --headless --host 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload

echo "▸ Bibliothèques système du navigateur (Chromium)"
npx --yes playwright@1.63.0 install-deps chromium >/dev/null

echo "▸ Pare-feu : seul SSH est ouvert (le dashboard passe par un tunnel SSH)"
ufw allow OpenSSH >/dev/null
ufw --force enable >/dev/null

echo
echo "✔ Serveur prêt. Suite : connecte-toi en tant que « joby » (ssh joby@<ip>) et suis deploy/DEPLOY.md, étape 3."
