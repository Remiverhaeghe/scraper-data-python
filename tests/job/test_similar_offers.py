"""Tests des offres proches de celles retenues"""

from datetime import datetime, timedelta

import pandas as pd

from job.similar_offers import (
    build_signature,
    compute_similarity,
    find_similar_offers,
    mark_like_ignored,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 23, 12)


def save_offer_list(pDatabaseFile, pOffers, pSeenAt):
    """Enregistre des offres Lever : identifiant, titre et compétences."""

    save_offers(
        pDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": vId,
                    "title": vTitle,
                    "skills": vSkills,
                }
                for vId, vTitle, vSkills in pOffers
            ]
        ),
        pSeenAt,
    )


def test_signature_and_similarity():
    """Vérifie les mots retenus du titre, les compétences et l'indice commun."""

    vFirst = build_signature(
        {"title": "Technicien de maintenance (H/F) CDI", "skills": '["GMAO"]'}
    )
    vSecond = build_signature({"title": "Technicien maintenance", "skills": None})

    assert vFirst == {"technicien", "maintenance", "competence:gmao"}
    assert compute_similarity(vFirst, vSecond) == 67
    assert compute_similarity(set(), set()) == 0


def test_similar_offers_follow_the_retained_ones(tmp_path):
    """Vérifie la comparaison aux offres retenues, sans les offres déjà suivies."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert find_similar_offers(vDatabaseFile, NOW, 4) == []

    save_offer_list(
        vDatabaseFile,
        [("ref", "Technicien de maintenance", '["GMAO", "Pneumatique"]')],
        NOW - timedelta(days=30),
    )
    save_offer_list(
        vDatabaseFile,
        [
            ("proche", "Technicien maintenance industrielle", '["GMAO"]'),
            ("loin", "Comptable", '["Excel"]'),
            ("suivie", "Technicien de maintenance", '["GMAO"]'),
        ],
        NOW - timedelta(days=2),
    )
    save_application(vDatabaseFile, "lever", "ref", "APPLIED", pNow=NOW)
    save_application(vDatabaseFile, "lever", "suivie", "INTERESTED", pNow=NOW)

    vOffers = find_similar_offers(vDatabaseFile, NOW, 4)

    assert [vOffer["source_id"] for vOffer in vOffers] == ["proche"]
    assert vOffers[0]["reference_title"] == "Technicien de maintenance"
    assert vOffers[0]["similarity"] == 75


def test_offers_like_an_ignored_one_are_marked(tmp_path):
    """Vérifie le signalement des offres proches d'un refus, jamais des offres suivies."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "0", "title": "Vendeur magasin sport"},
            ]
        ),
        datetime(2026, 10, 24),
    )
    save_application(vDatabaseFile, "lever", "0", "IGNORED")
    vOffers = [
        {"title": "Vendeur magasin sport"},
        {"title": "Développeur Python"},
        {"title": "Vendeur magasin sport", "application_status": "APPLIED"},
    ]

    mark_like_ignored(vDatabaseFile, vOffers)

    assert [vOffer["like_ignored"] for vOffer in vOffers] == [
        "Vendeur magasin sport",
        None,
        None,
    ]
