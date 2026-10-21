"""Tests de l'API JSON de l'application mobile"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from job.mobile_sync import renew_mobile_token
from storage.database import initialize_database
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
