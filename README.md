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
- [x] Retry des requêtes
- [x] Délai entre les requêtes
- [x] Limitation du nombre d'éléments
- [x] Limitation du nombre de pages
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
- [x] **147 tests automatisés**
- [x] Tests de sécurité
- [ ] Augmenter progressivement la couverture
- [ ] Tests d'intégration

## 📁 Structure

scraper-data-python/
│
├── book/                              # Domaine métier consacré aux livres
│   ├── __init__.py                    # Initialise le package Book
│   ├── config.py                      # Configuration spécifique aux livres
│   ├── csv_schema.py                  # Définit les colonnes CSV des livres
│   ├── model.py                       # Définit le modèle de données Book
│   ├── parser.py                      # Analyse le HTML et extrait les livres
│   ├── service.py                     # Orchestre le scraping des livres
│   ├── storage.py                     # Enregistre les livres
│   ├── application.py                 # Orchestre le traitement complet Book
│   ├── reader.py                      # Lit les CSV et crée les objets Book
│   ├── filter.py                      # Filtre les livres selon les critères
│   └── display.py                     # Prépare l'affichage des livres
│
├── job/                               # Domaine métier consacré aux emplois
│   ├── __init__.py                    # Initialise le package Job
│   ├── config.py                      # Configuration spécifique aux emplois
│   ├── csv_schema.py                  # Définit les colonnes CSV des emplois
│   ├── model.py                       # Définit le modèle de données Job
│   ├── parser.py                      # Analyse le HTML et extrait les offres
│   ├── service.py                     # Orchestre le scraping des offres
│   ├── storage.py                     # Enregistre les offres
│   ├── application.py                 # Orchestre le traitement complet Job
│   └── reader.py                      # Lit les CSV et crée les objets Job
│
├── scraper/                           # Composants techniques communs au scraping
│   ├── __init__.py                    # Initialise le package Scraper
│   ├── config.py                      # Configuration commune des scrapers
│   ├── http_client.py                 # Effectue les requêtes HTTP sécurisées
│   ├── collection.py                  # Gère les limites sur les collections
│   └── pagination.py                  # Gère la pagination commune
│
├── utils/                             # Utilitaires techniques transverses
│   ├── __init__.py                    # Initialise le package Utils
│   ├── helpers.py                     # Fonctions utilitaires communes
│   ├── logger.py                      # Centralise la gestion des logs
│   ├── url.py                         # Construit et manipule les URLs
│   └── security.py                    # Centralise les contrôles de sécurité
│
├── cli/                               # Interface en ligne de commande
│   ├── __init__.py                    # Initialise le package CLI
│   └── arguments.py                   # Analyse et valide les arguments CLI
│
├── data/                              # Gestion générique des données
│   ├── __init__.py                    # Initialise le package Data
│   ├── csv_reader.py                  # Lecture générique des fichiers CSV
│   └── csv_writer.py                  # Écriture générique des fichiers CSV
│
├── scripts/                           # Scripts destinés aux essais manuels
│   ├── __init__.py                    # Initialise le package Scripts
│   └── test_books_scraping.py         # Lance un scraping réel des livres
│
├── tests/                             # Tests automatisés du projet
│   ├── __init__.py                    # Initialise le package de tests
│   │
│   ├── book/                           # Tests du domaine Book
│   │   ├── __init__.py                # Initialise les tests Book
│   │   ├── test_config.py             # Teste la configuration Book
│   │   ├── test_model.py              # Teste le modèle Book
│   │   ├── test_parser.py             # Teste le parsing Book
│   │   ├── test_service.py            # Teste le service Book
│   │   ├── test_storage.py            # Teste le stockage Book
│   │   ├── test_application.py        # Teste l'orchestration Book
│   │   ├── test_filter.py             # Teste les filtres Book
│   │   └── test_display.py            # Teste l'affichage Book
│   │
│   ├── job/                            # Tests du domaine Job
│   │   ├── __init__.py                # Initialise les tests Job
│   │   ├── test_config.py             # Teste la configuration Job
│   │   ├── test_model.py              # Teste le modèle Job
│   │   ├── test_parser.py             # Teste le parsing Job
│   │   ├── test_service.py            # Teste le service Job
│   │   ├── test_storage.py            # Teste le stockage Job
│   │   ├── test_application.py        # Teste l'orchestration Job
│   │   └── test_config.py             # Teste la configuration Job
│   │
│   ├── cli/                            # Tests de l'interface CLI
│   │   ├── __init__.py                # Initialise les tests CLI
│   │   └── test_arguments.py          # Teste les arguments CLI
│   │
│   ├── data/                           # Tests des composants Data
│   │   ├── __init__.py                # Initialise les tests Data
│   │   ├── test_csv_reader.py         # Teste la lecture CSV
│   │   └── test_csv_writer.py         # Teste l'écriture CSV
│   │
│   ├── test_config.py                 # Teste la configuration générale
│   ├── test_helpers.py                # Teste les fonctions utilitaires
│   ├── test_http_client.py            # Teste les requêtes HTTP
│   ├── test_logger.py                 # Teste la gestion des logs
│   ├── test_main.py                   # Teste le point d'entrée
│   ├── test_security.py               # Teste les protections de sécurité
│   ├── test_url.py                    # Teste les fonctions liées aux URLs
│   ├── test_collection.py             # Teste les limites de collections
│   └── test_pagination.py             # Teste la pagination commune
│
├── config.py                           # Configuration générale de l'application
├── main.py                             # Point d'entrée principal
├── requirements.txt                    # Dépendances Python
├── README.md                           # Documentation synthétique du projet
├── .gitignore                          # Fichiers ignorés par Git
└── LICENSE                             # Licence du projet