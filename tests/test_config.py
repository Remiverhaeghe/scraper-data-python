"""Tests de la configuration générale de l'application"""

from config import DATABASE_FILE, WEB_HOST


def test_database_file_is_configured():
    """Vérifie que le chemin de la base SQLite est configuré."""

    assert DATABASE_FILE == "data/scraper.db"


def test_web_dashboard_listens_locally():
    """Vérifie que le tableau de bord n'écoute que sur ce poste par défaut."""

    assert WEB_HOST == "127.0.0.1"
