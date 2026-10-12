"""Tests du garde-fou qui isole les tests des données réelles"""

import sqlite3
from pathlib import Path

import pytest

from config import DATABASE_FILE


@pytest.mark.parametrize(
    "pDatabase",
    [
        DATABASE_FILE,
        Path(DATABASE_FILE),
        Path(DATABASE_FILE).resolve().as_uri() + "?mode=ro",
    ],
)
def test_real_database_cannot_be_opened(pDatabase):
    """Vérifie qu'un test ne peut pas ouvrir la base réelle, sous aucune forme."""

    with pytest.raises(RuntimeError, match="Base réelle"):
        sqlite3.connect(pDatabase, uri=str(pDatabase).startswith("file:"))


def test_temporary_database_can_be_opened(tmp_path):
    """Vérifie qu'une base temporaire et une base en mémoire restent utilisables."""

    for vDatabase in (tmp_path / "scraper.db", ":memory:"):
        vConnection = sqlite3.connect(vDatabase)
        vConnection.execute("SELECT 1")
        vConnection.close()
