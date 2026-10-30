# Cloud et infrastructure (AWS, Azure)

## L'essentiel
- Le cloud loue des ressources à la demande : calcul, stockage, réseau, bases de données, services managés.
- Modèles : IaaS (machines virtuelles), PaaS (plateforme gérée), SaaS (logiciel prêt à l'emploi).
- Responsabilité partagée : le fournisseur sécurise l'infrastructure, le client ses données, accès et configurations.

## Services courants
- Calcul : EC2 (AWS), Virtual Machines (Azure) ; fonctions sans serveur : Lambda, Azure Functions.
- Stockage objet : S3, Azure Blob Storage ; disques : EBS, Managed Disks.
- Bases managées : RDS, Azure SQL, DynamoDB, Cosmos DB.
- Réseau : VPC ou VNet, sous-réseaux, groupes de sécurité, équilibreurs de charge.
- Conteneurs : EKS, AKS ; registres d'images.

## Identité et sécurité
- IAM (AWS) ou Entra ID (Azure) : identités, rôles, moindre privilège.
- Authentification à plusieurs facteurs sur les comptes, pas de clés d'accès dans le code.
- Chiffrement au repos et en transit ; journaux d'audit (CloudTrail, Azure Monitor).

## Disponibilité et coûts
- Régions et zones de disponibilité pour la résilience.
- Mise à l'échelle automatique et équilibrage de charge.
- Coûts à l'usage : étiqueter les ressources, budgets et alertes, éteindre ce qui ne sert pas.

## Pièges fréquents
- Un compartiment de stockage laissé public par erreur.
- Des droits administrateur partout pour aller vite.
- Une facture qui explose à cause d'une ressource oubliée.
- Croire que le fournisseur sauvegarde les données à votre place.

## En entretien
- Expliquez IaaS, PaaS et SaaS, et la responsabilité partagée.
- Décrivez une architecture simple : réseau, calcul, base, stockage, sécurité.

## Références
- [Documentation AWS](https://docs.aws.amazon.com/)
- [Documentation Azure (Microsoft Learn)](https://learn.microsoft.com/fr-fr/azure/)
- [Cloud computing (Wikipédia)](https://fr.wikipedia.org/wiki/Cloud_computing)
