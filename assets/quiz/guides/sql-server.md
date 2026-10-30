# SQL Server et T-SQL

## L'essentiel
- SGBD relationnel de Microsoft, langage T-SQL (Transact-SQL).
- Outils : SQL Server Management Studio (SSMS), Azure Data Studio.
- Très présent en entreprise, notamment derrière les ERP, MES et supervisions.

## Spécificités de syntaxe
- SELECT TOP 10 … ; pagination avec OFFSET … ROWS FETCH NEXT … ROWS ONLY.
- IDENTITY pour les identifiants ; crochets [nom] pour les identifiants réservés.
- ISNULL(a, b) (T-SQL) et COALESCE (standard).
- GETDATE() pour la date courante ; types datetime2, nvarchar pour l'Unicode.
- MERGE pour insérer ou mettre à jour.

## Programmation T-SQL
- Variables (DECLARE @x INT), blocs BEGIN … END, IF, WHILE.
- Procédures stockées, fonctions, vues, déclencheurs.
- Gestion d'erreurs avec TRY … CATCH, transactions avec BEGIN TRAN, COMMIT, ROLLBACK.
- Tables temporaires (#temp) et variables table.

## Performances
- Plan d'exécution (estimé ou réel) dans SSMS.
- Index ordonné (clustered, un seul par table) et non ordonnés ; index couvrants (INCLUDE).
- Statistiques à jour ; attention aux conversions implicites qui empêchent l'usage d'un index.

## Administration
- Modes de récupération (simple, complet) et sauvegardes complètes, différentielles, du journal.
- Authentification Windows ou SQL ; rôles et droits minimaux.
- Agent SQL Server pour planifier les tâches.

## Pièges fréquents
- Comparer varchar et nvarchar et provoquer une conversion implicite.
- Oublier que TOP sans ORDER BY renvoie des lignes au hasard.
- Laisser le journal grossir sans sauvegarde en mode de récupération complet.

## En entretien
- Montrez une procédure stockée avec gestion d'erreurs.
- Expliquez la différence entre index ordonné et non ordonné.

## Références
- [Documentation SQL Server (Microsoft Learn)](https://learn.microsoft.com/fr-fr/sql/sql-server/)
- [Référence T-SQL (Microsoft Learn)](https://learn.microsoft.com/fr-fr/sql/t-sql/language-reference)
- [Microsoft SQL Server (Wikipédia)](https://fr.wikipedia.org/wiki/Microsoft_SQL_Server)
