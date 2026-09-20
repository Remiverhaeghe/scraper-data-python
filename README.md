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
- [ ] Finaliser les composants communs aux scrapers
- [ ] Ajouter une gestion centralisée des résultats
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
- [ ] Retry des requêtes
- [ ] Délai entre les requêtes
- [ ] Limitation du nombre d'éléments
- [ ] Déduplication
- [ ] Historique des exécutions
- [ ] Statistiques d'exécution
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
- [x] **128 tests automatisés**
- [x] Tests de sécurité
- [ ] Augmenter progressivement la couverture
- [ ] Tests d'intégration

## 📁 Structure

scraper-data-python/
│
├── book/                              # Domaine métier consacré aux livres
│   ├── __init__.py                   # Initialise le package Python Book
│   ├── config.py                     # Configuration spécifique au scraping des livres
│   ├── csv_schema.py                 # Définit les colonnes utilisées pour les livres
│   ├── model.py                      # Définit le modèle de données Book
│   ├── parser.py                     # Analyse le HTML et extrait les informations des livres
│   ├── service.py                    # Contient la logique de scraping et de pagination
│   ├── storage.py                    # Enregistre les livres dans le stockage
│   ├── application.py                # Orchestre le traitement complet des livres
│   ├── reader.py                     # Adapte la lecture CSV au domaine Book
│   ├── filter.py                     # Applique les critères de filtrage aux livres
│   └── display.py                    # Affiche les résultats des livres
│
├── job/                               # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                   # Initialise le package Python Job
│   ├── config.py                     # Configuration spécifique au scraping des offres
│   ├── csv_schema.py                 # Définit les colonnes utilisées pour les offres
│   ├── model.py                      # Définit le modèle de données Job
│   ├── parser.py                     # Analyse le HTML et extrait les informations des offres
│   ├── service.py                    # Contient la logique de scraping des offres
│   ├── storage.py                    # Enregistre les offres dans le stockage
│   ├── application.py                # Orchestre le traitement complet des offres
│   └── reader.py                     # Adapte la lecture CSV au domaine Job
│
├── scraper/                           # Composants techniques communs au scraping
│   ├── __init__.py                   # Initialise le package Python Scraper
│   ├── config.py                     # Configuration commune aux différents scrapers
│   └── http_client.py                # Effectue les requêtes HTTP et gère les redirections
│
├── utils/                             # Fonctions techniques réutilisables
│   ├── __init__.py                   # Initialise le package Python Utils
│   ├── helpers.py                    # Regroupe les fonctions utilitaires communes
│   ├── logger.py                     # Configure et centralise la gestion des logs
│   ├── security.py                   # Centralise les contrôles de sécurité
│   └── url.py                        # Construit et manipule les URLs
│
├── cli/                               # Gestion de l'interface en ligne de commande
│   ├── __init__.py                   # Initialise le package Python CLI
│   └── arguments.py                  # Analyse et valide les arguments de la ligne de commande
│
├── data/                              # Composants génériques de gestion des données
│   ├── __init__.py                   # Initialise le package Python Data
│   ├── csv_reader.py                 # Lit les fichiers CSV et retourne des DataFrames
│   └── csv_writer.py                 # Écrit les données dans des fichiers CSV
│
├── scripts/                           # Scripts destinés aux essais manuels
│   ├── __init__.py                   # Initialise le package Python Scripts
│   └── test_books_scraping.py        # Lance un scraping réel des livres pour les essais
│
├── tests/                             # Tests automatisés du projet
│   ├── __init__.py                   # Initialise le package de tests
│   │
│   ├── book/                          # Tests du domaine Book
│   │   ├── __init__.py               # Initialise le package de tests Book
│   │   ├── test_config.py            # Vérifie la configuration des livres
│   │   ├── test_model.py             # Vérifie le modèle Book
│   │   ├── test_parser.py            # Vérifie le parsing et l'extraction des livres
│   │   ├── test_service.py           # Vérifie le service de scraping des livres
│   │   ├── test_storage.py           # Vérifie le stockage des livres
│   │   ├── test_application.py       # Vérifie l'orchestration du traitement Book
│   │   ├── test_filter.py             # Vérifie le filtrage des livres
│   │   └── test_display.py            # Vérifie l'affichage des résultats
│   │
│   ├── job/                           # Tests du domaine Job
│   │   ├── __init__.py               # Initialise le package de tests Job
│   │   ├── test_config.py            # Vérifie la configuration des offres
│   │   ├── test_model.py             # Vérifie le modèle Job
│   │   ├── test_parser.py            # Vérifie le parsing et l'extraction des offres
│   │   ├── test_service.py           # Vérifie le service de scraping des offres
│   │   ├── test_storage.py           # Vérifie le stockage des offres
│   │   ├── test_application.py       # Vérifie l'orchestration du traitement Job
│   │   └── test_reader.py             # Vérifie la conversion des CSV en objets Job
│   │
│   ├── cli/                           # Tests de l'interface en ligne de commande
│   │   ├── __init__.py               # Initialise le package de tests CLI
│   │   └── test_arguments.py         # Vérifie l'analyse et la validation des arguments
│   │
│   ├── data/                          # Tests des composants génériques de données
│   │   ├── __init__.py               # Initialise le package de tests Data
│   │   ├── test_csv_reader.py        # Vérifie la lecture générique des fichiers CSV
│   │   └── test_csv_writer.py        # Vérifie l'écriture générique des fichiers CSV
│   │
│   ├── test_config.py                 # Vérifie la configuration générale
│   ├── test_helpers.py                # Vérifie les fonctions utilitaires
│   ├── test_http_client.py            # Vérifie les requêtes HTTP et les redirections
│   ├── test_logger.py                 # Vérifie la configuration et le fonctionnement des logs
│   ├── test_main.py                   # Vérifie le point d'entrée de l'application
│   ├── test_security.py               # Vérifie les protections de sécurité
│   └── test_url.py                    # Vérifie la construction et la manipulation des URLs
│
├── config.py                          # Centralise les paramètres généraux de l'application
├── main.py                            # Point d'entrée principal de l'application
├── requirements.txt                   # Liste les dépendances Python du projet
├── README.md                          # Présente le projet, son architecture et son avancement
├── .gitignore                         # Définit les fichiers ignorés par Git
└── LICENSE                            # Définit les conditions d'utilisation du projet