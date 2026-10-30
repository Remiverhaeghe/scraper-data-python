# MySQL et MariaDB

## L'essentiel
- SGBD relationnels libres très répandus pour le web ; MariaDB est un dérivé compatible de MySQL.
- Moteur de stockage InnoDB par défaut : transactions, clés étrangères, verrouillage par ligne.
- Client en ligne de commande mysql, outils graphiques (MySQL Workbench, DBeaver, phpMyAdmin).

## Spécificités de syntaxe
- LIMIT 10 OFFSET 20 pour paginer.
- AUTO_INCREMENT pour les identifiants.
- Guillemets obliques `nom` pour les identifiants réservés.
- IFNULL(a, b), GROUP_CONCAT, ON DUPLICATE KEY UPDATE pour l'insertion ou la mise à jour.
- Encodage : utf8mb4 (le « utf8 » historique ne gère pas tous les caractères, comme les emojis).

## Index et performances
- Index B-tree sur les colonnes filtrées, triées et jointes ; index composés dans le bon ordre.
- EXPLAIN pour lire le plan ; journal des requêtes lentes (slow query log).
- Éviter SELECT * et les fonctions sur colonnes indexées.

## Transactions et verrous
- Niveau d'isolation par défaut : REPEATABLE READ.
- Interblocages (deadlocks) : garder des transactions courtes, toujours dans le même ordre.

## Administration
- Utilisateurs et droits : CREATE USER, GRANT avec le minimum nécessaire.
- Sauvegardes : mysqldump (logique), sauvegardes physiques, journaux binaires pour la restauration à un instant.
- Réplication source et répliques pour la lecture et la haute disponibilité.

## Pièges fréquents
- Mélanger les encodages et obtenir des caractères illisibles.
- Comparaisons insensibles à la casse selon la collation, parfois inattendues.
- Donner tous les droits à l'utilisateur de l'application.
- Ne jamais tester la restauration des sauvegardes.

## En entretien
- Expliquez le rôle d'InnoDB et d'un index.
- Décrivez une optimisation de requête lente que vous avez faite.

## Références
- [Documentation MySQL](https://dev.mysql.com/doc/refman/8.0/en/)
- [Documentation MariaDB](https://mariadb.com/kb/en/documentation/)
- [MySQL (Wikipédia)](https://fr.wikipedia.org/wiki/MySQL)
