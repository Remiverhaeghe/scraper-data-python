"""Tests de l'API de la simulation d'entretien et de l'auto-évaluation"""

from job.interview_simulation import get_history, get_weak_questions
from job.profile import load_profile
from tests.web.test_api import api  # noqa: F401  pylint: disable=unused-import

API_PREFIX = "/api/v1"


def test_interview_questions_and_phone_series(api, tmp_path):
    """Vérifie les questions envoyées et les séries reçues du téléphone."""

    vClient = api
    vContent = vClient.get(f"{API_PREFIX}/interview").json()
    vQuestion = vContent["questions"][0]

    assert "Java" in vContent["themes"]
    assert vQuestion["points"]

    vReport = vClient.post(
        f"{API_PREFIX}/interview",
        json={
            "series": [
                {
                    "theme": "Java",
                    "finished_at": "2026-10-23T18:00:00",
                    "results": [
                        {"question_id": vQuestion["id"], "checked": [0, 99, True]},
                        {"question_id": "inconnue", "checked": [0]},
                    ],
                },
                {"theme": "Java", "results": []},
                "illisible",
            ]
        },
    ).json()

    vDatabaseFile = tmp_path / "scraper.db"

    assert vReport == {"received": 3, "recorded": 1}
    assert get_history(vDatabaseFile)[0]["theme"] == "Java"
    assert [vItem["id"] for vItem in get_weak_questions(vDatabaseFile)] == [
        vQuestion["id"]
    ]
    assert (
        vClient.post(f"{API_PREFIX}/interview", json={"series": [{}] * 21}).status_code
        == 400
    )


def test_skill_grid_is_read_and_saved_from_the_phone(api, tmp_path):
    """Vérifie la grille envoyée au téléphone et les niveaux reçus."""

    vClient = api
    vGrid = vClient.get(f"{API_PREFIX}/skills").json()

    assert vGrid["known_level"] == 5
    assert {"skill": "Java", "level": 0} in vGrid["grid"]

    vSaved = vClient.post(f"{API_PREFIX}/skills", json={"levels": {"Java": 8}})

    assert vSaved.json() == {"rated": 1}
    assert load_profile(tmp_path / "scraper.db")["skill_levels"] == {"Java": 8}

    for vLevels in ({"Java": "8"}, {"Java": 11}):
        assert (
            vClient.post(f"{API_PREFIX}/skills", json={"levels": vLevels}).status_code
            == 400
        )
