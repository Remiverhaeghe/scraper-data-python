# 🐍 Web Scraper Automatique (Python)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis un site web, de les analyser, de les structurer et de les rendre exploitables.

## 🎯 Objectifs

- Comprendre le fonctionnement d'un scraper Python
- Séparer les responsabilités : HTTP, parsing, modèle et logique métier
- Gérer la pagination d'un site web
- Structurer les données extraites
- Mettre en place des logs
- Tester progressivement les différents composants
- Stocker et exploiter les données extraites
- Préparer une architecture réutilisable pour plusieurs domaines

## 🛠️ Stack technique

- **Langage :** Python 3
- **Requêtes HTTP :** requests
- **Parsing HTML :** beautifulsoup4
- **Tests :** pytest
- **Analyse de données :** pandas

## 📋 Suivi du projet

- [x] Séparer les responsabilités HTTP / parsing / modèle / service
- [x] Séparer les domaines Books et Jobs
- [x] Mettre en place une configuration commune
- [x] Mettre en place une gestion centralisée des logs
- [x] Mettre en place une suite de tests
- [x] Mettre en place une lecture CSV générique
- [x] Mettre en place une écriture CSV générique
- [x] Finaliser les composants communs aux scrapers
- [x] Ajouter une gestion centralisée des résultats
- [ ] Ajouter l'historique des exécutions

### 📚 Books

- [x] Récupération des pages
- [x] Parsing HTML
- [x] Extraction des livres
- [x] Pagination
- [x] Modèle `Book`
- [x] Stockage CSV
- [x] Lecture CSV
- [x] Filtrage des résultats
- [x] Configuration du scraping
- [ ] Export JSON
- [ ] Export XLSX
- [ ] Détection des nouveaux éléments

### 💼 Jobs

- [x] Modèle `Job`
- [x] Parsing HTML
- [x] Extraction des offres
- [x] Service de scraping
- [x] Lecture CSV
- [x] Stockage CSV
- [ ] Gestion de plusieurs sources
- [ ] Pagination spécifique aux sites
- [ ] Filtres de recherche
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
- [ ] Déduplication
- [x] Historique des exécutions
- [x] Statistiques d'exécution
- [ ] Export JSON
- [ ] Export XLSX
- [ ] Notifications email
- [ ] Planification des exécutions
- [ ] Arrêt d'une exécution en cours

### 🖥️ Interface graphique

- [ ] Fenêtre principale
- [ ] Gestion des sources
- [ ] Configuration du scraping
- [ ] Filtres
- [ ] Options avancées
- [ ] Planification
- [ ] Notifications
- [ ] Progression de l'exécution
- [ ] Arrêt d'une exécution
- [ ] Résultats
- [ ] Historique

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
- [x] **161 tests automatisés**
- [x] Tests de sécurité
- [ ] Augmenter progressivement la couverture
- [ ] Tests d'intégration

## 📁 Structure

scraper-data-python/
│
├── book/                                      # Domaine métier consacré aux livres
│   ├── __init__.py                            # Initialise le package Book
│   ├── config.py                              # Configuration spécifique aux livres
│   ├── csv_schema.py                          # Définit les colonnes CSV des livres
│   ├── model.py                               # Modèle de données représentant un livre
│   ├── parser.py                              # Parse le HTML et extrait les livres
│   ├── service.py                             # Service réalisant le scraping des livres
│   ├── storage.py                             # Gère la sauvegarde des livres
│   ├── application.py                         # Orchestre le traitement complet des livres
│   ├── reader.py                              # Lit les livres depuis un fichier CSV
│   ├── filter.py                              # Applique les filtres aux livres
│   └── display.py                             # Gère l'affichage des résultats des livres
│
├── job/                                       # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                            # Initialise le package Job
│   ├── config.py                              # Configuration spécifique aux offres
│   ├── csv_schema.py                          # Définit les colonnes CSV des offres
│   ├── model.py                               # Modèle de données représentant une offre
│   ├── parser.py                              # Parse le HTML et extrait les offres
│   ├── service.py                             # Service réalisant le scraping des offres
│   ├── storage.py                             # Gère la sauvegarde des offres
│   ├── application.py                         # Orchestre le traitement complet des offres
│   └── reader.py                              # Lit les offres depuis un fichier CSV
│
├── scraper/                                   # Composants techniques communs au scraping
│   ├── __init__.py                            # Initialise le package Scraper
│   ├── config.py                              # Configuration commune aux scrapers
│   ├── http_client.py                         # Effectue les requêtes HTTP et gère les erreurs
│   ├── collection.py                          # Gère les limites appliquées aux collections
│   ├── pagination.py                          # Gère la pagination commune aux scrapers
│   ├── result.py                              # Représente le résultat d'une exécution
│   ├── history.py                             # Modèle représentant une entrée d'historique
│   └── history_service.py                    # Construit et enregistre l'historique
│
├── utils/                                     # Utilitaires techniques communs
│   ├── __init__.py                            # Initialise le package Utils
│   ├── helpers.py                             # Fonctions utilitaires génériques
│   ├── logger.py                              # Configure et centralise les logs
│   ├── url.py                                 # Validation et manipulation des URLs
│   └── security.py                            # Contrôles de sécurité du scraper
│
├── cli/                                       # Gestion de l'interface en ligne de commande
│   ├── __init__.py                            # Initialise le package CLI
│   └── arguments.py                           # Analyse et valide les arguments CLI
│
├── data/                                      # Composants génériques de gestion des données
│   ├── __init__.py                            # Initialise le package Data
│   ├── csv_reader.py                          # Lecture générique des fichiers CSV
│   └── csv_writer.py                          # Écriture générique des fichiers CSV
│
├── storage/                                   # Persistance technique des données communes
│   ├── __init__.py                            # Initialise le package Storage
│   ├── database.py                            # Gère les connexions à SQLite
│   └── history_repository.py                  # Persiste et récupère l'historique
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
│   │   ├── test_model.py                      # Teste le modèle Book
│   │   ├── test_parser.py                     # Teste le parsing et l'extraction des livres
│   │   ├── test_service.py                    # Teste le service de scraping des livres
│   │   ├── test_storage.py                    # Teste la sauvegarde des livres
│   │   ├── test_application.py                # Teste l'orchestration Book
│   │   ├── test_filter.py                      # Teste les filtres des livres
│   │   └── test_display.py                    # Teste l'affichage des livres
│   │
│   ├── job/                                   # Tests du domaine Job
│   │   ├── __init__.py                        # Initialise le package de tests Job
│   │   ├── test_config.py                     # Teste la configuration des offres
│   │   ├── test_model.py                      # Teste le modèle Job
│   │   ├── test_parser.py                     # Teste le parsing et l'extraction des offres
│   │   ├── test_service.py                    # Teste le service de scraping des offres
│   │   ├── test_storage.py                    # Teste la sauvegarde des offres
│   │   └── test_application.py                # Teste l'orchestration Job
│   │
│   ├── cli/                                   # Tests de l'interface CLI
│   │   ├── __init__.py                        # Initialise le package de tests CLI
│   │   └── test_arguments.py                  # Teste les arguments CLI
│   │
│   ├── data/                                  # Tests des composants génériques de données
│   │   ├── __init__.py                        # Initialise le package de tests Data
│   │   ├── test_csv_reader.py                 # Teste la lecture CSV
│   │   └── test_csv_writer.py                 # Teste l'écriture CSV
│   │
│   ├── storage/                               # Tests de la persistance commune
│   │   ├── __init__.py                        # Initialise le package de tests Storage
│   │   ├── test_database.py                   # Teste la connexion SQLite
│   │   └── test_history_repository.py         # Teste la persistance de l'historique
│   │
│   ├── test_config.py                          # Teste la configuration générale
│   ├── test_helpers.py                         # Teste les fonctions utilitaires
│   ├── test_http_client.py                     # Teste le client HTTP
│   ├── test_logger.py                          # Teste la configuration des logs
│   ├── test_main.py                            # Teste le point d'entrée principal
│   ├── test_security.py                        # Teste les contrôles de sécurité
│   ├── test_url.py                             # Teste la gestion des URLs
│   ├── test_collection.py                      # Teste les limites de collection
│   ├── test_pagination.py                      # Teste la pagination commune
│   ├── test_history.py                         # Teste le modèle d'historique
│   └── test_history_service.py                 # Teste le service d'historique
│
├── main.py                                    # Point d'entrée principal de l'application
├── config.py                                  # Configuration générale de l'application
├── requirements.txt                            # Liste des dépendances Python
├── README.md                                  # Documentation synthétique du projet
├── .gitignore                                 # Liste des fichiers ignorés par Git
└── LICENSE                                    # Licence du projet