# 🐍 Web Scraper Automatique (Python)

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
- **Stockage historique :** SQLite
- **Interface graphique :** Python GUI

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
- [x] Configuration API / HTML par source
- [x] France Travail
- [x] Greenhouse
- [x] Lever
- [ ] Pagination spécifique aux sites
- [ ] Détection des nouvelles offres
- [ ] Suivi des candidatures
- [ ] Relances

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
- [ ] Export JSON
- [ ] Export XLSX
- [ ] Notifications email
- [ ] Planification des exécutions
- [ ] Arrêt d'une exécution en cours

### 🖥️ Interface graphique

- [x] Structure de l'interface graphique
- [x] Vue principale
- [x] Vue Books
- [x] Vue Jobs
- [x] Composants graphiques communs
- [x] Gestion des styles
- [x] Fenêtre principale
- [ ] Gestion complète des sources
- [ ] Configuration complète du scraping
- [ ] Filtres graphiques
- [ ] Options avancées
- [ ] Planification
- [ ] Notifications
- [ ] Progression de l'exécution
- [ ] Arrêt d'une exécution
- [ ] Résultats avancés
- [ ] Historique graphique

### 🔐 Sécurité

- [x] Validation des URLs
- [x] Protection contre les accès réseau locaux
- [x] Protection contre les redirections dangereuses
- [x] Protection contre les résolutions DNS vers des IP privées
- [x] Limitation de la taille des réponses
- [ ] Gestion sécurisée des téléchargements
- [ ] Protection contre les fichiers malveillants
- [ ] Protection contre le path traversal
- [ ] Gestion sécurisée des secrets
- [ ] Exécution avec des privilèges minimum
- [ ] Isolation du scraper sur le NAS
- [ ] Préparation d'une exécution Docker sécurisée

### 🧪 Qualité

- [x] Tests unitaires
- [x] Tests des composants principaux
- [x] Tests anti-régression
- [x] Tests de sécurité
- [x] **223 tests automatisés**
- [ ] Augmenter progressivement la couverture
- [ ] Tests d'intégration

---

## 📁 Structure

```text
scraper-data-python/
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
│   ├── service.py                             # Service de scraping HTML des offres
│   ├── storage.py                             # Gère la sauvegarde des offres
│   ├── application.py                         # Orchestre le traitement des offres
│   ├── reader.py                              # Lit les offres depuis un fichier CSV
│   ├── filter.py                              # Applique les filtres aux offres
│   │
│   └── sources/                               # Gestion des différentes sources d'emploi
│       ├── __init__.py                         # Initialise le package des sources
│       ├── config.py                           # Configuration commune des sources
│       ├── aggregator.py                       # Agrège les résultats des sources
│       │
│       ├── france_travail/                     # Intégration France Travail
│       │   ├── __init__.py                     # Initialise le package France Travail
│       │   ├── authentication.py               # Gère l'authentification OAuth2
│       │   ├── client.py                       # Communique avec l'API France Travail
│       │   ├── config.py                       # Configuration France Travail
│       │   ├── parser.py                       # Transforme les réponses France Travail
│       │   └── service.py                       # Orchestre le scraping France Travail
│       │
│       ├── greenhouse/                         # Intégration Greenhouse
│       │   ├── __init__.py                     # Initialise le package Greenhouse
│       │   ├── client.py                       # Communique avec l'API Greenhouse
│       │   ├── parser.py                       # Transforme les réponses Greenhouse
│       │   └── service.py                      # Orchestre le scraping Greenhouse
│       │
│       └── lever/                              # Intégration Lever
│           ├── __init__.py                     # Initialise le package Lever
│           ├── client.py                       # Communique avec l'API Lever
│           ├── parser.py                       # Transforme les réponses Lever
│           └── service.py                      # Orchestre le scraping Lever
│
├── scraper/                                    # Composants techniques communs au scraping
│   ├── __init__.py                             # Initialise le package Scraper
│   ├── config.py                               # Configuration commune des scrapers
│   ├── http_client.py                          # Effectue les requêtes HTTP
│   ├── collection.py                           # Gère les collections et la déduplication
│   ├── pagination.py                           # Gère la pagination commune
│   ├── result.py                               # Représente le résultat d'une exécution
│   ├── history.py                              # Représente une entrée d'historique
│   └── history_service.py                      # Construit et enregistre l'historique
│
├── gui/                                        # Interface graphique de l'application
│   ├── __init__.py                             # Initialise le package GUI
│   ├── books_view.py                           # Vue graphique consacrée aux livres
│   ├── components.py                           # Composants graphiques réutilisables
│   ├── home_view.py                            # Vue principale de l'application
│   ├── jobs_view.py                            # Vue graphique consacrée aux offres
│   ├── styles.py                               # Styles et apparence graphique
│   └── window.py                               # Gestion de la fenêtre principale
│
├── utils/                                      # Utilitaires techniques communs
│   ├── __init__.py                             # Initialise le package Utils
│   ├── helpers.py                              # Fonctions utilitaires génériques
│   ├── logger.py                               # Configure et centralise les logs
│   ├── url.py                                  # Validation et manipulation des URLs
│   └── security.py                             # Contrôles de sécurité du scraper
│
├── cli/                                        # Gestion de l'interface en ligne de commande
│   ├── __init__.py                             # Initialise le package CLI
│   └── arguments.py                            # Analyse et valide les arguments CLI
│
├── data/                                       # Composants génériques de gestion des données
│   ├── __init__.py                             # Initialise le package Data
│   ├── csv_reader.py                           # Lecture générique des fichiers CSV
│   └── csv_writer.py                           # Écriture générique des fichiers CSV
│
├── storage/                                    # Persistance technique des données communes
│   ├── __init__.py                             # Initialise le package Storage
│   ├── database.py                             # Gère la base SQLite
│   └── history_repository.py                   # Persiste et récupère l'historique
│
├── scripts/                                    # Scripts destinés aux essais manuels
│   ├── __init__.py                             # Initialise le package Scripts
│   └── test_books_scraping.py                  # Lance un scraping réel des livres
│
├── tests/                                      # Ensemble des tests automatisés
│   ├── __init__.py                             # Initialise le package de tests
│   │
│   ├── book/                                   # Tests du domaine Book
│   │   ├── __init__.py                         # Initialise le package de tests Book
│   │   ├── test_config.py                      # Teste la configuration des livres
│   │   ├── test_parser.py                      # Teste le parsing des livres
│   │   ├── test_service.py                     # Teste le service de scraping
│   │   ├── test_storage.py                     # Teste la sauvegarde des livres
│   │   ├── test_application.py                 # Teste l'orchestration Book
│   │   ├── test_filter.py                      # Teste les filtres des livres
│   │   └── test_display.py                     # Teste l'affichage des livres
│   │
│   ├── job/                                    # Tests du domaine Job
│   │   ├── __init__.py                         # Initialise le package de tests Job
│   │   ├── test_config.py                      # Teste la configuration des offres
│   │   ├── test_parser.py                      # Teste le parsing des offres
│   │   ├── test_service.py                     # Teste le service de scraping
│   │   ├── test_storage.py                     # Teste la sauvegarde des offres
│   │   ├── test_application.py                 # Teste l'orchestration Job
│   │   ├── test_filter.py                      # Teste les filtres des offres
│   │   │
│   │   └── sources/                            # Tests des sources d'emploi
│   │       ├── __init__.py                     # Initialise les tests des sources
│   │       ├── test_aggregator.py              # Teste l'agrégation des sources
│   │       ├── test_config.py                  # Teste la configuration commune
│   │       │
│   │       ├── france_travail/                 # Tests France Travail
│   │       │   ├── __init__.py                 # Initialise les tests France Travail
│   │       │   ├── test_authentication.py     # Teste l'authentification
│   │       │   ├── test_client.py             # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── greenhouse/                     # Tests Greenhouse
│   │       │   ├── __init__.py                 # Initialise les tests Greenhouse
│   │       │   ├── test_client.py               # Teste le client API
│   │       │   ├── test_parser.py               # Teste le parsing
│   │       │   └── test_service.py              # Teste le service
│   │       │
│   │       └── lever/                          # Tests Lever
│   │           ├── __init__.py                 # Initialise les tests Lever
│   │           ├── test_client.py               # Teste le client API
│   │           ├── test_parser.py               # Teste le parsing
│   │           └── test_service.py              # Teste le service
│   │
│   ├── cli/                                    # Tests de l'interface CLI
│   │   ├── __init__.py                         # Initialise le package de tests CLI
│   │   └── test_arguments.py                   # Teste les arguments CLI
│   │
│   ├── data/                                   # Tests des composants génériques de données
│   │   ├── __init__.py                         # Initialise le package de tests Data
│   │   ├── test_csv_reader.py                  # Teste la lecture CSV
│   │   └── test_csv_writer.py                  # Teste l'écriture CSV
│   │
│   ├── scraper/                                # Tests des composants communs
│   │   ├── __init__.py                         # Initialise le package de tests Scraper
│   │   ├── test_collection.py                  # Teste les collections
│   │   └── test_config.py                      # Teste la configuration commune
│   │
│   ├── storage/                                # Tests de la persistance commune
│   │   ├── __init__.py                         # Initialise le package de tests Storage
│   │   ├── test_database.py                    # Teste la base SQLite
│   │   └── test_history_repository.py          # Teste la persistance de l'historique
│   │
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
├── README.md                                   # Documentation synthétique du projet
├── .gitignore                                  # Liste des fichiers ignorés par Git
└── LICENSE                                     # Licence du projet