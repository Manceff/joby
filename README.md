<h1 align="center">Joby</h1>

<p align="center"><strong>Ton agent de recherche d'emploi. Peu de candidatures, toutes irréprochables.</strong></p>

<p align="center">
Il cherche jour et nuit, uniquement sur les sites que tu as choisis,<br>
ne retient que les offres qui te correspondent vraiment, et prépare pour chacune<br>
un CV et une lettre réellement écrits pour elle. Tu valides en un clic, il postule.
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#comment-ça-marche">Comment ça marche</a> ·
  <a href="deploy/DEPLOY.md">Serveur 24h/24</a> ·
  <a href="#confidentialité-et-sécurité">Confidentialité</a> ·
  <a href="#faq">FAQ</a>
</p>

---

## Pourquoi Joby

Les outils de candidature automatique jouent la quantité : des centaines de candidatures
génériques, des CV qui suivent *leur* modèle, pas le tien. Joby fait l'inverse.

- **Qualité avant quantité.** Chaque offre est lue et notée par rapport à ce que *tu* cherches.
  Seules les meilleures reçoivent un dossier.
- **Ultra-personnalisé.** Un long onboarding en conversation avec Claude Opus : ton parcours,
  tes envies, tes deal-breakers, la mise en forme exacte de ton CV et de ta lettre.
- **Tes sites, et seulement eux.** Tu donnes la liste des pages carrières qui t'intéressent ;
  Joby n'ira jamais ramasser des offres ailleurs.
- **Des documents irréprochables.** CV (toujours en anglais) et lettre en LaTeX, sur *tes*
  modèles. Un relecteur indépendant traque toute information inventée avant que tu ne voies le dossier.
- **Tu gardes la main, sans perdre de temps.** Tu relis chaque dossier dans le dashboard et tu
  cliques sur « Valider » : l'agent ouvre le site, remplit le formulaire, joint tes documents
  et envoie. S'il tombe sur une question à laquelle tu n'as jamais répondu, il s'arrête et te demande.
- **Autonome.** Il tourne en continu (sur ton PC ou sur un petit serveur) et suit les réponses
  des recruteurs dans ta boîte mail.

Joby est construit sur [**CareerOps**](https://github.com/career-ops-hq/career-ops) (scanner de
plus de 100 ATS, extraction des offres, règles d'écriture) et fonctionne avec **ton propre
abonnement Claude**, via [Claude Code](https://claude.com/claude-code).

## Comment ça marche

```
  ┌────────────────────┐
  │     Onboarding     │  9 étapes en conversation : profil, CV, poste recherché,
  │  (une seule fois)  │  sites, connexions, modèle de CV, modèle de lettre, mail
  └─────────┬──────────┘
            ▼
  ┌──────────────────────────────── toutes les 3 h ───────────────────────────────┐
  │  Repérage ──▶ Présélection ──▶ Analyse ──▶ Dossier ──▶ Relecture              │
  │  tes sites    sur l'intitulé   note /5     CV + lettre   aucun fait inventé   │
  │  uniquement   (modèle léger)   vs ton      en LaTeX      sinon on réécrit     │
  │                                profil                                         │
  └───────────────────────────────────────────────────────┬───────────────────────┘
                                                          ▼
                     ┌───────────────────────────────────────────────────┐
                     │ Dashboard : tu relis, tu valides en un clic (ou   │
                     │ tu demandes une retouche, ou tu écartes)          │
                     └───────────────────────┬───────────────────────────┘
                                             ▼
          Envoi : l'agent remplit le formulaire dans son navigateur (tes sessions
          sont déjà ouvertes), joint CV et lettre, vérifie le récapitulatif, envoie.
                                             ▼
          Suivi : il lit ta boîte (lecture seule) et rattache chaque réponse à sa
          candidature : accusé de réception, entretien, refus, offre.
```

## Installation

### Ce qu'il te faut

- un Mac ou un PC Linux (Windows : via [WSL](https://learn.microsoft.com/fr-fr/windows/wsl/install)) ;
- un **abonnement Claude** (Pro ou Max) et [Claude Code](https://claude.com/claude-code) :
  `curl -fsSL https://claude.ai/install.sh | bash`, puis lance `claude` une fois pour te connecter ;
- **Python 3.10+**, **Node.js 20+** et **git** (sur Mac : `brew install python node git`).

### Trois commandes

```bash
git clone --recursive https://github.com/<toi>/joby.git
cd joby
./install.sh
```

L'installateur récupère CareerOps, le navigateur de l'agent, LaTeX (Tectonic) et tout le
reste, puis vérifie que tout est en place. Ensuite :

```bash
joby
```

… et laisse-toi guider. 🙂

> Envie de voir à quoi ça ressemble avant de te lancer ? `joby demo` ouvre le dashboard
> avec des données fictives.

## L'onboarding

| # | Étape | Avec qui | Ce qu'on y fait |
|---|---|---|---|
| 1 | Faisons connaissance | Claude | coordonnées, réponses types des formulaires (autorisation de travail, préavis…) |
| 2 | Ton CV | Claude | lecture, analyse de ton parcours, enrichissement ; devient la seule source de vérité |
| 3 | Le poste que tu cherches | Claude | une vraie discussion, jusqu'à un résumé que tu valides ; c'est la boussole de l'agent |
| 4 | Tes sites carrières | Claude | chaque lien est testé : fonctionne-t-il, combien d'offres, faut-il un compte ? |
| 5 | Tes connexions | toi | un navigateur dédié s'ouvre : tu te connectes toi-même ; personne ne voit tes mots de passe |
| 6 | Ton CV | Claude | type, typo, sections, en-tête, règles d'adaptation… jusqu'à ce que le rendu te plaise |
| 7 | Ta lettre | Claude | même chose, plus ta signature et ta façon d'écrire |
| 8 | Ta boîte mail | toi | connexion en lecture seule (Gmail, Outlook, iCloud, tout IMAP, ou ton propre serveur MCP) |
| 9 | Récapitulatif | toi | tu vérifies tout, tu valides : « Parfait, laisse-moi aller chercher. » |

Tu peux t'arrêter à tout moment : `joby setup` reprend là où tu en étais, et
`joby setup --step <étape>` refait une étape précise.

## Les commandes

| Commande | Ce qu'elle fait |
|---|---|
| `joby` | accueil (lance l'onboarding s'il n'est pas terminé) |
| `joby agent` | démarre l'agent en continu (`--once` pour un seul cycle) |
| `joby dashboard` | ouvre le tableau de bord |
| `joby status` | résumé rapide dans le terminal |
| `joby login` | te reconnecter à tes sites carrières |
| `joby doctor` | vérifie l'installation |
| `joby demo` | essayer le dashboard avec des données fictives |
| `joby reset` | efface toutes tes données |

## Le dashboard

- **Vue d'ensemble** : chiffres clés, entonnoir, activité de l'agent, bouton « lancer un cycle ».
- **À valider** : chaque dossier avec la note, les points forts et de vigilance, les notes de
  rédaction, et l'aperçu du CV et de la lettre côte à côte. *Valider*, *Demander une retouche* ou *Écarter*.
- **Action requise** : les questions que l'agent n'a pas voulu deviner. Tes réponses peuvent
  être mémorisées pour les prochaines fois.
- **Candidatures** : tout ce qui est parti, les mails reçus, les documents envoyés.
- **Offres repérées** : tout ce que l'agent a vu et pourquoi il l'a écarté (et tu peux repêcher une offre).
- **Mes modèles** et **Journal**.

## Faire tourner Joby 24h/24

Sur ton PC, `joby agent` tourne tant que l'ordinateur est allumé. Pour une recherche qui ne
dort jamais, installe-le sur un petit serveur (quelques euros par mois) : tout est expliqué
pas à pas dans **[deploy/DEPLOY.md](deploy/DEPLOY.md)**.

## Réglages

Tout est dans `user/config.yml` (créé au premier lancement). Les plus utiles :

```yaml
pipeline:
  cycle_hours: 3              # un cycle toutes les 3 h
  min_score: 4.0              # note minimale (sur 5) pour préparer un dossier
  max_dossiers_per_cycle: 3   # qualité > quantité, et ça ménage ton quota Claude
  max_offer_age_days: 30
letter:
  language: auto              # langue de l'offre ; ou "fr", "en"…
models:                       # quel modèle Claude pour quelle tâche
  onboarding: opus
  prescreen: haiku
  analysis: sonnet
  writing: opus
  apply: sonnet
```

**Ton quota Claude.** Joby utilise ton abonnement : le tri passe par des modèles légers, la
rédaction par Opus. Si la limite d'usage est atteinte, l'agent se met en pause et reprend
tout seul. Avec un abonnement Pro, garde des réglages modestes ; avec Max, tu peux augmenter
`max_dossiers_per_cycle`.

## Confidentialité et sécurité

- **Tes données restent chez toi.** Tout ce qui te concerne vit dans `user/`, ignoré par git.
  Rien n'est envoyé ailleurs qu'à Claude (via ton abonnement) et aux sites où tu postules.
- **Aucun mot de passe de site carrière** n'est demandé ni stocké par Joby : tu te connectes
  toi-même dans le navigateur de l'agent, qui réutilise ta session.
- **Boîte mail en lecture seule** : le serveur MCP intégré ouvre ta boîte en mode `readonly`
  (ni envoi, ni suppression, ni marquage comme lu). Le mot de passe d'application est stocké
  dans `user/.env` (permissions 600) et n'est jamais montré à Claude.
- **Chaque étape de l'agent n'a que les outils dont elle a besoin** : aucun pour l'analyse et la
  rédaction, le navigateur pour postuler, la boîte mail pour le suivi. Jamais de mode
  « toutes permissions ». Le contenu des pages et des mails est traité comme de la donnée,
  jamais comme des instructions.
- **Rien ne part sans ta validation.** L'agent n'envoie que les dossiers que tu as validés, et
  s'arrête avant l'envoi au moindre doute (question inconnue, captcha, session expirée).

## Structure du projet

```
joby/
├── install.sh            installation (macOS / Linux)
├── joby                  la commande
├── src/joby/
│   ├── onboarding.py     les 9 étapes
│   ├── prompts/          les instructions données à Claude (onboarding et pipeline)
│   ├── pipeline/         scan, triage, dossier, apply, mail, runner
│   ├── templates/latex/  modèles de CV et de lettre par défaut
│   ├── mail_mcp.py       serveur MCP mail (IMAP, lecture seule)
│   └── careerops.py      intégration CareerOps
├── dashboard/app.py      le dashboard Streamlit
├── deploy/               tout pour le serveur
├── vendor/career-ops/    CareerOps (sous-module git)
└── user/                 TES données (jamais versionnées)
```

## FAQ

**Est-ce que Joby postule tout seul, sans moi ?**
Non, et c'est voulu. Il fait tout le travail (recherche, tri, rédaction, remplissage du
formulaire), mais chaque candidature attend ton clic « Valider ». Ça prend dix secondes et
ça t'évite qu'un dossier parte chez l'entreprise de tes rêves sans que tu l'aies relu.

**Et si un site demande une info que Joby n'a pas ?**
Il s'arrête avant d'envoyer et te pose la question dans le dashboard. Ta réponse peut être
mémorisée pour les fois suivantes.

**Mon site carrière n'est pas reconnu, ça marche quand même ?**
Oui. Les sites basés sur un ATS connu (Lever, Greenhouse, Workday, Ashby, SmartRecruiters,
Welcome to the Jungle, Teamtailor… plus de 100) sont lus directement via leur API, sans
consommer de quota. Pour les autres, l'agent navigue sur la page comme le ferait un humain,
un peu moins souvent.

**Combien ça coûte ?**
Joby est gratuit et open source. Il te faut un abonnement Claude, et éventuellement un
serveur (quelques euros par mois) pour qu'il tourne 24h/24.

**Est-ce légal ?**
Joby agit en ton nom, sur les sites que tu as choisis, avec tes propres comptes, et seulement
après ta validation. Certaines plateformes interdisent l'automatisation dans leurs
conditions d'utilisation : c'est à toi de vérifier celles des sites que tu ajoutes. Tu restes
responsable des candidatures envoyées : relis toujours tes dossiers.

## Crédits

- [**CareerOps**](https://github.com/career-ops-hq/career-ops) de Santiago Fernández de
  Valderrama et ses contributeurs (licence MIT) : le socle de Joby. Joby n'est ni affilié
  à CareerOps ni soutenu par le projet.
- [Claude Code](https://claude.com/claude-code), [Playwright MCP](https://github.com/microsoft/playwright-mcp),
  [Tectonic](https://tectonic-typesetting.github.io), [Streamlit](https://streamlit.io), [Rich](https://github.com/Textualize/rich).

## Licence

MIT. Voir [LICENSE](LICENSE).
