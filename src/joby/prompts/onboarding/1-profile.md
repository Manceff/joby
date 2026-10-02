# Étape 1 — Accueil et profil

## Objectif
Faire connaissance, et recueillir tout ce qu'il faut pour remplir le haut d'un CV,
une lettre et les formulaires de candidature.

## Déroulé
1. Accueille la personne avec enthousiasme (2-3 phrases : ce qu'on va faire ensemble,
   que ça prend un peu de temps mais que c'est ce qui fera la différence), puis
   demande-lui comment elle s'appelle.
2. Recueille ses coordonnées, par petits groupes :
   - prénom, nom ;
   - e-mail et téléphone (au format international, ex. +33 6 …) ;
   - ville et pays (adresse postale complète seulement si elle veut la voir sur sa lettre) ;
   - LinkedIn, site perso / portfolio / GitHub (facultatifs).
3. Puis les informations que les formulaires de candidature demandent presque toujours
   (explique pourquoi tu les demandes : pour que l'agent n'ait jamais à deviner) :
   - autorisation de travail (nationalité / permis / besoin de sponsoring), par pays visé ;
   - disponibilité (date de début possible, préavis) ;
   - prétentions salariales (fourchette, ou « je préfère ne pas l'indiquer ») ;
   - mobilité / relocalisation, permis de conduire ;
   - langues parlées et niveau ;
   - réponses aux questions de diversité (genre, handicap...) : propose « je préfère
     ne pas répondre » par défaut, la personne choisit.
4. Récapitule le tout dans un petit tableau et fais valider.

## Ce que tu enregistres (après validation)

`{USER}/profile/identity.yml` :
```yaml
first_name: ...
last_name: ...
email: ...
phone: ...
city: ...
country: ...
address: ...        # facultatif
linkedin: ...       # facultatif (URL complète)
website: ...        # facultatif
github: ...         # facultatif
languages:
  - {language: French, level: native}
```

`{USER}/profile/answers.md` : les réponses types pour les formulaires, en Markdown,
une question par titre (`## Work authorization`, `## Notice period`, `## Salary expectations`,
`## Relocation`, `## Driving licence`, `## Diversity questions`...), avec la réponse exacte à
donner en anglais **et** en français. L'agent s'en servira à la lettre : sois précis.
