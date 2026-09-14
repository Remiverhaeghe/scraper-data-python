````markdown
# 🐍 Web Scraper Automatique (Python)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis un site web, de les analyser, de les structurer et de les rendre exploitables.

## 🎯 Objectifs

- Comprendre le fonctionnement d'un scraper Python.
- Séparer les responsabilités : HTTP, parsing, modèle et logique métier.
- Gérer la pagination d'un site web.
- Structurer les données extraites.
- Mettre en place des logs.
- Tester progressivement les différents composants.
- Stocker et exploiter les données extraites.

## 🛠️ Stack technique

- **Langage :** Python 3
- **Requêtes HTTP :** `requests`
- **Parsing HTML :** `beautifulsoup4`
- **Tests :** `pytest`
- **Analyse de données :** `pandas`

## 📁 Structure

````markdown
## 📁 Structure

```text
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
│   ├── reader.py               # Lit les données enregistrées dans le fichier CSV
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
│   │   ├── test_reader.py      # Vérifie la lecture des données
│   │   ├── test_filter.py      # Vérifie le filtrage des données
│   │   └── test_display.py     # Vérifie l'affichage des résultats
│   │
│   ├── __init__.py             # Déclare le dossier comme package de tests
│   ├── test_helpers.py         # Vérifie les fonctions utilitaires
│   ├── test_http_client.py     # Vérifie les requêtes HTTP et la gestion des erreurs
│   ├── test_logger.py          # Vérifie la configuration des logs
│   ├── test_main.py            # Vérifie l'orchestration des différentes étapes
│   └── test_url.py             # Vérifie la construction des URLs
│
├── config.py                   # Centralise les paramètres de configuration
├── main.py                     # Point d'entrée et orchestrateur principal de l'application
├── requirements.txt            # Liste les dépendances nécessaires au projet
├── README.md                   # Présente le projet et explique son fonctionnement
└── .gitignore                  # Définit les fichiers qui ne doivent pas être versionnés
````

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

Le résultat complet est enregistré dans :

```text
output/books.csv
```

### 🔎 Filtrer les résultats

Rechercher un texte dans les titres :

```bash
python main.py --title python
```

Limiter le prix :

```bash
python main.py --max-price 20
```

Définir une note minimale :

```bash
python main.py --min-rating 4
```

Les critères peuvent être combinés :

```bash
python main.py --title python --max-price 20 --min-rating 4
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

Le projet compte actuellement **44 tests automatisés**.

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
* Lecture des données avec `pandas`
* Filtrage des données
* Affichage des résultats
* Tests automatisés
* **44 tests**
* Scraping de 1 000 livres sur Books to Scrape

Les prochaines évolutions porteront sur l'amélioration de la robustesse et l'exploitation des données.

````

### Petite remarque importante

J'ai volontairement **simplifié la représentation de `tests/`** dans le README. Il n'est pas nécessaire de documenter chaque `__init__.py` et chaque fichier de test individuellement : le README doit rester synthétique.

Et surtout, maintenant le README représente réellement notre architecture :

```text
book       → domaine
scraper    → technique HTTP
data       → exploitation
cli        → interaction utilisateur
utils      → fonctionnalités communes
tests      → validation
main.py    → orchestration
````

Après avoir remplacé ton README, fais simplement :

```bash
python -m pytest
git status
```

**On ne commitera qu'après avoir vérifié le `git status`.**