# Docker

## L'essentiel
- Docker emballe une application et ses dépendances dans une image, lancée en conteneurs isolés.
- Image : modèle en lecture seule, construite par couches depuis un Dockerfile. Conteneur : instance qui tourne.
- Les données d'un conteneur disparaissent avec lui, sauf dans un volume.

## Dockerfile
- FROM (image de base), WORKDIR, COPY, RUN, ENV, EXPOSE, USER, CMD ou ENTRYPOINT.
- Ordonner les instructions pour profiter du cache : dépendances avant le code.
- Construction en plusieurs étapes (multi-stage) pour une image finale légère.
- Exécuter en utilisateur non root ; ne pas mettre de secret dans l'image.

## Commandes courantes
- docker build -t nom:version .
- docker run -d -p 8080:80 -v donnees:/app/data --name app nom:version
- docker ps, docker logs -f app, docker exec -it app sh, docker stop, docker rm.
- docker images, docker system prune pour faire le ménage.

## Docker Compose
- Décrit plusieurs services (application, base, broker) dans compose.yaml.
- docker compose up -d, docker compose logs, docker compose down.
- Réseaux internes : les services se joignent par leur nom.

## Sécurité et exploitation
- Images officielles et versions précises plutôt que latest.
- Système de fichiers en lecture seule, capacités réduites, ressources limitées.
- Analyse des vulnérabilités des images (Trivy, Docker Scout).
- Bilan de santé (HEALTHCHECK) et redémarrage automatique.

## Pièges fréquents
- Stocker des données dans le conteneur sans volume.
- Exposer un port sur toutes les interfaces sans le vouloir.
- Utiliser latest et voir l'application changer à la reconstruction.
- Un fichier .dockerignore absent qui copie secrets et fichiers lourds.

## En entretien
- Expliquez image et conteneur, volume et port.
- Décrivez un Dockerfile que vous avez écrit et ses choix.

## Références
- [Documentation Docker](https://docs.docker.com/)
- [Bonnes pratiques Dockerfile](https://docs.docker.com/build/building/best-practices/)
- [Docker Compose](https://docs.docker.com/compose/)
