"""Tests de l'API JSON de l'application mobile"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from job.mobile_sync import renew_mobile_token
from job.quiz import load_active_quiz
from job.quiz_exam import load_exam_results
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import save_offers, set_availability
from storage.settings_repository import save_json_setting
from web.app import app, get_database_file


@pytest.fixture
def api(tmp_path):
    """Fournit un client sans session et le jeton de l'application mobile."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vToken = renew_mobile_token(vDatabaseFile)

    app.dependency_overrides[get_database_file] = lambda: vDatabaseFile

    with TestClient(app) as rClient:
        rClient.headers["Authorization"] = f"Bearer {vToken}"

        yield rClient

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "pAuthorization", [None, "Bearer mauvais", "Basic xyz", "Bearer"]
)
def test_api_requires_the_token(api, pAuthorization):
    """Vérifie le refus sans jeton valide, et sans redirection vers la connexion."""

    if pAuthorization is None:
        del api.headers["Authorization"]
    else:
        api.headers["Authorization"] = pAuthorization

    vResponse = api.get("/api/v1/quiz", follow_redirects=False)

    assert vResponse.status_code == 401
    assert vResponse.headers["www-authenticate"] == "Bearer"


def test_api_quiz_download_uses_its_version(api):
    """Vérifie le téléchargement du contenu puis la réponse 304 s'il n'a pas changé."""

    vResponse = api.get("/api/v1/quiz")

    assert vResponse.status_code == 200
    assert vResponse.json()["questions"]

    vETag = vResponse.headers["etag"]

    assert api.get("/api/v1/quiz", headers={"If-None-Match": vETag}).status_code == 304


def test_api_answers_sync_and_progress(api):
    """Vérifie l'envoi des réponses faites hors ligne et la progression renvoyée."""

    vAnswer = {
        "id": "telephone-0001",
        "question_id": "sql-null",
        "choice": 1,
        "answered_at": datetime.now().isoformat(),
    }

    vResponse = api.post("/api/v1/answers", json={"answers": [vAnswer, vAnswer]})
    vResult = vResponse.json()

    assert vResponse.status_code == 200
    assert (vResult["added"], vResult["duplicates"]) == (1, 1)
    assert vResult["progress"]["statistics"]["answers"] == 1
    assert "sql-null" in api.get("/api/v1/progress").json()["questions"]

    vTooMany = api.post("/api/v1/answers", json={"answers": [vAnswer] * 501})

    assert vTooMany.status_code == 400


def test_api_ping_answers_without_token(api):
    """Vérifie que le serveur se signale sans jeton, et sans aucune donnée."""

    del api.headers["Authorization"]

    vResponse = api.get("/api/v1/ping")

    assert vResponse.status_code == 200
    assert vResponse.json() == {"application": "JobBoard Perso", "api_version": 1}


def test_exams_and_flags_from_the_phone(api, tmp_path):
    """Vérifie l'ajout des examens sans doublon et le retrait des questions signalées."""

    vDatabaseFile = tmp_path / "scraper.db"
    vExam = {
        "title": "Examen blanc · tous thèmes",
        "finished_at": "2026-10-21T18:30:00",
        "correct": 15,
        "count": 20,
        "seconds": 900,
    }

    vFirst = api.post("/api/v1/exams", json={"exams": [vExam]})
    vAgain = api.post("/api/v1/exams", json={"exams": [vExam]})
    vWrong = api.post("/api/v1/exams", json={"exams": [{**vExam, "correct": 30}]})

    assert vFirst.json() == {"received": 1, "added": 1}
    assert vAgain.json() == {"received": 1, "added": 0}
    assert vWrong.status_code == 400
    assert load_exam_results(vDatabaseFile)[0]["score"] == 75

    vQuestionId = load_active_quiz(vDatabaseFile)["sql"]["questions"][0]["id"]
    vFlags = api.post("/api/v1/flags", json={"question_ids": [vQuestionId, "inconnue"]})

    assert vFlags.json() == {"received": 2, "flagged": 1}
    assert vQuestionId not in {
        vQuestion["id"]
        for vQuestion in load_active_quiz(vDatabaseFile)["sql"]["questions"]
    }


def test_offers_and_status_changes_from_the_phone(api, tmp_path):
    """Vérifie la liste des nouvelles offres et les statuts donnés depuis le téléphone."""

    vDatabaseFile = tmp_path / "scraper.db"
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Technicien de maintenance",
                }
            ]
        ),
        datetime.now(),
    )

    vOffers = api.get("/api/v1/offers").json()["offers"]

    assert vOffers[0]["title"] == "Technicien de maintenance"
    assert vOffers[0]["status"] is None

    vReport = api.post(
        "/api/v1/applications",
        json={
            "changes": [
                {"source": "lever", "source_id": "1", "status": "APPLIED"},
                {"source": "lever", "source_id": "absente", "status": "APPLIED"},
                {"source": "lever", "source_id": "1", "status": "ACCEPTED"},
            ]
        },
    ).json()

    assert vReport == {"applied": 1, "rejected": ["lever/absente", "lever/1"]}
    assert get_application(vDatabaseFile, "lever", "1")["status"] == "APPLIED"

    # Une candidature suivie garde ses notes et sa date d'entretien.
    save_application(
        vDatabaseFile,
        "lever",
        "1",
        "APPLIED",
        pNotes="Contact : la RH",
        pInterviewAt=datetime(2026, 11, 3, 10),
    )
    api.post(
        "/api/v1/applications",
        json={"changes": [{"source": "lever", "source_id": "1", "status": "IGNORED"}]},
    )
    vApplication = get_application(vDatabaseFile, "lever", "1")

    assert vApplication["status"] == "IGNORED"
    assert vApplication["notes"] == "Contact : la RH"
    assert vApplication["interview_at"] == "2026-11-03T10:00"


def test_quick_notes_from_the_phone(api, tmp_path):
    """Vérifie les notes rapides : ajoutées datées, sans doublon, refus expliqués."""

    vDatabaseFile = tmp_path / "scraper.db"
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "1", "title": "Dev"}]),
        datetime.now(),
    )
    save_application(vDatabaseFile, "lever", "1", "APPLIED", pNotes="Contact : la RH")
    vWrittenAt = datetime.now().replace(second=0, microsecond=0)
    vNote = {
        "source": "lever",
        "source_id": "1",
        "text": "  Rappel   reçu, entretien à caler ",
        "written_at": vWrittenAt.isoformat(),
    }

    vReport = api.post(
        "/api/v1/notes",
        json={
            "notes": [
                vNote,
                vNote,
                {**vNote, "source_id": "absente"},
                {**vNote, "text": " "},
                {**vNote, "written_at": "hier"},
            ]
        },
    ).json()
    vApplication = get_application(vDatabaseFile, "lever", "1")

    assert vReport["applied"] == 2
    assert vReport["rejected"] == [
        "lever/absente : offre inconnue",
        "note vide ou de plus de 1000 caractères",
        "date de note illisible",
    ]
    assert vApplication["status"] == "APPLIED"
    assert vApplication["notes"] == (
        "Contact : la RH\n"
        f"[{vWrittenAt:%d/%m/%Y %H:%M}, téléphone] Rappel reçu, entretien à caler"
    )
    assert api.post("/api/v1/notes", json={"notes": "x"}).status_code == 422


def test_tracking_lists_applications_and_interview_sheets(api, tmp_path):
    """Vérifie les candidatures envoyées au téléphone et la fiche de l'entretien."""

    vDatabaseFile = tmp_path / "scraper.db"
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Dev",
                    "company": "Acme",
                },
                {"source": "lever", "source_id": "2", "title": "Data"},
            ]
        ),
        datetime.now(),
    )
    save_application(
        vDatabaseFile,
        "lever",
        "1",
        "INTERVIEW",
        pInterviewAt=datetime.now() + timedelta(days=2),
    )
    save_application(vDatabaseFile, "lever", "2", "INTERESTED")

    vTracking = api.get("/api/v1/tracking").json()

    assert [vItem["status_label"] for vItem in vTracking["applications"]] == [
        "Entretien",
        "Intéressé",
    ]
    assert list(vTracking["sheets"]) == ["lever/1"]
    assert vTracking["sheets"]["lever/1"]["title"] == "Dev"


def test_replies_are_sent_to_the_phone(api, tmp_path):
    """Vérifie les réponses gardées par la dernière lecture, transmises au téléphone."""

    save_json_setting(
        app.dependency_overrides[get_database_file](),
        "pending_replies",
        [{"id": "abc", "title": "Dev", "company": "Kiabi", "status": "INTERVIEW"}],
    )

    assert api.get("/api/v1/replies").json()["replies"][0]["company"] == "Kiabi"


def test_coming_interviews_are_sent_to_the_phone(api):
    """Vérifie les entretiens des sept prochains jours transmis au téléphone."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [{"source": "lever", "source_id": "1", "title": "Dev", "company": "Kiabi"}]
        ),
        datetime.now(),
    )
    save_application(
        vDatabaseFile,
        "lever",
        "1",
        "INTERVIEW",
        pInterviewAt=datetime.now() + timedelta(days=2),
    )

    vInterviews = api.get("/api/v1/interviews").json()["interviews"]

    assert [(vItem["company"], vItem["title"]) for vItem in vInterviews] == [
        ("Kiabi", "Dev")
    ]


def test_withdrawn_offers_are_sent_to_the_phone(api):
    """Vérifie les offres suivies retirées transmises au téléphone."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "1", "title": "Dev"}]),
        datetime.now(),
    )
    save_application(vDatabaseFile, "lever", "1", "APPLIED")
    set_availability(vDatabaseFile, "lever", "1", "expired", datetime.now())

    assert api.get("/api/v1/withdrawn").json()["offers"][0]["title"] == "Dev"


def test_game_gives_level_streak_and_quests(api):
    """Vérifie la progression envoyée au téléphone, avec le jeton seulement."""

    vGame = api.get("/api/v1/game").json()

    assert (vGame["level"], vGame["title"], vGame["xp"]) == (1, "Apprenti", 0)
    assert len(vGame["quests"]) == 4
    assert api.get("/api/v1/game", headers={"Authorization": ""}).status_code == 401


def test_labs_are_downloaded_and_results_replayed(api):
    """Vérifie le contenu des simulations envoyé, puis une partie rejouée par le PC."""

    vPackage = api.get("/api/v1/labs").json()
    vScenario = vPackage["troubleshooting"]["scenarios"][0]
    vRight = next(vCause for vCause in vScenario["causes"] if vCause.get("right"))
    vResult = {
        "id": "partie-api",
        "lab": "troubleshooting",
        "scenario": vScenario["id"],
        "actions": [f"repair:{vRight['id']}"],
        "finished_at": "2026-10-30T09:00:00",
    }

    assert vPackage["troubleshooting"]["rules"]["unproven_score"] == 50
    assert api.post("/api/v1/labs", json={"results": [vResult]}).json()["saved"] == 1
    assert api.post("/api/v1/labs", json={"results": "rien"}).status_code == 422
