# Étape 2 — Lecture et analyse du CV

## Objectif
Construire la **source de vérité** de son parcours : un CV « maître », complet,
sur lequel l'agent s'appuiera pour chaque candidature. Rien ne pourra être affirmé
dans un CV ou une lettre s'il n'est pas dans ce document.

## Déroulé
1. Demande-lui de déposer son CV : il suffit de **glisser le fichier dans le terminal**
   (son chemin s'affiche) puis d'appuyer sur Entrée. PDF, Word ou image, peu importe.
   Il peut aussi le copier dans `{USER}/profile/cv-source/`.
   Copie le fichier dans `{USER}/profile/cv-source/` (avec `cp`) pour le garder.
2. Lis-le intégralement et extrais : formations, expériences (poste, entreprise,
   lieu, dates, missions, réalisations chiffrées), compétences, outils, langues,
   certifications, projets, engagements, centres d'intérêt.
3. **Analyse** le profil en profondeur et restitue-le de façon claire et bienveillante :
   - le fil rouge du parcours, ce qui le rend cohérent ;
   - ses points forts, les compétences clés qui ressortent ;
   - ce qui pourrait interroger un recruteur (trous, changements de cap...),
     formulé avec tact, comme une piste à préparer, pas comme une critique.
4. Montre-lui ce que tu as extrait, section par section, et demande si tu as bien
   tout compris : rien d'oublié, rien de mal interprété ?
5. **Enrichis** : demande s'il y a des choses absentes du CV qui mériteraient d'y
   être selon l'offre (projets, réalisations chiffrées, responsabilités, outils,
   bénévolat). Ces éléments valent de l'or pour adapter les candidatures.
   Creuse les réalisations : « tu dis avoir amélioré X, tu te souviens de combien ? »
6. Fais valider la version finale.

## Ce que tu enregistres (après validation)

`{USER}/profile/cv.md` — le CV maître, en Markdown, **en anglais** (les CV de
Joby sont toujours rédigés en anglais ; traduis fidèlement si besoin et garde les
noms propres, intitulés de diplômes et noms d'écoles tels quels avec une traduction
entre parenthèses si utile). Structure :

```markdown
# Firstname Lastname
## Headline
## Summary
## Experience
### Job title — Company (City, Country) | Mon YYYY – Mon YYYY
- réalisation, avec chiffres quand ils existent
## Education
## Skills
## Languages
## Certifications / Projects / Volunteering (si présents)
## Additional facts (not on the original CV)
- tout ce que la personne a ajouté à l'étape 5, validé par elle
## Profile analysis
- ton analyse validée (fil rouge, points forts, points à préparer)
```

Termine le fichier par une ligne `<!-- validated: YYYY-MM-DD -->`.
