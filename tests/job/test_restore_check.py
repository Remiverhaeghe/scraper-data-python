"""Tests de l'essai mensuel de restauration"""

from datetime import datetime, timedelta

import pandas as pd

from job.restore_check import check_restore, load_restore_check, run_due_restore_check
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


def test_restore_is_tried_monthly_and_kept(tmp_path):
    """Vérifie l'essai réussi, gardé, puis pas refait avant un mois."""

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
