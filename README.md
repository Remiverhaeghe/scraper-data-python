🐍 Web Scraper Automatique (Python)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis un site web, de les analyser, de les structurer et de les rendre exploitables.

🎯 Objectifs
Comprendre le fonctionnement d'un scraper Python.
Séparer les responsabilités : HTTP, parsing, modèle et logique métier.
Gérer la pagination d'un site web.
Structurer les données extraites.
Mettre en place des logs.
Tester progressivement les différents composants.
Stocker et exploiter les données extraites.
🛠️ Stack technique
Langage : Python 3
Requêtes HTTP : requests
Parsing HTML : beautifulsoup4
Tests : pytest
Analyse de données : pandas
📁 Structure
scraper-data-python/
│
├── book/                       # Domaine métier consacré aux livres
│   ├── __init__.py             # Déclare le dossier comme package Python
│   ├── model.py                # Définit la structure d'un livre
│   ├── parser.py               # Analyse le HTML et extrait les informations des livres
│   ├── service.py              # Orchestre le scraping des livres et la pagination
│   └── storage.py              # Enregistre les livres dans un fichier CSV
│
├── job/                        # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py             # Déclare le dossier comme package Python
│   ├── model.py                # Définit la structure d'une offre d'emploi
│   ├── parser.py               # Analyse le HTML et extrait les informations des offres
│   └── service.py              # Orchestre le scraping des offres d'emploi
│
├── scraper/                    # Composants techniques liés au scraping
│   ├── __init__.py             # Déclare le dossier comme package Python
│   └── http_client.py          # Effectue les requêtes HTTP et récupère les pages HTML
│
├── utils/                      # Fonctions techniques réutilisables dans plusieurs domaines
│   ├── __init__.py             # Déclare le dossier comme package Python
│   ├── helpers.py              # Contient les fonctions d'extraction et de conversion
│   ├── logger.py               # Configure le système de logs de l'application
│   └── url.py                  # Construit et manipule les URLs
│
├── cli/                        # Gestion des interactions avec la ligne de commande
│   ├── __init__.py             # Déclare le dossier comme package Python
│   └── arguments.py            # Analyse et valide les arguments fournis par l'utilisateur
│
├── data/                       # Exploitation des données après le scraping
│   ├── __init__.py             # Déclare le dossier comme package Python
│   ├── reader.py               # Vérifie et lit les données enregistrées dans le fichier CSV
│   ├── filter.py               # Filtre les données selon les critères demandés
│   └── display.py              # Affiche les résultats dans la console
│
├── scripts/                    # Scripts destinés aux essais et vérifications manuelles
│   ├── __init__.py             # Déclare le dossier comme package Python
│   └── test_books_scraping.py  # Lance un scraping réel pour vérifier le comportement du scraper
│
├── tests/                      # Tests automatisés de l'application
│   ├── book/                   # Tests des composants du domaine Book
│   │   ├── __init__.py         # Déclare le dossier comme package de tests
│   │   ├── test_model.py       # Vérifie le modèle Book
│   │   ├── test_parser.py      # Vérifie l'analyse et l'extraction des livres
│   │   ├── test_service.py     # Vérifie le service de scraping des livres
│   │   └── test_storage.py     # Vérifie l'enregistrement des livres
│   │
│   ├── job/                    # Tests des composants du domaine Job
│   │   ├── __init__.py         # Déclare le dossier comme package de tests
│   │   ├── test_model.py       # Vérifie le modèle Job
│   │   ├── test_parser.py      # Vérifie l'analyse et l'extraction des offres
│   │   └── test_service.py     # Vérifie le service de scraping des offres
│   │
│   ├── cli/                    # Tests de la ligne de commande
│   │   ├── __init__.py         # Déclare le dossier comme package de tests
│   │   └── test_arguments.py   # Vérifie l'analyse et la validation des arguments
│   │
│   ├── data/                   # Tests liés à l'exploitation des données
│   │   ├── __init__.py         # Déclare le dossier comme package de tests
│   │   ├── test_reader.py      # Vérifie la lecture et la présence des données
│   │   ├── test_filter.py      # Vérifie le filtrage des données
│   │   └── test_display.py     # Vérifie l'affichage des résultats
│   │
│   ├── __init__.py             # Déclare le dossier comme package de tests
│   ├── test_helpers.py         # Vérifie les fonctions utilitaires
│   ├── test_http_client.py     # Vérifie les requêtes HTTP et la gestion des erreurs
│   ├── test_logger.py          # Vérifie la configuration et l'écriture des logs
│   ├── test_main.py            # Vérifie l'orchestration des différentes étapes
│   └── test_url.py             # Vérifie la construction des URLs
│
├── config.py                   # Centralise les paramètres de configuration
├── main.py                     # Point d'entrée et orchestrateur principal de l'application
├── requirements.txt            # Liste les dépendances nécessaires au projet
├── README.md                   # Présente le projet et explique son fonctionnement
└── .gitignore                  # Définit les fichiers qui ne doivent pas être versionnés
🚀 Installation

Cloner le dépôt :

git clone https://github.com/Remiverhaeghe/scraper-data-python.git
cd scraper-data-python

Créer un environnement virtuel :

python -m venv venv

Sous Windows :

venv\Scripts\activate

Installer les dépendances :

pip install -r requirements.txt
▶️ Lancer le scraping

Pour lancer l'application :

python main.py

Si le fichier output/books.csv n'existe pas, le scraping est lancé automatiquement.

Pour forcer une nouvelle récupération des données :

python main.py --refresh

Pour limiter le nombre de pages :

python main.py --refresh --max-pages 2

Le résultat complet est enregistré dans :

output/books.csv
🔎 Filtrer les résultats

Rechercher un texte dans les titres :

python main.py --title python

Limiter le prix :

python main.py --max-price 20

Définir une note minimale :

python main.py --min-rating 4

Les critères peuvent être combinés :

python main.py --title python --max-price 20 --min-rating 4

Il est également possible de mettre à jour les données avant de les filtrer :

python main.py --refresh --title python --max-price 20 --min-rating 4

Un script de test manuel permet également de réaliser rapidement un scraping limité :

python -m scripts.test_books_scraping
🧪 Tests

Lancer l'ensemble des tests :

python -m pytest

Le projet compte actuellement 67 tests automatisés.

📝 Logs

Les logs sont écrits dans :

logs/scraper.log

Le dossier logs/ n'est pas versionné.

📌 État actuel
Scraping HTTP fonctionnel
Parsing HTML fonctionnel
Pagination fonctionnelle
Modèle Book
Gestion des URLs relatives
Gestion des erreurs HTTP
Système de logs
Stockage CSV
Configuration centralisée
Arguments en ligne de commande
Lecture des données avec pandas
Filtrage des données
Affichage des résultats
Vérification de l'existence du fichier CSV
Actualisation des données avec --refresh
Tests automatisés
67 tests
Scraping de 1 000 livres sur Books to Scrape