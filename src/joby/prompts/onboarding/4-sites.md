# Étape 4 — Les sites carrières ciblés

## Objectif
Établir la liste des **seuls** endroits où l'agent cherchera. Pas d'agrégateur
fourre-tout : uniquement là où la personne veut aller.

## Déroulé
1. Demande : « Parfait. Maintenant, donne-moi la liste des sites carrières qui
   t'intéressent : pages carrières d'entreprises, plateformes spécifiques… Colle
   simplement les liens, un par ligne. » Si elle n'a que des noms d'entreprises,
   trouve toi-même la page carrière (WebSearch) et fais-la confirmer.
2. Pour **chaque** lien, vérifie :
   a. qu'il répond et qu'il s'agit bien d'une page avec des offres (WebFetch) ;
   b. que l'agent sait l'exploiter, avec la commande :
      `{JOBY} sites probe "<Nom de l'entreprise>" "<url>"`
      Elle renvoie du JSON :
      - `"kind": "ats"` → lu directement via l'API du site (rapide, gratuit, idéal) ;
        `offers_found` dit combien d'offres sont en ligne ;
      - `"kind": "browser"` → l'agent devra naviguer sur la page comme un humain
        (ça marche, mais c'est plus lent) ; vérifie avec WebFetch que les offres
        sont bien visibles sur la page, sinon cherche une meilleure URL
        (souvent un sous-domaine `jobs.`, `careers.`, ou une page Welcome to the Jungle,
        Lever, Greenhouse, Workday… de l'entreprise) et re-teste.
   c. s'il faut un compte pour postuler (Workday, Taleo, SuccessFactors, iCIMS en
      exigent presque toujours ; Lever, Greenhouse, Ashby, Welcome to the Jungle rarement).
      Dans le doute, regarde une offre du site.
3. Présente le résultat dans un tableau clair : entreprise, lien, ✅/⚠️/❌, nombre
   d'offres en ligne, compte nécessaire ou non. Pour chaque lien problématique,
   explique simplement le souci et demande une correction ou une alternative.
4. Rappelle que les sites demandant un compte seront traités à l'étape suivante :
   la personne s'y connectera elle-même, une fois, dans un navigateur sécurisé.
5. Fais valider la liste finale.

## Ce que tu enregistres (après validation)

`{USER}/profile/sites.yml` :
```yaml
sites:
  - name: Qonto
    url: https://jobs.lever.co/qonto
    kind: ats            # "ats" ou "browser", d'après la commande probe
    needs_account: false
    login_url: ""        # page de connexion si needs_account
    enabled: true
    note: "lu via l'API Lever, ~120 offres"
```
