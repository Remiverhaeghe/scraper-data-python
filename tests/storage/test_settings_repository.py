"""Tests des réglages enregistrés en base"""

import pytest

from storage.database import initialize_database
from storage.settings_repository import (
    load_json_setting,
    save_json_setting,
    save_setting_values,
)


@pytest.mark.parametrize(
    "pStored, pExpected",
    [(None, []), ("pas du json", []), ('{"a": 1}', []), ("[1, 2]", [1, 2])],
)
def test_load_json_setting_falls_back_to_default(tmp_path, pStored, pExpected):
    """Vérifie la valeur par défaut d'un réglage absent, illisible ou mal formé."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    if pStored is not None:
        save_setting_values(vDatabaseFile, {"essai": pStored})

    assert load_json_setting(vDatabaseFile, "essai", [], list) == pExpected


def test_save_json_setting_round_trip_and_clear(tmp_path):
    """Vérifie l'aller-retour d'un réglage JSON et son effacement par None."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_json_setting(vDatabaseFile, "essai", {"nom": "Éa"})

    assert load_json_setting(vDatabaseFile, "essai", None) == {"nom": "Éa"}

    save_json_setting(vDatabaseFile, "essai", None)

    assert load_json_setting(vDatabaseFile, "essai", "défaut") == "défaut"
