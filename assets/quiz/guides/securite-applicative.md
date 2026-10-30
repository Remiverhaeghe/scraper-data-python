# Sécurité applicative (OWASP)

## L'essentiel
- L'OWASP Top 10 recense les risques les plus fréquents des applications web.
- Principe de base : ne jamais faire confiance aux données reçues ; valider à l'entrée, échapper à la sortie.
- La sécurité se pense dès la conception, pas à la fin.

## Risques majeurs
- Contrôle d'accès défaillant : un utilisateur accède aux données d'un autre en changeant un identifiant.
- Injection SQL : utiliser des requêtes paramétrées, jamais de concaténation.
- XSS : échapper le texte affiché, éviter innerHTML, Content Security Policy.
- Défaillances cryptographiques : HTTPS, mots de passe hachés avec bcrypt ou argon2, jamais en clair.
- Mauvaise configuration : messages d'erreur trop bavards, comptes par défaut, en-têtes de sécurité absents.
- Composants vulnérables : dépendances à jour et analysées.
- Authentification faible : limiter les tentatives, MFA, sessions protégées.
- SSRF : le serveur appelle une adresse fournie par l'utilisateur.

## Bonnes pratiques
- Requêtes paramétrées ou ORM, validation des entrées par liste blanche.
- Cookies de session HttpOnly, Secure, SameSite ; protection CSRF pour les formulaires.
- Moindre privilège pour les comptes de base de données et de service.
- Secrets hors du code et du dépôt Git.
- Journaliser les événements de sécurité sans données sensibles.

## Tests
- Revue de code orientée sécurité, analyse statique (SAST), analyse des dépendances.
- Tests dynamiques (OWASP ZAP), tests d'intrusion.

## Pièges fréquents
- Vérifier les droits seulement côté interface, pas côté serveur.
- Afficher la trace complète d'une erreur à l'utilisateur.
- Stocker un mot de passe avec un simple hachage rapide (MD5, SHA-1).

## En entretien
- Expliquez l'injection SQL et la requête paramétrée qui la prévient.
- Décrivez comment vous protégez une API : authentification, autorisation, validation.

## Références
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Aide-mémoire OWASP (Cheat Sheet Series)](https://cheatsheetseries.owasp.org/)
- [Injection SQL (Wikipédia)](https://fr.wikipedia.org/wiki/Injection_SQL)
