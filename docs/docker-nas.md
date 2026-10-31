# Exécution sur le NAS (Docker)

Hébergement du tableau de bord web et du planificateur sur un NAS.

Le tableau de bord web et le planificateur tournent dans deux conteneurs isolés ; l'interface de
bureau reste sur le PC. Sur le NAS, dans le dossier du projet :

1. Copier le `.env` (droits `chmod 600 .env`) et le dossier `data/` (`chmod 750 data`). Les
   chemins du `.env` restent relatifs au projet, par exemple `data/tls/…`.
2. Choisir l'adresse publiée : `WEB_PUBLISHED_ADDRESS=100.x.y.z` dans le `.env`, l'adresse
   Tailscale du NAS ; sans elle, le tableau de bord n'est joignable que depuis le NAS.
3. `docker compose up -d` construit l'image et lance le web et le planificateur.

Durcissement : image en deux étapes sans outil de compilation, compte `jobboard` sans droits
d'administration, fichiers de l'image en lecture seule (seuls `data/` et `logs/` s'écrivent),
aucun droit système (`cap_drop: ALL`), pas d'élévation de privilèges, contrôle de santé
(`python -m web.healthcheck`). Au démarrage, un `.env` ou un `data/` trop ouvert, ou un
lancement en administrateur, est signalé dans le journal et dans la page Santé.

Copies chiffrées : `python -m tools.backup_key` donne une clé à mettre dans le `.env`
(`BACKUP_ENCRYPTION_KEY`) ; les copies du NAS sont alors chiffrées, et déchiffrées à la
restauration. Gardez la clé aussi hors du PC et du NAS : sans elle, ces copies sont perdues.
