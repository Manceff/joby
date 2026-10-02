# Étape 7 — La lettre de motivation

## Objectif
Définir la forme exacte de ses lettres (en LaTeX, très propre) et la façon de les
écrire. Chaque lettre sera ensuite réellement écrite pour l'entreprise et le poste :
c'est ici qu'on fixe le cadre.

## Point de départ
- `{USER}/templates/letter.tex` : modèle actuel (au départ, la lettre corporate de Joby).
  Compilation : `cd {USER}/templates && tectonic --chatter minimal letter.tex`.
- `{USER}/profile/identity.yml`, `{USER}/profile/cv.md`, `{USER}/profile/search.md`.

## Déroulé
1. Demande : « Ta lettre de motivation, tu la veux comment ? Envoie-moi une lettre dont
   tu aimes la mise en forme (glisse-la dans le terminal), je te fais la même chose. »
   Copie les exemples dans `{USER}/profile/examples/`.
2. S'il n'a pas de modèle, propose la **structure classique** : ses coordonnées,
   celles de l'entreprise, lieu et date, objet, corps de la lettre, signature.
3. La **signature** : « Envoie-moi ta signature » (une image : photo ou scan, idéalement
   sur fond blanc). Copie-la en `{USER}/profile/signature.png` (convertis si besoin avec
   `sips -s format png` sur macOS ou `convert` sur Linux). Elle sera ajoutée
   automatiquement en bas des lettres. Sans signature, le nom suffit.
4. Le **fond** (ce qui guidera la rédaction de chaque lettre) :
   - longueur (en général 3-4 paragraphes, une page maximum) ;
   - ton : sobre, chaleureux, direct, enthousiaste... ;
   - langue : par défaut la lettre est écrite **dans la langue de l'offre** ; demande
     s'il préfère autre chose (le CV, lui, est toujours en anglais) ;
   - formules d'appel et de politesse préférées, en français et en anglais ;
   - ce qu'il faut toujours mettre en avant, ce qu'il ne faut jamais dire ;
   - s'il a des lettres qu'il a écrites lui-même et qu'il aime, demande-les : elles
     serviront de référence pour sa voix (copie-les dans `{USER}/profile/examples/`).
5. Mets à jour `{USER}/templates/letter.tex` (style dans le préambule, contenu d'exemple
   réaliste avec ses vraies coordonnées dans le corps), compile, copie le PDF en
   `{USER}/templates/preview/letter.pdf`, ouvre-le, vérifie le rendu toi-même.
6. Ajuste jusqu'à ce qu'il soit pleinement satisfait.

## Ce que tu enregistres (après validation)

- `{USER}/templates/letter.tex` et `{USER}/templates/preview/letter.pdf`.
- `{USER}/profile/signature.png` (si fournie).
- `{USER}/profile/letter-preferences.md` : les règles d'écriture, très concrètes :
  ```markdown
  # Cover letter rules
  - Language: same as the job posting (French posting -> French letter)
  - Length: 3 to 4 paragraphs, never more than one page
  - Tone: ...
  - Opening (FR): "Madame, Monsieur," / (EN): "Dear Hiring Team,"
  - Closing (FR): "..." / (EN): "..."
  - Always: ...
  - Never: ...
  - Voice references: profile/examples/<fichier>
  ```
