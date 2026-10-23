"""Tests de la copie des sauvegardes automatiques sur le NAS"""

from datetime import datetime

import pytest

from storage.backup import (
    AUTO_BACKUP_REASON,
    backup_database,
    copy_to_nas,
    get_last_nas_copy_time,
    list_nas_copies,
)
from storage.database import initialize_database


def test_backup_is_copied_to_the_nas_once_with_rotation(tmp_path):
    """Vérifie la copie sur le NAS, sans doublon, et la rotation des anciennes."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vNas = tmp_path / "nas" / "jobboard"

    for vDay in range(1, 4):
        backup_database(vDatabaseFile, datetime(2026, 10, vDay, 2), AUTO_BACKUP_REASON)
        copy_to_nas(vDatabaseFile, vNas, pKeepCount=2)

    assert copy_to_nas(vDatabaseFile, vNas, pKeepCount=2) is None
    assert [vCopy.name for vCopy in list_nas_copies(vDatabaseFile, vNas)] == [
        "scraper-20261003-020000-auto.db",
        "scraper-20261002-020000-auto.db",
    ]
    assert not list(vNas.glob("*.partiel"))
    assert get_last_nas_copy_time(vDatabaseFile, vNas) == datetime(2026, 10, 3, 2)


def test_unreachable_nas_is_retried_later(tmp_path, caplog):
    """Vérifie qu'un NAS injoignable est signalé, puis rattrapé quand il revient."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    backup_database(vDatabaseFile, datetime(2026, 10, 1, 2), AUTO_BACKUP_REASON)

    # Un fichier à la place du dossier simule un partage réseau absent.
    vBlocked = tmp_path / "nas"
    vBlocked.write_text("pas un dossier", encoding="utf-8")

    assert copy_to_nas(vDatabaseFile, vBlocked / "jobboard") is None
    assert "nouvel essai au prochain passage" in caplog.text

    with pytest.raises(OSError):
        get_last_nas_copy_time(vDatabaseFile, vBlocked / "jobboard")

    vBlocked.unlink()

    assert copy_to_nas(vDatabaseFile, vBlocked / "jobboard") is not None
