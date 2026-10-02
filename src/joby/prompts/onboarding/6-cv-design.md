# Étape 6 — La mise en forme du CV

## Objectif
Reproduire **exactement** le CV que la personne veut, en LaTeX, avec un rendu
corporate, propre et parfaitement mis en page. Ses goûts priment sur les tiens.

## Point de départ
- `{USER}/templates/cv.tex` : modèle actuel (au départ, le modèle corporate de Joby).
  Il se compile avec **Tectonic** (XeLaTeX) : `cd {USER}/templates && tectonic --chatter minimal cv.tex`.
- `{USER}/profile/cv.md` : son contenu (CV maître, en anglais).
- `{USER}/profile/cv-source/` : son CV d'origine.

## Déroulé
1. Demande-lui s'il a des **CV d'exemple** dont il aime le style (le sien ou d'autres) :
   il peut les glisser dans le terminal. Copie-les dans `{USER}/profile/examples/`
   et regarde-les attentivement (structure, typographie, couleurs, densité, en-tête).
2. Pose tes questions, par petits groupes :
   - **Quel type de CV** ? (une colonne sobre, deux colonnes, très dense, aéré, avec ou
     sans photo, une page ou deux...)
   - **Quelle typographie** ? Propose des choix concrets disponibles : TeX Gyre Heros
     (style Helvetica), TeX Gyre Termes (style Times), TeX Gyre Pagella (style Palatino),
     Latin Modern, Libertinus, ou une police fournie en fichier .otf/.ttf.
   - **Quels intitulés de sections**, dans quel ordre ? (rappel : le CV est en anglais)
   - **Couleur d'accent** (ou noir et blanc).
   - **Veux-tu un en-tête** en haut du CV (nom, titre, coordonnées) ? Avec quoi dedans ?
   - **Faut-il personnaliser l'en-tête selon l'entreprise** visée (ex. le titre sous ton nom
     reprend l'intitulé du poste) ?
   - **Est-ce que je garde l'intégralité de ton CV**, ou est-ce que j'adapte le contenu
     selon l'offre (réordonner, mettre en avant, raccourcir, reformuler certaines puces) ?
     Qu'est-ce qui ne doit **jamais** être retiré ou modifié ?
3. Modifie `{USER}/templates/cv.tex` en conséquence, en y mettant **son vrai contenu**
   (depuis `cv.md`). Règles techniques :
   - garde le moteur XeLaTeX/fontspec, pas de package exotique ; tout le style
     (marges, polices, couleurs, macros) va dans le **préambule** (avant `\begin{document}`),
     le corps ne contient que du contenu qui utilise ces macros ;
   - en commentaire en tête de fichier, décris les macros disponibles et leur usage.
4. Compile, copie le PDF dans `{USER}/templates/preview/cv.pdf` et ouvre-le
   (`open` sur macOS, `xdg-open` sur Linux ; s'il n'y a pas d'écran, dis-lui qu'il le
   verra dans le dashboard, page « Mes modèles »). Vérifie toi-même le rendu en lisant
   le PDF : débordements, alignements, page qui déborde.
5. Demande ce qu'il en pense, ajuste, recompile... **jusqu'à ce qu'il soit pleinement
   satisfait.** Chaque détail compte.

## Ce que tu enregistres (après validation)

- `{USER}/templates/cv.tex` : le modèle final validé (avec son contenu réel).
- `{USER}/templates/preview/cv.pdf` : l'aperçu validé.
- `{USER}/profile/cv-preferences.md` : les règles de personnalisation, très concrètes, que
  l'agent appliquera à chaque candidature. Par exemple :
  ```markdown
  # CV rules
  - Language: English (always)
  - Length: exactly one page
  - Tailoring: reorder bullets and rewrite the summary for each offer; never remove an experience
  - Header: the line under the name becomes the exact job title of the offer
  - Never change: education section, dates, job titles
  - Sections order: Profile, Experience, Education, Skills, Languages
  ```
