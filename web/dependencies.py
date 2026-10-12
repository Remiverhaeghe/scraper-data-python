"""Dépendances communes aux routes du tableau de bord et de l'API mobile"""

from config import DATABASE_FILE


# Base de données : remplaçable dans les tests par app.dependency_overrides.
def get_database_file():
    """Retourne le chemin de la base, remplaçable dans les tests."""

    rDatabaseFile = DATABASE_FILE

    return rDatabaseFile
