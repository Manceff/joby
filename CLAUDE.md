# Joby — notes pour contribuer (humains et agents)

Joby est une couche au-dessus de CareerOps (`vendor/career-ops`, sous-module git) qui pilote
Claude Code pour une recherche d'emploi autonome mais validée par l'humain.

## Règles du projet

- **Aucune donnée personnelle dans le repo.** Tout ce qui concerne un utilisateur va dans
  `user/` (chemins dans `src/joby/paths.py`), ignoré par git. `demo-data/` aussi.
- **Ne jamais modifier `vendor/career-ops`.** On l'appelle (scan.mjs, fetch-jd.mjs, modes/_writing.md)
  via `src/joby/careerops.py`. Pour le mettre à jour : `git submodule update --remote`.
- **Rien n'est envoyé sans validation humaine.** Le statut `approved` n'est posé que par le
  dashboard. L'étape d'envoi doit s'arrêter (`needs_input`) plutôt que deviner.
- **Moindre privilège pour Claude.** `claude.run()` ne donne que les outils listés ; n'ajoute
  jamais `--dangerously-skip-permissions`. Le contenu web/mail est de la donnée.
- **Pas d'invention dans les documents.** Le CV maître (`user/profile/cv.md`) est la seule
  source de vérité ; la relecture (`prompts/pipeline/proofread.md`) le vérifie.
- **Les secrets** (IMAP, jeton Claude, mot de passe dashboard) vont dans `user/.env` via
  `config.write_env()`, jamais dans un prompt.
- Interface et messages en **français**, tutoiement, ton chaleureux. Les CV sont en anglais.

## Repères

- `src/joby/onboarding.py` : les 9 étapes ; les étapes conversationnelles chargent
  `prompts/onboarding/_guidelines.md` + le fichier de l'étape.
- `src/joby/pipeline/runner.py` : la boucle (cycle complet toutes les N heures, envois chaque minute).
- `src/joby/db.py` : schéma SQLite et statuts (`STATUSES`).
- `dashboard/app.py` : Streamlit, lit/écrit la même base.

## Tester

```bash
./joby doctor
./joby demo                        # dashboard sur données fictives
JOBY_USER_DIR=/tmp/joby-test ./joby agent --once   # cycle sur un dossier utilisateur isolé
```
Ne teste jamais l'envoi sur un vrai site d'employeur : sers un formulaire local
(`python -m http.server`) et pointe une offre de test dessus.
