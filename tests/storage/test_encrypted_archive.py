"""Tests de la sauvegarde chiffrée par mot de passe"""

from datetime import datetime

import pandas as pd
import pytest

from storage.database import initialize_database
from storage.encrypted_archive import (
    export_encrypted_archive,
    read_encrypted_archive,
    restore_encrypted_archive,
)
from storage.job_offers import count_offers, save_offers

NOW = datetime(2026, 10, 24, 17, 0)
PASSWORD = "cle-usb-de-test"


def test_encrypted_copy_is_restored_with_its_password(tmp_path):
    """Vérifie la copie chiffrée, illisible en clair, puis sa restauration."""

    vDatabaseFile = tmp_path / "data" / "scraper.db"
    vDatabaseFile.parent.mkdir()
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "1", "title": "Secret RH"}]),
        NOW,
    )
    vUsb = tmp_path / "usb"
    vUsb.mkdir()

    vFile = export_encrypted_archive(vDatabaseFile, vUsb, PASSWORD, NOW)

    assert vFile.name == "jobboard-20261024-170000.jbk"
    assert b"Secret RH" not in vFile.read_bytes()
    assert not list(vUsb.glob("*.partiel"))

    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "2", "title": "Ajout"}]),
        NOW,
    )
    restore_encrypted_archive(vDatabaseFile, vFile, PASSWORD, NOW)

    assert count_offers(vDatabaseFile) == 1


def test_wrong_password_and_short_password_are_refused(tmp_path):
    """Vérifie les refus : mot de passe court, faux, ou fichier étranger."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    with pytest.raises(ValueError, match="trop court"):
        export_encrypted_archive(vDatabaseFile, tmp_path, "court", NOW)

    vFile = export_encrypted_archive(vDatabaseFile, tmp_path, PASSWORD, NOW)

    with pytest.raises(ValueError, match="Mot de passe incorrect"):
        read_encrypted_archive(vFile, "mauvais-mot-de-passe")

    vOther = tmp_path / "autre.jbk"
    vOther.write_bytes(b"pas une sauvegarde")

    with pytest.raises(ValueError, match="pas une sauvegarde"):
        read_encrypted_archive(vOther, PASSWORD)
