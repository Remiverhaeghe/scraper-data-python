"""Tests des agences d'intérim reconnues"""

from job.agencies import (
    INTERIM_AGENCIES,
    is_agency_offer,
    is_consulting_offer,
    load_interim_agencies,
    mark_agency_offers,
    save_interim_agencies,
)
from storage.database import initialize_database


def test_agency_list_is_saved_then_reset(tmp_path):
    """Vérifie la liste saisie, normalisée et dédoublonnée, puis la liste par défaut."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert load_interim_agencies(vDatabaseFile) == list(INTERIM_AGENCIES)
    assert save_interim_agencies(
        vDatabaseFile, "Proman\nAgence Locale SAS; proman"
    ) == [
        "agence locale",
        "proman",
    ]
    assert load_interim_agencies(vDatabaseFile) == ["agence locale", "proman"]
    assert save_interim_agencies(vDatabaseFile, " ") == list(INTERIM_AGENCIES)


def test_agency_offers_are_recognized():
    """Vérifie l'agence par mot entier dans l'entreprise ou par la description."""

    vOffers = [
        {"company": "PROMAN 123"},
        {"company": "Promanex"},
        {"company": "Acme", "description": "Notre Agence d'Intérim recrute."},
        {"company": None},
    ]

    mark_agency_offers(vOffers, ["proman"])

    assert [vOffer["is_agency"] for vOffer in vOffers] == [True, False, True, False]
    assert not is_agency_offer({}, INTERIM_AGENCIES)


def test_consulting_firms_are_marked():
    """Vérifie le repérage des ESN par mot entier dans le nom de l'entreprise."""

    vOffers = [
        {"company": "ALTEN SA"},
        {"company": "Sopra Steria Group"},
        {"company": "Altenergie"},
        {"company": None},
    ]

    mark_agency_offers(vOffers, INTERIM_AGENCIES)

    assert [vOffer["is_consulting"] for vOffer in vOffers] == [True, True, False, False]
    assert is_consulting_offer({"company": "Néosoft"})
