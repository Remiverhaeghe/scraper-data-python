# 🐍 Web Scraper Automatique (Python)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis un site web, de les analyser, de les structurer et de les rendre exploitables.

## 🎯 Objectifs

* Comprendre le fonctionnement d'un scraper Python.
* Séparer les responsabilités : HTTP, parsing, modèle et logique métier.
* Gérer la pagination d'un site web.
* Structurer les données extraites.
* Mettre en place des logs.
* Tester progressivement les différents composants.
* Stocker les données extraites dans un format exploitable.

## 🛠️ Stack technique

* **Langage :** Python 3
* **Requêtes HTTP :** `requests`
* **Parsing HTML :** `beautifulsoup4`
* **Tests :** `pytest`
* **Analyse de données :** `pandas`

## 📁 Structure

```text
scraper-data-python/
│
├── book/                       # Domaine des livres
│   ├── __init__.py             # Déclare le package Python
│   ├── model.py                # Définit le modèle de données Book
│   ├── parser.py               # Analyse le HTML et extrait les livres
│   ├── service.py              # Orchestre le scraping des livres
│   └── storage.py              # Enregistre les livres dans un fichier CSV
│
├── job/                        # Domaine des offres d'emploi
│   ├── __init__.py             # Déclare le package Python
│   ├── model.py                # Définit le modèle de données Job
│   ├── parser.py               # Analyse le HTML et extrait les offres
│   └── service.py              # Orchestre le scraping des offres
│
├── scraper/                    # Composants liés au scraping technique
│   ├── __init__.py             # Déclare le package Python
│   └── http_client.py          # Gère les requêtes HTTP et la récupération des pages
│
├── utils/                      # Fonctions et composants réutilisables
│   ├── __init__.py             # Déclare le package Python
│   ├── helpers.py              # Fonctions utilitaires d'extraction et de conversion
│   ├── logger.py               # Configure et fournit le système de logs
│   └── url.py                  # Gère la construction des URLs
│
├── cli/                        # Gestion de la ligne de commande
│   ├── __init__.py             # Déclare le package Python
│   └── arguments.py            # Analyse et valide les arguments CLI
│
├── scripts/                    # Scripts destinés aux tests et essais manuels
│   ├── __init__.py             # Déclare le package Python
│   └── test_books_scraping.py  # Lance un scraping réel de Books to Scrape
│
├── tests/                      # Tests automatisés du projet
│   ├── book/                   # Tests du domaine Book
│   │   ├── __init__.py         # Déclare le package de tests
│   │   ├── test_model.py       # Teste le modèle Book
│   │   ├── test_parser.py      # Teste l'extraction des livres
│   │   ├── test_service.py     # Teste le service de scraping
│   │   └── test_storage.py     # Teste le stockage des livres
│   │
│   ├── job/                    # Tests du domaine Job
│   │   ├── __init__.py         # Déclare le package de tests
│   │   ├── test_model.py       # Teste le modèle Job
│   │   ├── test_parser.py      # Teste l'extraction des offres
│   │   └── test_service.py     # Teste le service de scraping
│   │
│   ├── cli/                    # Tests de la ligne de commande
│   │   ├── __init__.py         # Déclare le package de tests
│   │   └── test_arguments.py   # Teste les arguments CLI
│   │
│   ├── __init__.py             # Déclare le package de tests
│   ├── test_helpers.py         # Teste les fonctions utilitaires
│   ├── test_http_client.py     # Teste les requêtes HTTP
│   ├── test_logger.py          # Teste la configuration des logs
│   └── test_url.py             # Teste la gestion des URLs
│
├── config.py                   # Centralise la configuration de l'application
├── main.py                     # Point d'entrée principal de l'application
├── requirements.txt            # Liste des dépendances Python
├── README.md                   # Présentation et documentation synthétique du projet
└── .gitignore                  # Définit les fichiers ignorés par Git
```

## 🚀 Installation

Cloner le dépôt :

```bash
git clone https://github.com/Remiverhaeghe/scraper-data-python.git
cd scraper-data-python
```

Créer un environnement virtuel :

```bash
python -m venv venv
```

Sous Windows :

```bash
venv\Scripts\activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

## ▶️ Lancer le scraping

Pour lancer le scraping complet :

```bash
python main.py
```

Pour limiter le nombre de pages :

```bash
python main.py --max-pages 2
```

Le résultat est enregistré dans :

```text
output/books.csv
```

Un script de test manuel permet également de réaliser rapidement un scraping limité :

```bash
python -m scripts.test_books_scraping
```

## 🧪 Tests

Lancer l'ensemble des tests :

```bash
python -m pytest
```

## 📝 Logs

Les logs sont écrits dans :

```text
logs/scraper.log
```

Le dossier `logs/` n'est pas versionné.

## 📌 État actuel

* Scraping HTTP fonctionnel
* Parsing HTML fonctionnel
* Pagination fonctionnelle
* Modèle `Book`
* Gestion des URLs relatives
* Gestion des erreurs HTTP
* Système de logs
* Stockage CSV
* Configuration centralisée
* Arguments en ligne de commande
* Tests automatisés
* **32 tests**
* Scraping de 1 000 livres sur Books to Scrape

Les prochaines évolutions porteront sur l'amélioration de la robustesse et l'exploitation des données.
