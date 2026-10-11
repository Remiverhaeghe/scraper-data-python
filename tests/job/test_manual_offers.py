"""Tests de l'ajout manuel et de l'import d'offres"""

import io
import json
from datetime import datetime

import pandas as pd
import pytest

from job.export import export_offers
from job.manual_offers import (
    add_manual_offer,
    describe_import,
    find_offer_errors,
    import_offers_file,
    normalize_offer,
    read_offers_file,
)
from storage.database import initialize_database
from storage.job_offers import get_offer, get_offers

NOW = datetime(2026, 10, 11, 10, 0)

OFFER = {
    "title": "Développeur Java H/F",
    "company": "Acme",
    "url": "https://acme.example/offre",
    "description": "Java, Spring et Docker. Télétravail partiel.",
    "location": "Lille",
    "contract": "cdi",
    "remote": "Oui",
}


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


@pytest.mark.parametrize(
    "pChanges, pExpected",
    [
        ({}, []),
        ({"title": " "}, ["titre manquant"]),
        ({"company": None}, ["entreprise manquante"]),
        ({"url": "", "description": ""}, ["lien ou description manquant"]),
        (
            {"url": "javascript:alert(1)"},
            ["lien invalide, http:// ou https:// attendu"],
        ),
        ({"contract": "stage"}, ["contrat inconnu, CDI, CDD, FREELANCE attendu"]),
        ({"title": "x" * 301}, ["titre trop long, 300 caractères au maximum"]),
    ],
)
def test_find_offer_errors(pChanges, pExpected):
    """Vérifie les champs obligatoires et les valeurs refusées."""

    assert find_offer_errors(normalize_offer({**OFFER, **pChanges})) == pExpected


def test_add_manual_offer_completes_and_saves(database_file):
    """Vérifie l'enregistrement complété d'une offre saisie, puis le refus du doublon."""

    vSourceId = add_manual_offer(database_file, OFFER, NOW)

    vOffer = get_offer(database_file, "manual", vSourceId)

    assert vOffer["contract"] == "CDI"
    # Comme pour les autres sources, SQLite range la valeur en texte.
    assert vOffer["remote"] == "1"
    assert "Java" in vOffer["skills"]
    assert vOffer["fingerprint"] == "developpeur java|acme|lille"

    with pytest.raises(ValueError, match="déjà dans la liste"):
        add_manual_offer(database_file, {**OFFER, "title": "Développeur Java"}, NOW)

    with pytest.raises(ValueError, match="titre manquant, entreprise manquante"):
        add_manual_offer(database_file, {"url": "https://a.example"}, NOW)


def test_import_round_trip_from_export(database_file, tmp_path):
    """Vérifie l'import d'un CSV exporté : intitulés, formules et doublons."""

    vExported = pd.DataFrame(
        [
            {**OFFER, "source": "remotive", "application_status": None},
            {**OFFER, "title": "=Chef de projet", "source": "adzuna"},
            {**OFFER, "title": "Data analyst", "company": None, "source": "jooble"},
        ]
    )
    vPath = tmp_path / "offres.csv"

    export_offers(vExported, vPath)

    vReport = import_offers_file(database_file, vPath, ".csv", NOW)

    assert vReport["added"] == 2
    assert vReport["rejected"] == [(4, "entreprise manquante")]
    assert describe_import(vReport) == (
        "2 offre(s) importée(s) sur 3, 0 doublon(s) écarté(s), 1 ligne(s) rejetée(s)."
    )
    assert sorted(get_offers(database_file)["title"]) == [
        "=Chef de projet",
        "Développeur Java H/F",
    ]

    vAgain = import_offers_file(database_file, vPath, ".csv", NOW)

    assert vAgain["added"] == 0
    assert len(vAgain["duplicates"]) == 2


def test_read_offers_file_formats_and_errors():
    """Vérifie la lecture du JSON envoyé et les messages des fichiers refusés."""

    vRows = read_offers_file(io.BytesIO(json.dumps([OFFER]).encode()), ".JSON")

    assert vRows == [(1, OFFER)]

    with pytest.raises(ValueError, match="Format non pris en charge"):
        read_offers_file(io.BytesIO(b""), ".txt")

    with pytest.raises(ValueError, match="liste d'offres"):
        read_offers_file(io.BytesIO(b'{"title": "x"}'), ".json")

    with pytest.raises(ValueError, match="Fichier illisible"):
        read_offers_file(io.BytesIO(b"pas du json"), ".json")
