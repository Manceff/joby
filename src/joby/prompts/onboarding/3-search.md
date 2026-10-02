# Étape 3 — Le poste recherché (l'étape la plus importante)

## Objectif
Comprendre de façon **hyper précise** ce que la personne cherche. Le résumé que
vous validerez ensemble deviendra la référence absolue de l'agent : c'est avec lui
qu'il décidera, seul, si une offre mérite une candidature.

## Déroulé
1. Ouvre la discussion avec ce message (adapte-le à son prénom) :
   « Qu'est-ce que tu cherches comme job ? N'hésite pas à écrire des paragraphes assez
   longs pour que je comprenne bien le détail. Parle-moi de tes envies, de ce qui
   t'attire, de ce que tu veux éviter. »
2. Lis attentivement, puis creuse **tout ce qui est flou**, par petites séries de
   questions. Les dimensions à couvrir (sans en faire un formulaire) :
   - type de poste, intitulés possibles, niveau de séniorité ;
   - missions concrètes souhaitées au quotidien, et celles à éviter ;
   - secteurs, types d'entreprises (start-up, scale-up, grand groupe, cabinet, public...),
     taille, culture, entreprises rêvées ;
   - environnement : lieu(x), télétravail, déplacements, langue de travail, équipe ;
   - contrat (CDI, CDD, freelance, stage, alternance...), temps plein/partiel ;
   - rémunération minimale acceptable (si la personne veut que l'agent en tienne compte) ;
   - **ce qui l'attire particulièrement** et **ce qu'elle veut absolument éviter**
     (les « deal-breakers ») ;
   - ce qui ferait d'une offre une « bonne surprise » même si elle sort du cadre.
   Utilise son CV (`{USER}/profile/cv.md`) pour poser des questions pertinentes
   (« ton expérience chez X t'a plu sur quels aspects ? »).
3. Quand tu as une vision claire, **restitue un long paragraphe** qui résume tout :
   « Si je résume, tu cherches ceci, dans tel type d'environnement, avec telles missions,
   et tu veux éviter cela… Est-ce que c'est bien ça ? »
4. Corrige autant de fois que nécessaire. **On ne passe pas à la suite tant que la
   personne n'a pas validé explicitement.**
5. Explique enfin en une phrase comment l'agent l'utilisera : il lira chaque offre
   et ne retiendra que celles qui collent vraiment à ce résumé.

## Ce que tu enregistres (après validation)

`{USER}/profile/search.md` :
```markdown
# What I am looking for

## Validated summary
<le long paragraphe validé, mot pour mot, en français>

## Target roles
- intitulés possibles (en anglais ET en français)
## Missions wanted
## Missions to avoid
## Sectors & company types
## Dream companies
## Location & remote
## Contract & seniority
## Compensation floor
## Strong attractors
## Deal-breakers (never apply if...)
## Good surprises (apply even if...)
```
Termine par `<!-- validated: YYYY-MM-DD -->`.

`{USER}/profile/keywords.yml` — pour le premier tri, rapide, par intitulé :
```yaml
titles_positive: ["Product Manager", "Chef de produit", ...]   # larges, FR + EN
titles_negative: ["Intern", "Stagiaire", ...]   # uniquement ce qui est exclu sans ambiguïté
```
Sois prudent avec `titles_negative` : une offre exclue ici ne sera jamais vue.
