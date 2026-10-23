"""Tests de l'enregistrement des offres d'emploi en base"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from job.agencies import INTERIM_AGENCIES
from storage.database import connect_database, initialize_database
from storage.job_applications import save_application
from storage.job_offers import (
    CONTENT_COLUMNS,
    count_new_offers_by_day,
    count_offers,
    get_offer,
    get_offers,
    get_offers_to_check,
    read_remote,
    save_offers,
)


def build_items():
    """Construit un DataFrame minimal pour les tests."""

    rItems = pd.DataFrame(
        [{"source": "lever", "source_id": "123", "title": "Développeur Python"}]
    )

    return rItems


def build_database(pTmpPath):
    """Crée une base initialisée dans un dossier temporaire."""

    rDatabaseFile = Path(pTmpPath) / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_job_offer_table_contains_content_columns(tmp_path):
    """Vérifie que la table contient toutes les colonnes de JOB_COLUMNS."""

    vDatabaseFile = build_database(tmp_path)

    vConnection = connect_database(vDatabaseFile)

    try:
        vColumns = {
            vRow[1] for vRow in vConnection.execute("PRAGMA table_info(job_offer)")
        }

    finally:
        vConnection.close()

    assert set(CONTENT_COLUMNS) <= vColumns


def test_new_job_gets_first_seen_at(tmp_path):
    """Vérifie qu'une nouvelle offre reçoit une date de première découverte."""

    vDatabaseFile = build_database(tmp_path)

    vScrapedAt = datetime(2026, 10, 1, 10, 0, 0)

    vItems = save_offers(vDatabaseFile, build_items(), vScrapedAt)

    assert vItems.loc[0, "scraped_at"] == vScrapedAt
    assert vItems.loc[0, "first_seen_at"] == vScrapedAt
    assert vItems.loc[0, "is_new"] == True


def test_existing_job_keeps_first_seen_at(tmp_path):
    """Vérifie qu'une offre déjà connue garde sa date de découverte."""

    vDatabaseFile = build_database(tmp_path)

    vFirstScrapedAt = datetime(2026, 10, 1, 10, 0, 0)
    vSecondScrapedAt = datetime(2026, 10, 2, 10, 0, 0)

    save_offers(vDatabaseFile, build_items(), vFirstScrapedAt)

    vItems = save_offers(vDatabaseFile, build_items(), vSecondScrapedAt)

    assert vItems.loc[0, "first_seen_at"] == vFirstScrapedAt
    assert vItems.loc[0, "scraped_at"] == vSecondScrapedAt
    assert vItems.loc[0, "is_new"] == False


def test_same_source_id_is_tracked_separately(tmp_path):
    """Vérifie qu'un même source_id de deux sources donne deux offres."""

    vDatabaseFile = build_database(tmp_path)

    vItems = pd.DataFrame(
        [
            {"source": "lever", "source_id": "123", "title": "Offre Lever"},
            {"source": "greenhouse", "source_id": "123", "title": "Offre Greenhouse"},
        ]
    )

    vResult = save_offers(vDatabaseFile, vItems, datetime(2026, 10, 1, 10, 0, 0))

    assert vResult["is_new"].tolist() == [True, True]
    assert len(get_offers(vDatabaseFile)) == 2


def test_existing_job_content_is_updated(tmp_path):
    """Vérifie que le contenu d'une offre connue est mis à jour."""

    vDatabaseFile = build_database(tmp_path)

    save_offers(vDatabaseFile, build_items(), datetime(2026, 10, 1, 10, 0, 0))

    vItems = build_items()
    vItems["title"] = "Développeur Python senior"

    save_offers(vDatabaseFile, vItems, datetime(2026, 10, 2, 10, 0, 0))

    vOffers = get_offers(vDatabaseFile)

    assert vOffers.loc[0, "title"] == "Développeur Python senior"
    assert vOffers.loc[0, "first_seen_at"] == "2026-10-01T10:00:00"
    assert vOffers.loc[0, "last_seen_at"] == "2026-10-02T10:00:00"


def test_job_without_source_id_is_not_saved(tmp_path):
    """Vérifie qu'une offre sans source_id n'est pas enregistrée."""

    vDatabaseFile = build_database(tmp_path)

    vItems = pd.DataFrame([{"source": "lever", "source_id": None, "title": "Offre"}])

    vResult = save_offers(vDatabaseFile, vItems, datetime(2026, 10, 1, 10, 0, 0))

    assert vResult.loc[0, "is_new"] == False
    assert get_offers(vDatabaseFile).empty


def test_non_scalar_values_are_saved(tmp_path):
    """Vérifie l'enregistrement des listes, dates et valeurs manquantes."""

    vDatabaseFile = build_database(tmp_path)

    vItems = build_items()
    vItems["skills"] = [[{"libelle": "Python"}]]
    vItems["published_at"] = [pd.Timestamp("2026-09-30 08:00:00")]
    vItems["salary_min"] = [float("nan")]

    save_offers(vDatabaseFile, vItems, datetime(2026, 10, 1, 10, 0, 0))

    vOffers = get_offers(vDatabaseFile)

    assert vOffers.loc[0, "skills"] == '[{"libelle": "Python"}]'
    assert vOffers.loc[0, "published_at"] == "2026-09-30T08:00:00"
    assert pd.isna(vOffers.loc[0, "salary_min"])


def test_get_offers_returns_most_recent_first(tmp_path):
    """Vérifie que les offres découvertes en dernier sont retournées en premier."""

    vDatabaseFile = build_database(tmp_path)

    save_offers(vDatabaseFile, build_items(), datetime(2026, 10, 1, 10, 0, 0))

    vItems = pd.DataFrame([{"source": "lever", "source_id": "456", "title": "Récente"}])

    save_offers(vDatabaseFile, vItems, datetime(2026, 10, 2, 10, 0, 0))

    vOffers = get_offers(vDatabaseFile)

    assert vOffers["source_id"].tolist() == ["456", "123"]


def build_tracked_database(pTmpPath):
    """Crée une base avec trois offres, dont deux suivies."""

    rDatabaseFile = build_database(pTmpPath)

    vItems = pd.DataFrame(
        [
            {"source": "lever", "source_id": vId, "title": f"Offre {vId}"}
            for vId in ("1", "2", "3")
        ]
    )

    save_offers(rDatabaseFile, vItems, datetime(2026, 10, 1, 10, 0, 0))

    save_application(rDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 1))
    save_application(rDatabaseFile, "lever", "2", "IGNORED")

    return rDatabaseFile


def test_get_offers_includes_application_status(tmp_path):
    """Vérifie que le statut du suivi accompagne chaque offre."""

    vOffers = get_offers(build_tracked_database(tmp_path))

    vStatuses = dict(zip(vOffers["source_id"], vOffers["application_status"]))

    assert vStatuses["1"] == "APPLIED"
    assert pd.isna(vStatuses["3"])


def test_get_offers_hides_ignored_offers(tmp_path):
    """Vérifie le masquage des offres ignorées."""

    vOffers = get_offers(build_tracked_database(tmp_path), pHideIgnored=True)

    assert sorted(vOffers["source_id"]) == ["1", "3"]


def test_get_offers_filters_status(tmp_path):
    """Vérifie que filtrer sur un statut affiche aussi les offres ignorées."""

    vOffers = get_offers(
        build_tracked_database(tmp_path), pStatus="IGNORED", pHideIgnored=True
    )

    assert vOffers["source_id"].tolist() == ["2"]


def test_get_offers_filters_follow_ups_due(tmp_path):
    """Vérifie la sélection des candidatures à relancer."""

    vDatabaseFile = build_tracked_database(tmp_path)

    assert get_offers(vDatabaseFile, pFollowUpBefore=datetime(2026, 10, 5)).empty

    vOffers = get_offers(vDatabaseFile, pFollowUpBefore=datetime(2026, 10, 9))

    assert vOffers["source_id"].tolist() == ["1"]


def test_count_offers_applies_filters(tmp_path):
    """Vérifie que le comptage applique les mêmes filtres que la lecture."""

    vDatabaseFile = build_tracked_database(tmp_path)

    assert count_offers(vDatabaseFile) == 3
    assert count_offers(vDatabaseFile, pHideIgnored=True) == 2
    assert count_offers(vDatabaseFile, pStatus="APPLIED") == 1


def test_get_offer(tmp_path):
    """Vérifie la lecture d'une offre et le cas d'une offre inconnue."""

    vDatabaseFile = build_tracked_database(tmp_path)

    assert get_offer(vDatabaseFile, "lever", "1")["title"] == "Offre 1"
    assert get_offer(vDatabaseFile, "lever", "inconnue") is None


def test_count_new_offers_by_day(tmp_path):
    """Vérifie le décompte quotidien, jours sans nouvelle offre compris."""

    vDatabaseFile = build_database(tmp_path)

    vItems = pd.DataFrame(
        [{"source": "lever", "source_id": vId} for vId in ("1", "2", "3")]
    )

    save_offers(vDatabaseFile, vItems.iloc[:2], datetime(2026, 10, 8, 9, 0))
    save_offers(vDatabaseFile, vItems.iloc[2:], datetime(2026, 10, 10, 9, 0))

    rCounts = count_new_offers_by_day(vDatabaseFile, 3, datetime(2026, 10, 10, 12, 0))

    assert [(vDay.isoformat(), vCount) for vDay, vCount in rCounts] == [
        ("2026-10-08", 2),
        ("2026-10-09", 0),
        ("2026-10-10", 1),
    ]


def build_salary_database(pTmpPath):
    """Crée une base avec trois offres : sans salaire, à 2 000 € et à 3 000 € net."""

    rDatabaseFile = build_database(pTmpPath)

    vItems = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "1",
                "published_at": "2026-09-01T10:00:00Z",
            },
            {
                "source": "lever",
                "source_id": "2",
                "salary_net_monthly_min": 2000,
                "published_at": "2026-10-08T10:00:00Z",
            },
            {
                "source": "lever",
                "source_id": "3",
                "salary_net_monthly_min": 3000,
                "salary_net_monthly_max": 3500,
            },
        ]
    )

    save_offers(rDatabaseFile, vItems, datetime(2026, 10, 10, 9, 0))

    return rDatabaseFile


def get_ids(pDatabaseFile, **pFilters):
    """Retourne les identifiants des offres correspondant aux filtres."""

    rIds = sorted(get_offers(pDatabaseFile, **pFilters)["source_id"])

    return rIds


def test_get_offers_filters_salary_range(tmp_path):
    """Vérifie les bornes de salaire et le filtre des offres avec salaire."""

    vDatabaseFile = build_salary_database(tmp_path)

    assert get_ids(vDatabaseFile, pMinNetSalary=2500) == ["3"]
    assert get_ids(vDatabaseFile, pMaxNetSalary=2500) == ["2"]
    assert get_ids(vDatabaseFile, pHasSalary=True) == ["2", "3"]


def test_get_offers_filters_publication_date(tmp_path):
    """Vérifie que la date de découverte remplace une date de publication absente."""

    vDatabaseFile = build_salary_database(tmp_path)

    assert get_ids(vDatabaseFile, pPublishedSince=datetime(2026, 10, 1)) == ["2", "3"]


def test_get_offers_filters_keys(tmp_path):
    """Vérifie la restriction aux offres d'une recherche, liste vide comprise."""

    vDatabaseFile = build_salary_database(tmp_path)

    assert get_ids(vDatabaseFile, pKeys=[("lever", "1"), ("lever", "3")]) == ["1", "3"]
    assert get_ids(vDatabaseFile, pKeys=[]) == []


def test_offers_to_check_keep_only_checked_fields(tmp_path):
    """Vérifie les champs lus pour la qualité : description réduite à sa présence."""

    vDatabaseFile = build_database(tmp_path)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "1", "title": "A", "description": "x"},
                {"source": "lever", "source_id": "2", "title": "B", "description": ""},
            ]
        ),
        datetime.now(),
    )

    vOffers = {
        vOffer["source_id"]: vOffer for vOffer in get_offers_to_check(vDatabaseFile)
    }

    assert vOffers["1"]["description"] == 1
    assert not vOffers["2"]["description"]
    assert vOffers["1"]["title"] == "A" and vOffers["1"]["company"] is None


def test_get_offers_hides_interim_agencies(tmp_path):
    """Vérifie que les agences sont reconnues par mot entier dans l'entreprise."""

    vDatabaseFile = build_database(tmp_path)
    vOffers = [
        ("1", "technicien|proman 123|lille", ""),
        ("2", "technicien|alstom|valenciennes", "Poste chez Alstom."),
        ("3", "technicien|groupe atlantic|lyon", "Notre agence d'intérim recrute."),
        ("4", "chargé adecco|cristal union|reims", ""),
        ("5", "technicien|cristal union|reims", ""),
        ("6", None, ""),
    ]
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": vId,
                    "title": "Technicien",
                    "fingerprint": vFingerprint,
                    "description": vDescription,
                }
                for vId, vFingerprint, vDescription in vOffers
            ]
        ),
        datetime(2026, 10, 23),
    )

    vIds = sorted(
        get_offers(vDatabaseFile, pHiddenAgencies=list(INTERIM_AGENCIES))["source_id"]
    )

    assert vIds == ["2", "4", "5", "6"]


@pytest.mark.parametrize(
    ("pValue", "pExpected"),
    [("1", True), ("0", False), ("true", True), (None, None), (float("nan"), None)],
)
def test_remote_is_read_as_a_boolean(pValue, pExpected):
    """Vérifie le télétravail lu en base : « 0 » ne doit pas valoir vrai."""

    assert read_remote(pValue) is pExpected


def test_get_offers_hides_consulting_firms_and_training(tmp_path):
    """Vérifie le masquage des ESN par mot entier, et des stages et alternances."""

    vDatabaseFile = build_database(tmp_path)
    vOffers = [
        ("1", "Développeur Java", "developpeur java|alten|lille"),
        ("2", "Développeur Java", "developpeur java|altenergie|lille"),
        ("3", "Stage - Développeur Java", "stage developpeur java|kiabi|hem"),
        ("4", "Alternant(e) développeur", "alternant developpeur|kiabi|hem"),
        ("5", "Développeur backstage", "developpeur backstage|kiabi|hem"),
    ]
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": vId,
                    "title": vTitle,
                    "fingerprint": vFingerprint,
                }
                for vId, vTitle, vFingerprint in vOffers
            ]
        ),
        datetime(2026, 10, 23),
    )

    vWithoutFirms = get_offers(vDatabaseFile, pHiddenCompanies=["alten"])
    vWithoutTraining = get_offers(vDatabaseFile, pHideTraining=True)

    assert sorted(vWithoutFirms["source_id"]) == ["2", "3", "4", "5"]
    assert sorted(vWithoutTraining["source_id"]) == ["1", "2", "5"]
