"""Tests web des trajets estimés, de la relecture des lettres et du bilan du mois"""

from datetime import datetime

from storage.job_applications import save_application
from storage.settings_repository import save_json_setting
from web.app import app, get_database_file
from web.routes.offers import build_map_points


def test_map_points_carry_travel_estimates():
    """Vérifie que chaque pastille de la carte porte les trajets estimés."""

    vPoints = build_map_points(
        [
            {
                "source": "adzuna",
                "source_id": "1",
                "title": "Dev",
                "latitude": 50.6,
                "longitude": 3.1,
                "drive_minutes": 20,
                "bike_minutes": 50,
            },
            {"source": "adzuna", "source_id": "2", "latitude": 50.7, "longitude": 3.2},
        ]
    )

    assert vPoints[0]["travel"] == "≈ 20 min en voiture · ≈ 50 min à vélo"
    assert vPoints[1]["travel"] == ""


def test_map_page_explains_the_speeds(client):
    """Vérifie la note des vitesses sur la carte, réglées dans les Paramètres."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()

    assert "Trajets estimés hors ligne" not in client.get("/offers?view=map").text

    save_json_setting(
        vDatabaseFile,
        "home_location",
        {"label": "Ville fictive", "latitude": 50.63, "longitude": 3.06},
    )
    client.post(
        "/settings",
        data={"car_city_speed_kmh": "35", "bike_speed_kmh": "20"},
    )

    vPage = client.get("/offers?view=map").text

    assert "Trajets estimés hors ligne" in vPage
    assert "35 km/h en ville" in vPage
    assert "20 km/h à vélo" in vPage
    assert "Ce sont des estimations" in vPage


def test_letter_review_lists_length_keywords_and_mistakes(client):
    """Vérifie la relecture de la lettre depuis la fiche de l'offre."""

    vResponse = client.post(
        "/offer/letter/review",
        data={
            "source": "adzuna",
            "id": "new",
            "letter": "Je me permet de postuler chez [Entreprise] en Python.",
        },
    )

    assert vResponse.status_code == 200
    assert "un peu court" in vResponse.text
    assert 'ython, <span class="muted">présent</span>' in vResponse.text
    assert "Je me permets" in vResponse.text
    assert "Reste du modèle" in vResponse.text

    vEmpty = client.post(
        "/offer/letter/review", data={"source": "adzuna", "id": "new", "letter": ""}
    )

    assert "Lettre vide." in vEmpty.text
    assert "Aucune faute courante" not in vEmpty.text
    assert (
        client.post(
            "/offer/letter/review", data={"source": "adzuna", "id": "absente"}
        ).status_code
        == 404
    )


def test_offer_page_has_the_review_button(client):
    """Vérifie le bouton de relecture sous le brouillon de lettre."""

    client.post("/profile", data={"skills": "Python"})

    vPage = client.get("/offer?source=adzuna&id=new").text

    assert "Relire la lettre" in vPage
    assert 'id="letter-review"' in vPage


def test_monthly_report_shows_average_delay(client):
    """Vérifie le délai moyen de réponse sur le récapitulatif du mois."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    vMonth = datetime.now().strftime("%Y-%m")

    assert (
        "aucune réponse reçue"
        in client.get(f"/applications/france-travail?month={vMonth}").text
    )

    vStart = datetime.now().replace(day=1, hour=8)
    save_application(vDatabaseFile, "adzuna", "new", "APPLIED", pNow=vStart)
    save_application(vDatabaseFile, "adzuna", "new", "REJECTED", pNow=vStart)

    vPage = client.get(f"/applications/france-travail?month={vMonth}").text

    assert "Délai moyen de réponse des recruteurs ce mois-ci : 0 jour." in vPage
