# 🐍 Web Scraper Automatique (Python)

[![License: MIT](https://shields.io)](https://opensource.org)

Ce projet est un script d'automatisation écrit en Python permettant d'extraire, de nettoyer et de structurer des données publiques provenant d'un site web cible (ex: offres d'emploi, prix de produits) afin de les exporter dans un format exploitable.

## 🎯 Objectifs Pédagogiques
- Maîtriser la manipulation du DOM HTML à l'aide de scripts.
- Structurer des flux de données non organisés.
- Gérer l'exportation et l'écriture de fichiers (`.csv`, `.xlsx`).

## 🛠️ Stack Technique
- **Langage :** Python 3
- **Librairies clés :** `requests` (requêtes HTTP), `beautifulsoup4` (parsing HTML), `pandas` (analyse et structuration des données).

## 🚀 Comment installer et lancer le script

1. Cloner le dépôt et y accéder :
   ```bash
   git clone https://github.com
   cd scraper-data-python
   ```
2. Créer et activer un environnement virtuel (recommandé) :
   ```bash
   python -m venv venv
   # Sur Windows:
   venv\Scripts\activate
   # Sur Mac/Linux:
   source venv/bin/activate
   ```
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Exécuter le script principal :
   ```bash
   python main.py
   ```
