"""Tests de la purge des offres hors sujet"""

from datetime import datetime

import pandas as pd
import pytest

from job.offer_purge import (
    add_excluded_words,
    drop_excluded_offers,
    find_offers_to_purge,
    load_excluded_words,
    parse_purge_words,
    purge_offers,
    save_excluded_words,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import count_offers, save_offers

NOW = datetime(2026, 10, 19, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec trois offres, dont un stage suivi par une candidature."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": "1", "title": "Développeur Java"},
                {"source": "remotive", "source_id": "2", "title": "Stage Java"},
                {"source": "remotive", "source_id": "3", "title": "STAGE data"},
            ]
        ),
        NOW,
    )
    save_application(rDatabaseFile, "remotive", "3", "APPLIED", pNow=NOW)

    return rDatabaseFile


@pytest.mark.parametrize(
    "pText, pMessage",
    [("", "au moins un mot"), ("stage, it", r"Mots trop courts \(it\)")],
)
def test_parse_purge_words_rejects_unusable_words(pText, pMessage):
    """Vérifie le refus d'une saisie vide ou d'un mot trop court."""

    with pytest.raises(ValueError, match=pMessage):
        parse_purge_words(pText)


def test_purge_keeps_offers_with_application(database_file):
    """Vérifie l'aperçu, la sauvegarde et la protection des offres suivies."""

    vWords = parse_purge_words("stage, alternance")

    assert [
        vOffer["source_id"] for vOffer in find_offers_to_purge(database_file, vWords)
    ] == ["2"]

    vCount, vBackupFile = purge_offers(database_file, vWords, NOW)

    assert vCount == 1
    assert vBackupFile.exists()
    assert "avant-purge" in vBackupFile.name
    assert count_offers(database_file) == 2


def test_purge_without_match_makes_no_backup(database_file):
    """Vérifie qu'aucune sauvegarde n'est faite quand rien n'est supprimé."""

    assert purge_offers(database_file, ["commercial"], NOW) == (0, None)


def test_excluded_words_are_kept_and_drop_offers(database_file):
    """Vérifie l'ajout des mots exclus et le retrait des offres récupérées."""

    assert load_excluded_words(database_file) == []
    assert add_excluded_words(database_file, ["stage", "Stage", "alternance"]) == [
        "stage",
        "alternance",
    ]

    vItems = pd.DataFrame([{"title": "Stage Java"}, {"title": "Développeur"}])
    vKept, vCount = drop_excluded_offers(vItems, load_excluded_words(database_file))

    assert (vKept["title"].tolist(), vCount) == (["Développeur"], 1)
    assert drop_excluded_offers(vItems, []) == (vItems, 0)
    assert save_excluded_words(database_file, "") == []

    with pytest.raises(ValueError, match="trop courts"):
        save_excluded_words(database_file, "it")
