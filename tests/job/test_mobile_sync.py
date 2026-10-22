"""Tests de la synchronisation avec l'application mobile de révision"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from job.mobile_sync import (
    MAX_SYNC_ANSWERS,
    build_connection_png,
    build_connection_svg,
    build_progress,
    build_quiz_package,
    check_mobile_token,
    get_mobile_token,
    renew_mobile_token,
    sync_answers,
)
from job.quiz import get_review_schedule, load_quiz
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers
from storage.quiz_answers import get_last_answers

NOW = datetime(2026, 10, 12, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def build_answer(pClientId, pChoice, pAnsweredAt, pQuestionId="sql-null"):
    """Construit une réponse telle que l'envoie le téléphone."""

    rAnswer = {
        "id": pClientId,
        "question_id": pQuestionId,
        "choice": pChoice,
        "answered_at": pAnsweredAt.isoformat(),
    }

    return rAnswer


def test_package_contains_everything_for_offline_use(database_file):
    """Vérifie le paquet : questions corrigeables hors ligne et version stable."""

    vPackage = build_quiz_package(database_file, NOW)
    vQuestion = next(
        vItem for vItem in vPackage["questions"] if vItem["id"] == "sql-null"
    )

    assert vPackage["api_version"] == 1
    assert {"answer", "explanation", "choices", "theme"} <= set(vQuestion)
    assert vPackage["levels"][0] == "débutant"
    assert vPackage["version"] == build_quiz_package(database_file, NOW)["version"]


def test_sync_recomputes_corrections_and_ignores_duplicates(database_file):
    """Vérifie l'envoi : correction recalculée, doublon ignoré, refus motivés."""

    vCorrect = load_quiz()["sql"]["questions"]
    vAnswer = next(vItem for vItem in vCorrect if vItem["id"] == "sql-null")["answer"]

    vReport = sync_answers(
        database_file,
        [
            build_answer("telephone-0001", vAnswer, NOW - timedelta(hours=2)),
            build_answer("telephone-0001", vAnswer, NOW - timedelta(hours=2)),
            build_answer("telephone-0002", 99, NOW),
            build_answer("telephone-0003", 0, NOW, "inconnue"),
            build_answer("telephone-0004", 0, NOW + timedelta(days=3)),
            {"id": "x", "question_id": "sql-null", "choice": 0},
            {**build_answer("telephone-0005", 0, NOW), "answered_at": "hier"},
            {**build_answer("telephone-0006", True, NOW)},
            "pas une réponse",
        ],
        NOW,
    )

    assert (vReport["received"], vReport["added"], vReport["duplicates"]) == (9, 1, 1)
    assert len(vReport["rejected"]) == 7
    assert get_last_answers(database_file) == {"sql-null": True}

    # Renvoyer le même lot après une coupure ne change rien.
    vAgain = sync_answers(
        database_file,
        [build_answer("telephone-0001", vAnswer, NOW - timedelta(hours=2))],
        NOW,
    )

    assert (vAgain["added"], vAgain["duplicates"]) == (0, 1)


def test_late_answers_keep_their_place_in_history(database_file):
    """Vérifie qu'une réponse ancienne reçue tard ne passe pas pour la plus récente."""

    sync_answers(database_file, [build_answer("telephone-0010", 1, NOW)], NOW)
    sync_answers(
        database_file,
        [build_answer("telephone-0011", 0, NOW - timedelta(days=2))],
        NOW,
    )

    assert get_last_answers(database_file) == {"sql-null": True}
    # Faux avant-hier (boîte 1), puis juste aujourd'hui : boîte 2.
    assert get_review_schedule(database_file)["sql-null"]["box"] == 2

    vProgress = build_progress(database_file, NOW)

    assert vProgress["questions"]["sql-null"]["last_correct"] is True
    assert vProgress["statistics"]["answers"] == 2
    assert vProgress["statistics"]["days"][-1] == {
        "date": NOW.date().isoformat(),
        "answers": 1,
        "correct": 1,
    }


def test_sync_refuses_invalid_batches(database_file):
    """Vérifie le refus d'un envoi qui n'est pas une liste ou qui est trop gros."""

    with pytest.raises(ValueError, match="Liste"):
        sync_answers(database_file, {"id": "x"}, NOW)

    with pytest.raises(ValueError, match="au plus"):
        sync_answers(database_file, [{}] * (MAX_SYNC_ANSWERS + 1), NOW)


def test_mobile_token_is_created_checked_and_renewed(database_file):
    """Vérifie le jeton : absent, valide, puis remplacé."""

    assert get_mobile_token(database_file) is None
    assert not check_mobile_token(database_file, "")

    vFirst = renew_mobile_token(database_file)

    assert check_mobile_token(database_file, vFirst)

    vSecond = renew_mobile_token(database_file)

    assert not check_mobile_token(database_file, vFirst)
    assert check_mobile_token(database_file, vSecond)


def test_connection_qr_code_in_svg_and_png():
    """Vérifie le QR code de connexion, en SVG pour le web et en PNG pour le PC."""

    vSvg = build_connection_svg("http://192.168.1.80:8000/api/v1", "secret")
    vPng = build_connection_png("http://192.168.1.80:8000/api/v1", "secret")

    assert vSvg.startswith("<svg") and "secret" not in vSvg
    assert vPng.startswith(b"\x89PNG")


def test_progress_lists_themes_of_current_applications(database_file):
    """Vérifie les thèmes à revoir pour une candidature en cours, pas pour les autres."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Développeur Java Spring",
                    "company": "Acme",
                    "skills": ["Java", "Spring"],
                },
                {"source": "lever", "source_id": "2", "title": "Comptable"},
            ]
        ),
        NOW,
    )
    save_application(database_file, "lever", "1", "INTERVIEW", pNow=NOW)
    save_application(database_file, "lever", "2", "APPLIED", pNow=NOW)

    vApplications = build_progress(database_file, NOW)["applications"]

    assert len(vApplications) == 1
    assert vApplications[0]["status"] == "Entretien"
    assert "java" in vApplications[0]["themes"]
