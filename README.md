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

### 🏗️ Architecture

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

- [ ] Validation des URLs
- [ ] Protection contre les accès réseau non autorisés
- [ ] Gestion sécurisée des téléchargements
- [ ] Limitation de la taille des réponses
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
- [ ] Augmenter progressivement la couverture
- [ ] Ajouter des tests de sécurité
- [ ] Ajouter des tests d'intégration

## 📁 Structure

```text
scraper-data-python/
│
├── book/                              # Domaine métier consacré aux livres
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   ├── config.py                      # Définit la configuration spécifique au scraping des livres
│   ├── model.py                       # Définit la structure d'un livre
│   ├── parser.py                      # Analyse le HTML et extrait les informations des livres
│   ├── service.py                     # Orchestre le scraping des livres et la pagination
│   └── storage.py                     # Enregistre les livres dans un fichier CSV
│
├── job/                               # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   ├── model.py                       # Définit la structure d'une offre d'emploi
│   ├── parser.py                      # Analyse le HTML et extrait les informations des offres
│   └── service.py                     # Orchestre le scraping des offres d'emploi
│
├── scraper/                           # Composants techniques communs au scraping
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   ├── config.py                      # Définit la configuration commune aux scrapers
│   └── http_client.py                 # Effectue les requêtes HTTP et récupère les pages HTML
│
├── utils/                             # Fonctions techniques réutilisables
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   ├── helpers.py                     # Contient les fonctions d'extraction et de conversion
│   ├── logger.py                      # Configure le système de logs de l'application
│   └── url.py                          # Construit et manipule les URLs
│
├── cli/                               # Gestion des interactions avec la ligne de commande
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   └── arguments.py                   # Analyse et valide les arguments fournis par l'utilisateur
│
├── data/                              # Exploitation des données après le scraping
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   ├── reader.py                      # Vérifie et lit les données enregistrées dans le fichier CSV
│   ├── filter.py                      # Filtre les données selon les critères demandés
│   └── display.py                     # Affiche les résultats dans la console
│
├── scripts/                            # Scripts destinés aux essais et vérifications manuelles
│   ├── __init__.py                    # Déclare le dossier comme package Python
│   └── test_books_scraping.py         # Lance un scraping réel pour vérifier le comportement du scraper
│
├── tests/                              # Tests automatisés de l'application
│   ├── book/                           # Tests des composants du domaine Book
│   │   ├── __init__.py                 # Déclare le dossier comme package de tests
│   │   ├── test_config.py              # Vérifie la configuration du scraping des livres
│   │   ├── test_model.py               # Vérifie le modèle Book
│   │   ├── test_parser.py              # Vérifie l'analyse et l'extraction des livres
│   │   ├── test_service.py             # Vérifie le service de scraping des livres
│   │   └── test_storage.py             # Vérifie l'enregistrement des livres
│   │
│   ├── job/                            # Tests des composants du domaine Job
│   │   ├── __init__.py                 # Déclare le dossier comme package de tests
│   │   ├── test_model.py               # Vérifie le modèle Job
│   │   ├── test_parser.py              # Vérifie l'analyse et l'extraction des offres
│   │   └── test_service.py             # Vérifie le service de scraping des offres
│   │
│   ├── cli/                            # Tests de la ligne de commande
│   │   ├── __init__.py                 # Déclare le dossier comme package de tests
│   │   └── test_arguments.py            # Vérifie l'analyse et la validation des arguments
│   │
│   ├── data/                           # Tests liés à l'exploitation des données
│   │   ├── __init__.py                 # Déclare le dossier comme package de tests
│   │   ├── test_reader.py              # Vérifie la lecture et la présence des données
│   │   ├── test_filter.py              # Vérifie le filtrage des données
│   │   └── test_display.py             # Vérifie l'affichage des résultats
│   │
│   ├── __init__.py                     # Déclare le dossier comme package de tests
│   ├── test_config.py                  # Vérifie la configuration générale de l'application
│   ├── test_helpers.py                 # Vérifie les fonctions utilitaires
│   ├── test_http_client.py             # Vérifie les requêtes HTTP et la gestion des erreurs
│   ├── test_logger.py                  # Vérifie la configuration et l'écriture des logs
│   ├── test_main.py                    # Vérifie l'orchestration des différentes étapes
│   └── test_url.py                     # Vérifie la construction et la manipulation des URLs
│
├── config.py                           # Centralise les paramètres généraux de l'application
├── main.py                              # Point d'entrée et orchestrateur principal de l'application
├── requirements.txt                     # Liste les dépendances nécessaires au projet
├── README.md                            # Présente le projet et explique son fonctionnement
└── .gitignore                           # Définit les fichiers qui ne doivent pas être versionnés