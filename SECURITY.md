# Politique de sécurité

## Versions suivies

Seule la dernière version de la branche `main` reçoit des correctifs.

## Signaler une vulnérabilité

Merci de ne pas ouvrir d'issue publique pour une faille de sécurité.

Utilisez le signalement privé de GitHub : onglet **Security** du dépôt, puis
**Report a vulnerability**. Indiquez si possible :

- la partie concernée (application de bureau, tableau de bord web, planificateur, source) ;
- les étapes pour reproduire le problème ;
- l'impact estimé.

Un premier retour est donné sous 7 jours. Le correctif est publié dès que possible,
puis la faille est décrite une fois corrigée.

## Mesures en place

- Clés d'API et mots de passe uniquement dans `.env`, jamais versionné ni affiché
- Tableau de bord web protégé par mot de passe, cookie de session signé, jeton CSRF et limitation des tentatives de connexion
- En-têtes HTTP de sécurité : Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Vérification des adresses avant toute requête vers un lien d'offre
- En CI : Bandit (code), pip-audit (dépendances), Gitleaks (secrets), actions épinglées par empreinte
- Mises à jour des dépendances proposées chaque semaine par Dependabot
