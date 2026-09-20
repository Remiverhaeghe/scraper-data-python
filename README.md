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
- [ ] Gestion sécurisée des téléchargements
- [x] Limitation de la taille des réponses
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
- [x] 109 tests automatisés
- [ ] Augmenter progressivement la couverture
- [x] Tests de sécurité
- [ ] Tests d'intégration

## 📁 Structure

scraper-data-python/
│
├── book/                                      # Domaine métier consacré aux livres
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   ├── config.py                              # Configuration spécifique au scraping des livres
│   ├── model.py                               # Définit la structure d'un livre
│   ├── parser.py                              # Analyse le HTML et extrait les livres
│   ├── service.py                             # Orchestre le scraping et la pagination
│   └── storage.py                             # Enregistre les livres extraits
│
├── job/                                       # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   ├── model.py                               # Définit la structure d'une offre d'emploi
│   ├── parser.py                              # Analyse le HTML et extrait les offres
│   └── service.py                             # Orchestre le scraping des offres
│
├── scraper/                                   # Composants techniques communs au scraping
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   ├── config.py                              # Configuration commune aux différents scrapers
│   └── http_client.py                         # Effectue les requêtes HTTP et gère les redirections
│
├── utils/                                     # Fonctions techniques réutilisables
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   ├── helpers.py                             # Contient les fonctions utilitaires communes
│   ├── logger.py                              # Configure et centralise les logs
│   ├── security.py                            # Valide les URLs et sécurise les accès réseau
│   └── url.py                                 # Construit et manipule les URLs
│
├── cli/                                      # Gestion de l'interface en ligne de commande
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   └── arguments.py                           # Analyse et valide les arguments CLI
│
├── data/                                     # Exploitation des données après le scraping
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   ├── reader.py                              # Lit et vérifie les données enregistrées
│   ├── filter.py                              # Filtre les données selon les critères demandés
│   └── display.py                             # Affiche les résultats
│
├── scripts/                                  # Scripts destinés aux essais manuels
│   ├── __init__.py                            # Déclare le dossier comme package Python
│   └── test_books_scraping.py                 # Lance un scraping réel pour vérifier le comportement
│
├── tests/                                    # Tests automatisés du projet
│   │
│   ├── book/                                 # Tests du domaine Book
│   │   ├── __init__.py                        # Déclare le dossier comme package de tests
│   │   ├── test_config.py                     # Teste la configuration des livres
│   │   ├── test_model.py                      # Teste le modèle Book
│   │   ├── test_parser.py                     # Teste le parsing et l'extraction
│   │   ├── test_service.py                    # Teste le service de scraping
│   │   └── test_storage.py                    # Teste le stockage des livres
│   │
│   ├── job/                                  # Tests du domaine Job
│   │   ├── __init__.py                        # Déclare le dossier comme package de tests
│   │   ├── test_model.py                      # Teste le modèle Job
│   │   ├── test_parser.py                     # Teste le parsing et l'extraction
│   │   └── test_service.py                    # Teste le service de scraping
│   │
│   ├── cli/                                  # Tests de la ligne de commande
│   │   ├── __init__.py                        # Déclare le dossier comme package de tests
│   │   └── test_arguments.py                  # Teste les arguments CLI
│   │
│   ├── data/                                 # Tests liés aux données
│   │   ├── __init__.py                        # Déclare le dossier comme package de tests
│   │   ├── test_reader.py                     # Teste la lecture des données
│   │   ├── test_filter.py                     # Teste le filtrage
│   │   └── test_display.py                    # Teste l'affichage
│   │
│   ├── __init__.py                            # Déclare le dossier comme package de tests
│   ├── test_config.py                         # Teste la configuration générale
│   ├── test_helpers.py                        # Teste les fonctions utilitaires
│   ├── test_http_client.py                    # Teste les requêtes HTTP et les redirections
│   ├── test_logger.py                         # Teste le système de logs
│   ├── test_main.py                           # Teste le point d'entrée de l'application
│   ├── test_security.py                       # Teste les protections de sécurité réseau
│   └── test_url.py                            # Teste la construction et la manipulation des URLs
│
├── config.py                                  # Centralise les paramètres généraux de l'application
├── main.py                                    # Point d'entrée et orchestration principale
├── requirements.txt                           # Liste les dépendances Python du projet
├── README.md                                  # Présente le projet, son architecture et son avancement
├── .gitignore                                 # Définit les fichiers exclus du versionnement Git
└── LICENSE                                    # Définit les conditions d'utilisation du projet