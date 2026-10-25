"""Tests de l'essai mensuel de restauration"""

from datetime import datetime, timedelta

import pandas as pd
from cryptography.fernet import Fernet

import job.restore_check as restore_check
from job.restore_check import (
    check_nas_restore,
    check_restore,
    load_restore_check,
    run_due_restore_check,
)
from storage.backup import backup_database
from storage.database import initialize_database
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 24, 12, 0)


def save_offer_count(pDatabaseFile, pCount, pStart=0):
    """Enregistre pCount offres numérotées à partir de pStart."""

    save_offers(
        pDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": str(vId), "title": "Dev"}
                for vId in range(pStart, pStart + pCount)
            ]
        ),
        NOW,
    )


def test_restore_is_tried_monthly_and_kept(tmp_path, monkeypatch):
    """Vérifie l'essai réussi, gardé, puis pas refait avant un mois."""

    monkeypatch.setattr(restore_check, "BACKUP_NAS_DIRECTORY", None)
    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offer_count(vDatabaseFile, 3)
    backup_database(vDatabaseFile, NOW, "auto")

    vResult = run_due_restore_check(vDatabaseFile, NOW)

    assert vResult["success"]
    assert vResult["message"].endswith("restaurée à l'essai : 3 offre(s)")
    assert load_restore_check(vDatabaseFile) == vResult
    assert run_due_restore_check(vDatabaseFile, NOW + timedelta(days=10)) is None


def test_restore_fails_without_backup_or_with_too_few_offers(tmp_path):
    """Vérifie l'échec sans sauvegarde, puis avec une sauvegarde trop ancienne."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert check_restore(vDatabaseFile) == (False, "Aucune sauvegarde à restaurer")

    save_offer_count(vDatabaseFile, 1)
    backup_database(vDatabaseFile, NOW, "auto")
    save_offer_count(vDatabaseFile, 9, 1)

    vSuccess, vMessage = check_restore(vDatabaseFile)

    assert not vSuccess
    assert "1 offre(s) seulement, contre 10 en base" in vMessage


def test_nas_copy_is_restored_plain_or_encrypted(tmp_path, monkeypatch):
    """Vérifie l'essai d'une copie du NAS : en clair, chiffrée, mauvaise clé ou absente."""

    vDatabaseFile = tmp_path / "data" / "scraper.db"
    vDatabaseFile.parent.mkdir()
    initialize_database(vDatabaseFile)
    save_offer_count(vDatabaseFile, 3)
    vBackup = backup_database(vDatabaseFile, NOW, "auto")
    vNas = tmp_path / "nas"
    vNas.mkdir()
    vKey = Fernet.generate_key()

    assert check_nas_restore(vDatabaseFile, vNas, vKey) == (
        False,
        "Aucune copie sur le NAS",
    )

    (vNas / vBackup.name).write_bytes(vBackup.read_bytes())

    assert check_nas_restore(vDatabaseFile, vNas, vKey)[0]

    (vNas / vBackup.name).unlink()
    vEncrypted = vNas / (vBackup.name + ".chiffre")
    vEncrypted.write_bytes(Fernet(vKey).encrypt(vBackup.read_bytes()))

    assert check_nas_restore(vDatabaseFile, vNas, vKey)[1].endswith(
        "restaurée à l'essai : 3 offre(s)"
    )
    assert check_nas_restore(vDatabaseFile, vNas, Fernet.generate_key())[1].endswith(
        "chiffrée avec une autre clé"
    )
    assert (
        "BACKUP_ENCRYPTION_KEY manquante"
        in check_nas_restore(vDatabaseFile, vNas, None)[1]
    )

    monkeypatch.setattr(restore_check, "BACKUP_NAS_DIRECTORY", None)

    assert check_nas_restore(vDatabaseFile) is None


def test_monthly_check_includes_the_nas_copy(tmp_path, monkeypatch):
    """Vérifie que l'essai mensuel échoue si la copie du NAS manque."""

    vDatabaseFile = tmp_path / "data" / "scraper.db"
    vDatabaseFile.parent.mkdir()
    initialize_database(vDatabaseFile)
    save_offer_count(vDatabaseFile, 2)
    backup_database(vDatabaseFile, NOW, "auto")
    monkeypatch.setattr(restore_check, "BACKUP_NAS_DIRECTORY", tmp_path / "nas")
    (tmp_path / "nas").mkdir()

    vResult = run_due_restore_check(vDatabaseFile, NOW)

    assert not vResult["success"]
    assert vResult["message"].endswith(" ; NAS : Aucune copie sur le NAS")
