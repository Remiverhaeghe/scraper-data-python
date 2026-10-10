# 🐍 Web Scraper Automatique (Python)

[![CI](https://github.com/Remiverhaeghe/scraper-data-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Remiverhaeghe/scraper-data-python/actions/workflows/ci.yml)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis des sites web, de les analyser, de les structurer et de les rendre exploitables.

Le projet sert également de support d'apprentissage afin de construire progressivement une architecture Python propre, testable et maintenable.

---

## 🎯 Objectifs

- Comprendre le fonctionnement d'un scraper Python
- Séparer les responsabilités HTTP / parsing / extraction / métier / stockage
- Gérer la pagination
- Structurer les données avec `pandas`
- Mettre en place des logs
- Tester progressivement les composants
- Stocker et exploiter les données extraites
- Préparer une architecture réutilisable pour plusieurs domaines
- Préparer une utilisation sécurisée sur un NAS

---

## 🛠️ Stack technique

- **Langage :** Python 3
- **Requêtes HTTP :** requests
- **Parsing HTML :** beautifulsoup4
- **Analyse et structure des données :** pandas
- **Tests :** pytest
- **Stockage :** SQLite
- **Interface graphique :** PySide6 (Qt)
- **Tableau de bord web :** FastAPI, Jinja2, HTMX

---

## 🚀 Lancement

```bash
pip install -r requirements.txt
cp .env.example .env              # puis renseigner les clés des sources utilisées

python main.py                    # interface graphique
python -m cli.main --help         # ligne de commande
python -m web                     # tableau de bord sur http://127.0.0.1:8000
```

---

## 📋 Suivi du projet

### 🏗️ Architecture

- [x] Séparer les responsabilités HTTP / parsing / service
- [x] Séparer les domaines Books et Jobs
- [x] Mettre en place une configuration commune
- [x] Mettre en place une gestion centralisée des logs
- [x] Mettre en place une suite de tests
- [x] Mettre en place une lecture CSV générique
- [x] Mettre en place une écriture CSV générique
- [x] Finaliser les composants communs aux scrapers
- [x] Ajouter une gestion centralisée des résultats
- [x] Ajouter l'historique des exécutions
- [x] Utiliser des DataFrames pour les données extraites
- [x] Supprimer les anciens modèles `Book` et `Job`
- [x] Ajouter une configuration commune aux sources d'emploi
- [x] Permettre l'activation / désactivation des sources
- [x] Gérer le choix API / HTML selon les capacités d'une source
- [x] Centraliser l'agrégation des sources d'emploi
- [x] Centraliser l'orchestration du traitement des offres
- [x] Dédupliquer les offres lors de l'agrégation multi-sources
- [x] Gérer les limites par source et la limite globale
- [x] Stocker les offres en base SQLite
- [x] Versionner le schéma de la base par migrations (v2 : paramètres de l'historique, v3 : journal des relances, v4 : réglages)
- [x] Déclarer les sources d'emploi dans un registre unique

### 📚 Books

- [x] Récupération des pages
- [x] Parsing HTML
- [x] Extraction des livres
- [x] Pagination
- [x] Stockage CSV
- [x] Lecture CSV
- [x] Filtrage des résultats
- [x] Configuration du scraping
- [ ] Export JSON
- [ ] Export XLSX
- [ ] Détection des nouveaux éléments

### 💼 Jobs

- [x] Parsing HTML
- [x] Extraction des offres
- [x] Service de scraping
- [x] Lecture CSV
- [x] Stockage CSV
- [x] Filtrage des offres
- [x] Configuration des recherches
- [x] Gestion de plusieurs sources
- [x] Normalisation des données entre les sources
- [x] Agrégation des résultats
- [x] Orchestration du traitement multi-sources
- [x] Déduplication des offres entre les sources
- [x] Filtrage des résultats après agrégation
- [x] Enregistrement de l'historique du traitement
- [x] Configuration API / HTML par source
- [x] France Travail — API suspendue par France Travail, accès sur demande
- [x] Adzuna
- [x] Remotive (télétravail)
- [x] Arbeitnow (Europe)
- [x] Jobicy (télétravail ouvert à la France)
- [x] Himalayas (télétravail ouvert à la France)
- [x] Jooble — clé à demander, intégration à valider sur un vrai appel
- [x] Findwork — clé à créer, intégration à valider sur un vrai appel
- [x] Hacker News « Who is hiring? »
- [x] Greenhouse
- [x] Lever
- [ ] Pagination spécifique aux sites
  - [x] France Travail
  - [x] Adzuna
  - [x] Arbeitnow
  - [x] Himalayas
  - [x] Jooble
  - [x] Findwork
  - [ ] Greenhouse — non nécessaire sur l'API Job Board utilisée
  - [x] Lever
  - [ ] Remotive — non nécessaire, l'API renvoie tout en une requête
- [x] Enregistrement de la première récupération
- [x] Enregistrement de la dernière récupération
- [x] Gestion des limites par source
- [x] Limitation globale après déduplication
- [x] Normalisation de la période des salaires
- [x] Estimation du salaire net mensuel, avant et après impôt
- [x] Détection des primes, du 13e mois et de l'épargne salariale
- [x] Normalisation du contrat : CDI, CDD ou freelance
- [x] Poursuite du traitement si une source échoue
- [x] Détection des nouvelles offres
- [x] Suivi des candidatures
- [x] Relances

### ⚙️ Fonctionnalités communes

- [x] Gestion du timeout HTTP
- [x] Gestion des erreurs HTTP
- [x] Logs
- [x] Tests automatisés
- [x] Lecture CSV générique
- [x] Écriture CSV générique
- [x] Retry des requêtes
- [x] Délai entre les requêtes
- [x] Limitation du nombre d'éléments
- [x] Limitation du nombre de pages
- [x] Déduplication
- [x] Historique des exécutions
- [x] Statistiques d'exécution
- [x] Export des offres en CSV, Excel et JSON, avec protection contre l'injection de formules
- [ ] Notifications email
- [ ] Planification des exécutions
- [x] Arrêt d'une exécution en cours (recherche d'offres)

### 🖥️ Interface graphique

- [x] Fenêtre principale avec menu latéral
- [x] Identité visuelle : logo, icônes, bannière, cartes colorées, activité récente et actions rapides
- [x] Accueil : offres, nouveautés, candidatures, relances et dernière exécution
- [x] Recherche : sources, filtres, options avancées, progression et arrêt
- [x] Sources non configurées grisées, derniers critères mémorisés
- [x] Offres : filtres, tableau triable, détail et suivi des candidatures
- [x] Historique des exécutions : synthèse, critères et statut de chaque recherche
- [x] Thèmes clair et sombre, changement sans scintillement ; page Paramètres (sources)
- [x] Règles de calcul modifiables (net, impôt, nouveauté, relance), partagées avec le web, net recalculé
- [x] Graphique d'activité (offres, candidatures, relances) et cartes d'accès direct aux offres filtrées
- [x] Historique : répartition des offres par source et rendement des recherches

### 🌐 Tableau de bord web

- [x] Liste des offres avec mise en évidence des nouvelles
- [x] Filtres : recherche, source, contrat, télétravail, net mensuel, nouveautés
- [x] Mise à jour des résultats sans rechargement (HTMX)
- [x] Fiche détaillée avec lien et mention de la source
- [x] Suivi des candidatures : statut, notes, relances
- [x] Filtre des candidatures à relancer et masquage des offres ignorées
- [x] Même identité que l'application de bureau : menu latéral, logo, icônes, cartes
- [x] Tableau de bord : indicateurs cliquables, graphique d'activité, activité récente
- [x] Historique : camembert des offres par source et rendement des recherches
- [x] Historique des exécutions et page Paramètres (état des sources)
- [x] Thèmes clair et sombre, choix mémorisé dans le navigateur
- [x] Pages d'erreur intégrées au site
- [x] Règles de calcul modifiables, partagées avec l'application de bureau
- [x] Mentions légales, lien vers la licence et contact LinkedIn
- [ ] Authentification

### 🔐 Sécurité

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
- [ ] Exécution avec des privilèges minimum
- [ ] Isolation du scraper sur le NAS
- [ ] Préparation d'une exécution Docker sécurisée

### 🧪 Qualité

- [x] Tests unitaires
- [x] Tests des composants principaux
- [x] Tests anti-régression
- [x] Tests de sécurité
- [x] Intégration continue : tests, couverture, formatage Black et recherche de secrets à chaque push
- [x] Couverture mesurée, branches comprises, avec un seuil minimal relevé progressivement (95 %)
- [x] Tests d'intégration : des API simulées jusqu'à la base, au tableau de bord web et à l'export

---

## 📁 Structure

```text
scraper-data-python/
│
├── .github/                                   # Configuration GitHub
│   └── workflows/                             # Workflows GitHub Actions
│       └── ci.yml                             # Tests, formatage et recherche de secrets
│
├── book/                                      # Domaine métier consacré aux livres
│   ├── __init__.py                            # Initialise le package Book
│   ├── config.py                              # Configuration spécifique aux livres
│   ├── csv_schema.py                          # Définit les colonnes CSV des livres
│   ├── parser.py                              # Parse le HTML et extrait les livres
│   ├── service.py                             # Service réalisant le scraping des livres
│   ├── storage.py                             # Gère la sauvegarde des livres
│   ├── application.py                         # Orchestre le traitement complet des livres
│   ├── reader.py                              # Lit les livres depuis un fichier CSV
│   ├── filter.py                              # Applique les filtres aux livres
│   └── display.py                             # Gère l'affichage des livres
│
├── job/                                       # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                            # Initialise le package Job
│   ├── config.py                              # Configuration spécifique aux offres
│   ├── csv_schema.py                          # Définit les colonnes CSV des offres
│   ├── parser.py                              # Parse le HTML et extrait les offres
│   ├── service.py                             # Service de scraping des offres
│   ├── storage.py                             # Gère la sauvegarde des offres
│   ├── application.py                         # Orchestre le traitement des offres
│   ├── filter.py                              # Applique les filtres aux offres
│   ├── salary.py                              # Estime le salaire net mensuel
│   ├── benefits.py                            # Détecte primes, 13e mois et épargne salariale
│   ├── contract.py                            # Normalise le contrat : CDI, CDD ou freelance
│   ├── presentation.py                        # Mise en forme et filtres communs aux interfaces
│   ├── statistics.py                          # Indicateurs et graphiques, bureau et web
│   ├── settings.py                            # Réglages de calcul modifiables et recalcul du net
│   ├── export.py                              # Export des offres en CSV, Excel et JSON
│   │
│   └── sources/                               # Gestion des différentes sources d'emploi
│       ├── __init__.py                         # Initialise le package des sources
│       ├── config.py                           # Configuration et définition commune des sources
│       ├── configuration.py                    # Construit la configuration des sources
│       ├── registry.py                         # Liste des sources disponibles
│       ├── aggregator.py                       # Agrège les résultats des sources
│       │
│       ├── adzuna/                             # Intégration Adzuna
│       │   ├── __init__.py                     # Initialise le package Adzuna
│       │   ├── client.py                       # Communique avec l'API Adzuna
│       │   ├── config.py                       # Configuration Adzuna
│       │   ├── parser.py                       # Transforme les réponses Adzuna
│       │   ├── service.py                      # Orchestre le scraping Adzuna
│       │   └── source.py                       # Déclare la source Adzuna
│       │
│       ├── arbeitnow/                          # Intégration Arbeitnow
│       │   ├── __init__.py                     # Initialise le package Arbeitnow
│       │   ├── client.py                       # Communique avec l'API Arbeitnow
│       │   ├── parser.py                       # Transforme les réponses Arbeitnow
│       │   ├── service.py                      # Filtre et pagine les offres Arbeitnow
│       │   └── source.py                       # Déclare la source Arbeitnow
│       │
│       ├── findwork/                           # Intégration Findwork
│       │   ├── __init__.py                     # Initialise le package Findwork
│       │   ├── client.py                       # Communique avec l'API Findwork
│       │   ├── config.py                       # Configuration Findwork
│       │   ├── parser.py                       # Transforme les réponses Findwork
│       │   ├── service.py                      # Pagine les offres Findwork
│       │   └── source.py                       # Déclare la source Findwork
│       │
│       ├── france_travail/                     # Intégration France Travail
│       │   ├── __init__.py                     # Initialise le package France Travail
│       │   ├── authentication.py               # Gère l'authentification OAuth2
│       │   ├── client.py                       # Communique avec l'API France Travail
│       │   ├── config.py                       # Configuration France Travail
│       │   ├── parser.py                       # Transforme les réponses France Travail
│       │   ├── service.py                      # Orchestre le scraping France Travail
│       │   └── source.py                       # Déclare la source France Travail
│       │
│       ├── greenhouse/                         # Intégration Greenhouse
│       │   ├── __init__.py                     # Initialise le package Greenhouse
│       │   ├── client.py                       # Communique avec l'API Greenhouse
│       │   ├── config.py                       # Configuration Greenhouse
│       │   ├── parser.py                       # Transforme les réponses Greenhouse
│       │   ├── service.py                      # Orchestre le scraping Greenhouse
│       │   └── source.py                       # Déclare la source Greenhouse
│       │
│       ├── hackernews/                         # Intégration Hacker News
│       │   ├── __init__.py                     # Initialise le package Hacker News
│       │   ├── client.py                       # Communique avec l'API Hacker News
│       │   ├── parser.py                       # Transforme les réponses Hacker News
│       │   ├── service.py                      # Filtre les offres du fil « Who is hiring? »
│       │   └── source.py                       # Déclare la source Hacker News
│       │
│       ├── himalayas/                          # Intégration Himalayas
│       │   ├── __init__.py                     # Initialise le package Himalayas
│       │   ├── client.py                       # Communique avec l'API Himalayas
│       │   ├── parser.py                       # Transforme les réponses Himalayas
│       │   ├── service.py                      # Pagine les offres Himalayas ouvertes à la France
│       │   └── source.py                       # Déclare la source Himalayas
│       │
│       ├── jobicy/                             # Intégration Jobicy
│       │   ├── __init__.py                     # Initialise le package Jobicy
│       │   ├── client.py                       # Communique avec l'API Jobicy
│       │   ├── parser.py                       # Transforme les réponses Jobicy
│       │   ├── service.py                      # Récupère les offres Jobicy ouvertes à la France
│       │   └── source.py                       # Déclare la source Jobicy
│       │
│       ├── jooble/                             # Intégration Jooble
│       │   ├── __init__.py                     # Initialise le package Jooble
│       │   ├── client.py                       # Communique avec l'API Jooble
│       │   ├── config.py                       # Configuration Jooble
│       │   ├── parser.py                       # Transforme les réponses Jooble
│       │   ├── service.py                      # Pagine les offres Jooble
│       │   └── source.py                       # Déclare la source Jooble
│       │
│       ├── lever/                              # Intégration Lever
│       │   ├── __init__.py                     # Initialise le package Lever
│       │   ├── client.py                       # Communique avec l'API Lever
│       │   ├── config.py                       # Configuration Lever
│       │   ├── parser.py                       # Transforme les réponses Lever
│       │   ├── service.py                      # Orchestre le scraping Lever
│       │   └── source.py                       # Déclare la source Lever
│       │
│       └── remotive/                           # Intégration Remotive
│           ├── __init__.py                     # Initialise le package Remotive
│           ├── client.py                       # Communique avec l'API Remotive
│           ├── parser.py                       # Transforme les réponses Remotive
│           ├── service.py                      # Applique le délai de publication Remotive
│           └── source.py                       # Déclare la source Remotive
│
├── scraper/                                   # Composants techniques communs au scraping
│   ├── __init__.py                            # Initialise le package Scraper
│   ├── config.py                              # Configuration commune des scrapers
│   ├── http_client.py                         # Effectue les requêtes HTTP
│   ├── collection.py                          # Gère les collections et la déduplication
│   ├── pagination.py                          # Gère la pagination commune
│   ├── result.py                              # Représente le résultat d'une exécution
│   ├── service.py                             # Mécanique commune de scraping d'un élément
│   ├── history.py                             # Représente une entrée d'historique
│   └── history_service.py                     # Construit et enregistre l'historique
│
├── gui/                                       # Interface graphique de l'application
│   ├── __init__.py                            # Initialise le package GUI
│   ├── app.py                                 # Crée l'application Qt et ouvre la fenêtre
│   ├── branding.py                            # Nom, slogan et logo de l'application
│   ├── main_window.py                         # Fenêtre principale, menu latéral et pages
│   ├── home_page.py                           # Accueil et indicateurs
│   ├── search_page.py                         # Critères, sources, progression et arrêt
│   ├── search_worker.py                       # Exécute la recherche dans un QThread
│   ├── offers_page.py                         # Filtres et tableau des offres en base
│   ├── offers_model.py                        # Modèle Qt du tableau des offres
│   ├── offer_detail.py                        # Détail d'une offre et suivi de candidature
│   ├── history_page.py                        # Historique des exécutions
│   ├── settings_page.py                       # Thème, règles de calcul, sources et licence
│   ├── dialogs.py                             # Fenêtres des mentions légales et de la licence
│   ├── chart.py                               # Histogramme et camembert dessinés avec QPainter
│   ├── widgets.py                             # Composants graphiques partagés
│   ├── theme.py                               # Thèmes clair et sombre, palette et feuille de style
│   ├── theme.qss                              # Feuille de style Qt, couleurs en variables
│   ├── icons.py                               # Charge les icônes SVG dans une couleur donnée
│   └── job_controller.py                      # Lance le traitement des offres depuis la GUI
│
├── web/                                       # Tableau de bord web
│   ├── __init__.py                            # Initialise le package Web
│   ├── __main__.py                            # Lance le serveur avec python -m web
│   ├── app.py                                 # Application FastAPI et routes
│   ├── templates/                             # Gabarits HTML Jinja2
│   │   ├── base.html                          # Mise en page commune et menu latéral
│   │   ├── _macros.html                       # En-tête de page et carte statistique
│   │   ├── dashboard.html                     # Tableau de bord
│   │   ├── offers.html                        # Liste des offres et filtres
│   │   ├── _offers_table.html                 # Tableau rechargé par HTMX
│   │   ├── offer.html                         # Fiche détaillée d'une offre
│   │   ├── _application.html                  # Bloc de suivi d'une candidature
│   │   ├── history.html                       # Historique des exécutions
│   │   ├── settings.html                      # Thème, règles de calcul et état des sources
│   │   ├── legal.html                         # Mentions légales
│   │   ├── license.html                       # Texte de la licence
│   │   └── error.html                         # Page d'erreur
│   └── static/                                # Fichiers statiques
│       ├── style.css                          # Feuille de style, thèmes clair et sombre
│       ├── theme.js                           # Applique et mémorise le thème choisi
│       └── htmx.min.js                        # HTMX 2.0.4, copie locale
│
├── assets/                                    # Ressources partagées par le bureau et le web
│   ├── logo.png                               # Logo, icône de fenêtre et favicon
│   └── icons/                                 # Icônes SVG Lucide (licence ISC)
│
├── utils/                                     # Utilitaires techniques communs
│   ├── __init__.py                            # Initialise le package Utils
│   ├── helpers.py                             # Fonctions utilitaires génériques
│   ├── logger.py                              # Configure et centralise les logs
│   ├── url.py                                 # Validation et manipulation des URLs
│   ├── api_client.py                          # Appels sécurisés aux API des sources
│   └── security.py                            # Contrôles de sécurité du scraper
│
├── cli/                                       # Gestion de l'interface en ligne de commande
│   ├── __init__.py                            # Initialise le package CLI
│   ├── arguments.py                           # Analyse et valide les arguments CLI
│   └── main.py                                # Point d'entrée du mode ligne de commande
│
├── data/                                      # Composants génériques de gestion des données
│   ├── __init__.py                            # Initialise le package Data
│   ├── csv_reader.py                          # Lecture générique des fichiers CSV
│   └── csv_writer.py                          # Écriture générique des fichiers CSV
│
├── storage/                                   # Persistance technique des données communes
│   ├── __init__.py                            # Initialise le package Storage
│   ├── database.py                            # Gère la connexion et les migrations SQLite
│   ├── history_repository.py                  # Persiste et récupère l'historique
│   ├── job_applications.py                    # Suit les candidatures et les relances
│   ├── settings_repository.py                 # Persiste les réglages modifiables
│   └── job_offers.py                          # Enregistre les offres et détecte les nouvelles
│
├── scripts/                                   # Scripts destinés aux essais manuels
│   ├── __init__.py                            # Initialise le package Scripts
│   └── test_books_scraping.py                 # Lance un scraping réel des livres
│
├── tests/                                     # Ensemble des tests automatisés
│   ├── __init__.py                            # Initialise le package de tests
│   │
│   ├── book/                                  # Tests du domaine Book
│   │   ├── __init__.py                        # Initialise le package de tests Book
│   │   ├── test_config.py                     # Teste la configuration des livres
│   │   ├── test_parser.py                     # Teste le parsing des livres
│   │   ├── test_service.py                    # Teste le service de scraping
│   │   ├── test_storage.py                    # Teste la sauvegarde des livres
│   │   ├── test_application.py                # Teste l'orchestration Book
│   │   ├── test_filter.py                     # Teste les filtres des livres
│   │   └── test_display.py                    # Teste l'affichage des livres
│   │
│   ├── job/                                   # Tests du domaine Job
│   │   ├── __init__.py                         # Initialise le package de tests Job
│   │   ├── test_config.py                      # Teste la configuration des offres
│   │   ├── test_parser.py                      # Teste le parsing des offres
│   │   ├── test_service.py                    # Teste le service des offres
│   │   ├── test_storage.py                    # Teste la sauvegarde des offres
│   │   ├── test_application.py                # Teste l'orchestration Job
│   │   ├── test_salary.py                     # Teste l'estimation du salaire net
│   │   ├── test_benefits.py                   # Teste la détection des avantages
│   │   ├── test_contract.py                   # Teste la normalisation du contrat
│   │   ├── test_presentation.py               # Teste la mise en forme commune des offres
│   │   ├── test_statistics.py                 # Teste les indicateurs du tableau de bord
│   │   ├── test_settings.py                   # Teste les réglages et le recalcul du net
│   │   ├── test_export.py                     # Teste l'export et la neutralisation des formules
│   │   ├── test_filter.py                     # Teste les filtres des offres
│   │   │
│   │   └── sources/                           # Tests des sources d'emploi
│   │       ├── __init__.py                     # Initialise les tests des sources
│   │       ├── conftest.py                     # Évite la résolution DNS dans les tests
│   │       ├── fake_http.py                    # Réponses HTTP simulées des API
│   │       ├── test_aggregator.py              # Teste l'agrégation des sources
│   │       ├── test_api_keys.py                # Teste le chargement des clés d'API
│   │       ├── test_config.py                  # Teste la configuration commune
│   │       ├── test_configuration.py           # Teste la construction de la configuration
│   │       │
│   │       ├── adzuna/                         # Tests Adzuna
│   │       │   ├── __init__.py                 # Initialise les tests Adzuna
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   ├── test_service.py             # Teste le service
│   │       │   └── test_source.py              # Teste la déclaration de la source
│   │       │
│   │       ├── arbeitnow/                      # Tests Arbeitnow
│   │       │   ├── __init__.py                 # Initialise les tests Arbeitnow
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le filtrage et la pagination
│   │       │
│   │       ├── findwork/                       # Tests Findwork
│   │       │   ├── __init__.py                 # Initialise les tests Findwork
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination et la configuration
│   │       │
│   │       ├── france_travail/                 # Tests France Travail
│   │       │   ├── __init__.py                 # Initialise les tests France Travail
│   │       │   ├── test_authentication.py      # Teste l'authentification
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── greenhouse/                     # Tests Greenhouse
│   │       │   ├── __init__.py                 # Initialise les tests Greenhouse
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── hackernews/                     # Tests Hacker News
│   │       │   ├── __init__.py                 # Initialise les tests Hacker News
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le filtrage local
│   │       │
│   │       ├── himalayas/                      # Tests Himalayas
│   │       │   ├── __init__.py                 # Initialise les tests Himalayas
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination
│   │       │
│   │       ├── jobicy/                         # Tests Jobicy
│   │       │   ├── __init__.py                 # Initialise les tests Jobicy
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── jooble/                         # Tests Jooble
│   │       │   ├── __init__.py                 # Initialise les tests Jooble
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination et la configuration
│   │       │
│   │       ├── lever/                          # Tests Lever
│   │       │   ├── __init__.py                 # Initialise les tests Lever
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       └── remotive/                       # Tests Remotive
│   │           ├── __init__.py                 # Initialise les tests Remotive
│   │           ├── test_client.py              # Teste le client API
│   │           ├── test_parser.py              # Teste le parsing
│   │           └── test_service.py             # Teste le délai de publication
│   │
│   ├── cli/                                    # Tests de l'interface CLI
│   │   ├── __init__.py                          # Initialise le package de tests CLI
│   │   ├── test_arguments.py                   # Teste les arguments CLI
│   │   └── test_main.py                        # Teste le point d'entrée CLI
│   │
│   ├── gui/                                    # Tests de l'interface graphique
│   │   ├── __init__.py                          # Initialise le package de tests GUI
│   │   ├── conftest.py                         # Crée l'application Qt sans écran
│   │   ├── test_app.py                         # Teste le lancement et le changement de thème
│   │   ├── test_chart.py                       # Teste le rendu des graphiques
│   │   ├── test_history_page.py                # Teste la page de l'historique
│   │   ├── test_home_page.py                   # Teste l'accueil et ses indicateurs
│   │   ├── test_job_controller.py              # Teste le contrôleur des offres
│   │   ├── test_main_window.py                 # Teste la navigation et l'état du menu
│   │   ├── test_offers_model.py                # Teste le modèle du tableau des offres
│   │   ├── test_offers_page.py                 # Teste la page des offres et le suivi
│   │   ├── test_search_page.py                 # Teste la page de recherche
│   │   ├── test_search_worker.py               # Teste le worker de recherche
│   │   ├── test_settings_page.py               # Teste la page des paramètres
│   │   └── test_theme.py                       # Teste les thèmes, les icônes et le logo
│   │
│   ├── data/                                   # Tests des composants génériques de données
│   │   ├── __init__.py                          # Initialise le package de tests Data
│   │   ├── test_csv_reader.py                  # Teste la lecture CSV
│   │   └── test_csv_writer.py                  # Teste l'écriture CSV
│   │
│   ├── scraper/                                # Tests des composants communs
│   │   ├── __init__.py                          # Initialise le package de tests Scraper
│   │   ├── test_collection.py                  # Teste les collections
│   │   ├── test_config.py                      # Teste la configuration commune
│   │   └── test_service.py                     # Teste la mécanique commune de scraping
│   │
│   ├── storage/                                # Tests de la persistance commune
│   │   ├── __init__.py                          # Initialise le package de tests Storage
│   │   ├── test_database.py                    # Teste la base SQLite
│   │   ├── test_history_repository.py          # Teste la persistance de l'historique
│   │   ├── test_job_applications.py            # Teste le suivi des candidatures
│   │   └── test_job_offers.py                  # Teste l'enregistrement des offres
│   │
│   ├── integration/                            # Tests de bout en bout
│   │   ├── __init__.py                          # Initialise le package des tests d'intégration
│   │   └── test_search_to_dashboard.py         # Recherche, base, statistiques, web et export
│   │
│   ├── web/                                    # Tests du tableau de bord
│   │   ├── __init__.py                          # Initialise le package de tests Web
│   │   └── test_app.py                         # Teste les routes et la sécurité de l'affichage
│   │
│   ├── conftest.py                             # Bloque tout accès réseau réel
│   ├── test_api_client.py                      # Teste les appels sécurisés aux API
│   ├── test_config.py                          # Teste la configuration générale
│   ├── test_helpers.py                         # Teste les fonctions utilitaires
│   ├── test_history.py                         # Teste le modèle d'historique
│   ├── test_history_service.py                 # Teste le service d'historique
│   ├── test_http_client.py                     # Teste le client HTTP
│   ├── test_logger.py                          # Teste la configuration des logs
│   ├── test_main.py                            # Teste le point d'entrée principal
│   ├── test_pagination.py                      # Teste la pagination commune
│   ├── test_security.py                        # Teste les contrôles de sécurité
│   └── test_url.py                             # Teste la gestion des URLs
│
├── main.py                                     # Point d'entrée principal de l'application
├── config.py                                   # Configuration générale de l'application
├── requirements.txt                            # Liste des dépendances Python
├── pyproject.toml                              # Configuration et seuil de la couverture
├── README.md                                   # Documentation synthétique du projet
├── .env.example                                # Modèle des variables d'environnement
├── .gitattributes                              # Impose les fins de ligne LF
├── .gitignore                                  # Liste des fichiers ignorés par Git
├── .gitleaksignore                             # Fausses alertes connues de gitleaks
└── LICENSE                                     # Licence du projet
```

## 📄 Licence

Ce projet est publié sous licence [PolyForm Strict 1.0.0](LICENSE) : le code peut être consulté et utilisé tel quel à des fins non commerciales, mais ni modifié, ni redistribué.

Les icônes de `assets/icons/` proviennent de [Lucide](https://lucide.dev) et restent sous leur licence [ISC](assets/icons/LICENSE).
