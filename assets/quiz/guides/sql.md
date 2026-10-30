# SQL

## L'essentiel
- SQL interroge et modifie les bases relationnelles : tables, lignes, colonnes, clés.
- Clé primaire : identifie une ligne. Clé étrangère : relie à une autre table.
- Ordre d'écriture : SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY ; ordre logique : FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY.

## Requêtes de base
- SELECT colonnes FROM table WHERE condition ORDER BY colonne.
- Filtres : =, <>, BETWEEN, IN, LIKE 'abc%', IS NULL (jamais = NULL).
- Agrégats : COUNT, SUM, AVG, MIN, MAX avec GROUP BY ; HAVING filtre les groupes.
- DISTINCT supprime les doublons.

## Jointures
- INNER JOIN : seulement les lignes qui correspondent des deux côtés.
- LEFT JOIN : toutes les lignes de gauche, NULL à droite si pas de correspondance.
- Trouver les lignes sans correspondance : LEFT JOIN … WHERE droite.id IS NULL.
- Une jointure sans condition multiplie les lignes (produit cartésien).

## Sous-requêtes et avancé
- Sous-requêtes dans WHERE (IN, EXISTS) ou dans FROM.
- CTE avec WITH pour découper une requête complexe.
- Fonctions de fenêtre : ROW_NUMBER, RANK, SUM OVER (PARTITION BY … ORDER BY …).
- UNION (sans doublons) et UNION ALL (avec).

## Modification et transactions
- INSERT, UPDATE, DELETE : toujours vérifier le WHERE avant d'exécuter.
- Transactions : BEGIN, COMMIT, ROLLBACK ; propriétés ACID.
- Contraintes : NOT NULL, UNIQUE, CHECK, clés étrangères.

## Performances
- Index sur les colonnes filtrées et jointes ; trop d'index ralentit les écritures.
- Lire le plan d'exécution (EXPLAIN) avant d'optimiser.
- Éviter les fonctions sur une colonne indexée dans le WHERE.

## Pièges fréquents
- Écrire = NULL au lieu de IS NULL.
- Filtrer la table de droite d'un LEFT JOIN dans le WHERE : il devient un INNER JOIN.
- COUNT(colonne) ignore les NULL, COUNT(*) non.
- UPDATE sans WHERE.

## En entretien
- Expliquez INNER et LEFT JOIN avec un exemple.
- Écrivez une requête avec GROUP BY et HAVING.

## Références
- [SQL (Wikipédia)](https://fr.wikipedia.org/wiki/Structured_Query_Language)
- [Jointure (Wikipédia)](https://fr.wikipedia.org/wiki/Jointure_%28informatique%29)
- [SQLite (documentation SQL)](https://www.sqlite.org/lang.html)
