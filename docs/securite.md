# Sécurité

Mesures de sécurité en place. Le signalement d'une faille est décrit dans [SECURITY.md](../SECURITY.md), le durcissement des conteneurs dans [docker-nas.md](docker-nas.md).

- [x] Validation des URLs
- [x] Protection contre les accès réseau locaux
- [x] Protection contre les redirections dangereuses
- [x] Protection contre les résolutions DNS vers des IP privées
- [x] Limitation de la taille des réponses
- [x] Gestion sécurisée des téléchargements : client commun des API (redirections refusées, taille plafonnée, type JSON vérifié)
- [x] Protection contre les fichiers malveillants : contenus échappés, injection de formules neutralisée, icônes vérifiées par test
- [x] Protection contre le path traversal : aucun chemin saisi côté serveur, fichiers statiques testés
- [x] Gestion sécurisée des secrets : .env ignoré, gitleaks en CI, clés masquées dans les erreurs et jamais affichées
- [x] Aucun accès réseau réel pendant les tests
- [x] Exécution avec des privilèges minimum : compte dédié, .env et data/ protégés, vérifiés au démarrage et dans la page Santé
- [x] Isolation du scraper sur le NAS : conteneurs du web et du planificateur, fichiers en lecture seule sauf data/ et logs/
- [x] Exécution Docker sécurisée : image en deux étapes sans compte administrateur, aucun droit système (cap_drop), pas d'élévation de privilèges, contrôle de santé
- [x] Copies du NAS chiffrées (clé du .env, `python -m tools.backup_key`), déchiffrées à la restauration
