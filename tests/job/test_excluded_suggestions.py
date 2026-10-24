"""Tests des mots exclus suggérés d'après les offres ignorées"""

from datetime import datetime

import pandas as pd

from job.offer_purge import save_excluded_words, suggest_excluded_words
from job.profile import build_profile, save_profile
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

TITLES = {
    "1": ("Commercial sédentaire Java", "IGNORED"),
    "2": ("Commercial terrain", "IGNORED"),
    "3": ("Commercial grands comptes", "IGNORED"),
    "4": ("Vendeur magasin", "IGNORED"),
    "5": ("Développeur terrain", "APPLIED"),
    "6": ("Vendeur Java", "IGNORED"),
    "7": ("Technicien Java", "IGNORED"),
}


def test_words_typical_of_ignored_offers_are_suggested(tmp_path):
    """Vérifie les mots suggérés : fréquents chez les ignorées, jamais chez les retenues."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": vId, "title": vTitle}
                for vId, (vTitle, _) in TITLES.items()
            ]
        ),
        datetime(2026, 10, 24),
    )

    for vId, (_, vStatus) in TITLES.items():
        save_application(vDatabaseFile, "lever", vId, vStatus)

    save_profile(vDatabaseFile, build_profile("", "", "Java", "", ""))

    # « terrain » apparaît dans une offre postulée ; « java » est une compétence.
    assert suggest_excluded_words(vDatabaseFile) == [("commercial", 3)]

    save_excluded_words(vDatabaseFile, "commercial")

    assert suggest_excluded_words(vDatabaseFile) == []
