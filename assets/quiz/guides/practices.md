# Bonnes pratiques et API

## L'essentiel
- Du code lisible, testé et simple coûte moins cher à faire évoluer qu'un code astucieux.
- Une API est un contrat : stable, documentée, cohérente.

## Code propre
- Noms explicites, fonctions courtes qui font une seule chose.
- Éviter la duplication (DRY) sans abstraire trop tôt (YAGNI, KISS).
- Principes SOLID : responsabilité unique, ouvert et fermé, substitution de Liskov, ségrégation des interfaces, inversion des dépendances.
- Gérer les erreurs explicitement et journaliser ce qui aide au diagnostic.

## Tests
- Pyramide : beaucoup de tests unitaires, moins de tests d'intégration, peu de tests de bout en bout.
- Un test : préparer, agir, vérifier (Arrange, Act, Assert).
- Tests rapides, indépendants, reproductibles ; couverture comme indicateur, pas comme objectif.

## API REST
- Ressources nommées au pluriel : /offres, /offres/42.
- Verbes HTTP : GET (lire), POST (créer), PUT ou PATCH (modifier), DELETE (supprimer).
- Codes : 200 OK, 201 créé, 204 sans contenu, 400 requête invalide, 401 non authentifié, 403 interdit, 404 introuvable, 409 conflit, 500 erreur serveur.
- Pagination, filtres, versionnement (/v1), documentation OpenAPI.
- GET, PUT et DELETE idempotents ; POST non.

## Revue de code et Git
- Petites modifications, description claire, revue par un pair.
- Intégration continue : tests et analyse à chaque push.

## Pièges fréquents
- Renvoyer 200 avec un message d'erreur dans le corps.
- Exposer les entités de la base telles quelles dans l'API.
- Écrire des tests qui dépendent les uns des autres ou du réseau.

## En entretien
- Expliquez un principe SOLID avec un exemple tiré de votre code.
- Décrivez une API que vous avez conçue : ressources, codes, erreurs.

## Références
- [Méthodes HTTP (MDN)](https://developer.mozilla.org/fr/docs/Web/HTTP/Methods)
- [Codes de réponse HTTP (MDN)](https://developer.mozilla.org/fr/docs/Web/HTTP/Status)
- [Spécification OpenAPI](https://spec.openapis.org/oas/latest.html)
- [SOLID (Wikipédia)](https://fr.wikipedia.org/wiki/SOLID_%28informatique%29)
