# Faire tourner Joby 24h/24 sur un serveur

Un serveur, c'est un ordinateur qui ne s'éteint jamais. Ce guide part d'un serveur
**Ubuntu 24.04** tout neuf (Hetzner, OVH, Scaleway, DigitalOcean… peu importe).
Compte une trentaine de minutes.

> **Le plus simple :** fais l'onboarding sur ton PC (glisser-déposer du CV, aperçu
> des PDF…), puis copie ta configuration sur le serveur (étape 5). Tu peux aussi tout
> faire directement sur le serveur, en SSH.

---

## 1. Louer le serveur

- **Taille :** 2 vCPU et 4 Go de RAM suffisent largement (chez Hetzner : la plus petite
  instance « Cloud » x86, quelques euros par mois).
- **Système :** Ubuntu 24.04.
- **Accès :** ajoute ta clé SSH au moment de la création (Hetzner le propose dans le
  formulaire). Pas de clé ? Sur ton PC : `ssh-keygen -t ed25519`, puis copie le contenu
  de `~/.ssh/id_ed25519.pub`.

Note l'adresse IP du serveur, on l'appellera `<ip>`.

## 2. Préparer le serveur (une seule fois)

```bash
ssh root@<ip>
git clone --recursive https://github.com/<toi>/joby.git /tmp/joby
bash /tmp/joby/deploy/setup-server.sh
exit
```

Ce script installe Python, Node.js, le navigateur distant, crée un utilisateur `joby`
(l'agent ne tourne jamais en root) et ferme tous les ports sauf SSH.

## 3. Installer Joby

```bash
ssh joby@<ip>
git clone --recursive https://github.com/<toi>/joby.git ~/joby
cd ~/joby && ./install.sh
```

## 4. Connecter ton abonnement Claude

```bash
curl -fsSL https://claude.ai/install.sh | bash   # si install.sh t'a dit que Claude Code manquait
claude setup-token
```

`setup-token` affiche un lien : ouvre-le sur ton PC, connecte-toi avec ton compte Claude,
puis copie le jeton affiché. Enregistre-le pour Joby :

```bash
echo 'CLAUDE_CODE_OAUTH_TOKEN="<le jeton>"' >> ~/joby/user/.env && chmod 600 ~/joby/user/.env
./joby doctor
```

Toutes les lignes de `joby doctor` doivent être vertes (sauf l'onboarding si tu ne l'as pas encore copié).

## 5. Ta configuration

**Option A : tu as fait l'onboarding sur ton PC.** Depuis ton PC :

```bash
cd ~/joby   # ton dossier Joby local
rsync -av --exclude browser/ --exclude work/ --exclude logs/ --exclude '.agent.lock' user/ joby@<ip>:~/joby/user/
```

Le dossier `browser/` (tes sessions de connexion) n'est volontairement pas copié : elles
sont chiffrées pour ton PC et ne fonctionneraient pas sur le serveur. Refais simplement
l'étape 6.

**Option B : tout faire sur le serveur.** `./joby setup` fonctionne en SSH. Pour ton CV,
envoie-le d'abord depuis ton PC : `scp ~/Documents/MonCV.pdf joby@<ip>:~/joby/user/profile/cv-source/`,
puis indique ce chemin à Claude quand il te le demande. Les aperçus de CV et de lettre
s'afficheront dans le dashboard, page « Mes modèles » (étape 8).

## 6. Se connecter aux sites carrières (si certains demandent un compte)

Le navigateur de l'agent tourne sur le serveur ; tu vas l'afficher dans le tien.

```bash
# Sur ton PC : un tunnel SSH
ssh -L 6080:localhost:6080 joby@<ip>
# Puis, dans cette session SSH :
cd ~/joby && ./deploy/remote-browser.sh
```

Ouvre <http://localhost:6080/vnc.html> sur ton PC, clique **Connect** : tu vois le
navigateur de Joby avec un onglet par site. Connecte-toi (coche « rester connecté »),
puis ferme la fenêtre. C'est tout : tes mots de passe ne sont stockés nulle part ailleurs
que dans ce navigateur, et l'agent ne les voit jamais.

À refaire si un jour le dashboard te signale « session expirée ».

## 7. Lancer l'agent en continu

```bash
cd ~/joby && ./deploy/install-services.sh
```

L'agent et le dashboard démarrent, et redémarreront tout seuls (y compris après un
redémarrage du serveur).

| Pour… | Commande |
|---|---|
| voir ce que fait l'agent en direct | `journalctl -u joby-agent -f` |
| un résumé rapide | `~/joby/joby status` |
| arrêter / relancer l'agent | `sudo systemctl stop joby-agent` / `start` |
| mettre Joby à jour | `cd ~/joby && git pull --recurse-submodules && ./install.sh && sudo systemctl restart joby-agent joby-dashboard` |

## 8. Ouvrir ton dashboard

Le dashboard n'est pas exposé sur Internet (tes candidatures sont des données
personnelles). Tu y accèdes par un tunnel SSH, depuis ton PC :

```bash
ssh -N -L 8501:localhost:8501 joby@<ip>
```

puis <http://localhost:8501>. Laisse le terminal ouvert tant que tu utilises le dashboard.

**Envie d'y accéder depuis ton téléphone ?** Installe [Tailscale](https://tailscale.com)
sur le serveur et sur ton téléphone (gratuit pour un usage perso) : ton dashboard sera
joignable sur `http://<nom-du-serveur>:8501` uniquement depuis tes appareils. Dans ce
cas, lance le dashboard avec `--host 0.0.0.0` (modifie `/etc/systemd/system/joby-dashboard.service`)
et ajoute un mot de passe :

```bash
echo 'JOBY_DASHBOARD_PASSWORD="un-mot-de-passe-solide"' >> ~/joby/user/.env
sudo systemctl restart joby-dashboard
```

## Sauvegarder

Tout ce qui compte est dans `~/joby/user/`. Pour le récupérer sur ton PC :

```bash
rsync -av joby@<ip>:~/joby/user/ ~/joby-backup/
```
