"""Tests des candidatures spontanées"""

from datetime import datetime

import pytest

from job.manual_offers import add_spontaneous_application
from storage.database import initialize_database
from storage.job_applications import get_application
from storage.job_offers import get_offer

NOW = datetime(2026, 10, 23, 12)


def test_spontaneous_application_is_followed_like_the_others(tmp_path):
    """Vérifie l'offre créée, le statut Postulé et la relance programmée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vSourceId = add_spontaneous_application(
        vDatabaseFile, "OVHcloud", "Développeur Java", "", "", NOW
    )
    vOffer = get_offer(vDatabaseFile, "manual", vSourceId)
    vApplication = get_application(vDatabaseFile, "manual", vSourceId)

    assert vOffer["title"] == "Candidature spontanée · Développeur Java"
    assert vOffer["description"] == "Candidature spontanée envoyée le 23/10/2026."
    assert vApplication["status"] == "APPLIED"
    assert vApplication["follow_up_date"] > NOW.isoformat()

    with pytest.raises(ValueError, match="entreprise manquante"):
        add_spontaneous_application(vDatabaseFile, "", "", "", "", NOW)
