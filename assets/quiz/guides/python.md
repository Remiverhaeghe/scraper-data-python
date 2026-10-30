# Python

## L'essentiel
- Langage interprété, typage dynamique, syntaxe par indentation.
- Très utilisé pour les scripts, l'automatisation, les données, le web (Django, FastAPI) et l'IoT.
- Environnements virtuels (venv) et gestion des dépendances (pip, uv, requirements).

## Types et structures
- Types immuables : int, float, str, tuple, frozenset. Mutables : list, dict, set.
- Compréhensions : [x * 2 for x in valeurs if x > 0].
- Déballage : a, b = b, a ; fonctions avec *args et **kwargs.
- f-strings pour formater : f"{nom} a {age} ans".

## Fonctions et objets
- Valeur par défaut mutable partagée entre appels : utiliser None puis créer la liste.
- Classes, héritage, méthodes spéciales (__init__, __repr__, __eq__).
- dataclasses pour des classes de données simples.
- Décorateurs (functools.lru_cache, property), gestionnaires de contexte (with).

## Bibliothèque standard utile
- pathlib (fichiers), json, csv, datetime, re (expressions régulières), logging, collections (Counter, defaultdict).
- itertools et functools pour les traitements en flux.

## Bonnes pratiques
- PEP 8 pour le style, Black pour le formatage, Ruff ou Pylint pour l'analyse.
- Annotations de type et mypy pour détecter des erreurs.
- Tests avec pytest, fixtures et paramétrage.
- Journaliser avec logging plutôt que print.

## Performances
- Choisir la bonne structure : un set pour tester l'appartenance, un dict pour un index.
- Mettre en cache les calculs répétés (lru_cache).
- Le GIL limite le calcul parallèle en threads : multiprocessing pour le calcul, threads ou asyncio pour les entrées-sorties.

## Pièges fréquents
- Argument par défaut mutable (def f(x=[])).
- Modifier une liste pendant qu'on la parcourt.
- Comparer des flottants avec ==.
- Attraper Exception sans la journaliser.

## En entretien
- Expliquez la différence entre liste et tuple, et le rôle du GIL.
- Montrez un script que vous avez écrit pour automatiser une tâche.

## Références
- [Documentation Python (en français)](https://docs.python.org/fr/3/)
- [Tutoriel Python](https://docs.python.org/fr/3/tutorial/index.html)
- [PEP 8](https://peps.python.org/pep-0008/)
