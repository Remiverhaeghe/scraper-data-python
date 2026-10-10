"""Tests du tableau de bord web"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from storage.job_offers import save_offers
from web.app import app, format_euros, get_database_file, safe_url


def build_offer(pSourceId, **pValues):
    """Construit une offre au format commun avec quelques valeurs par défaut."""

    rOffer = {
        "source": "adzuna",
        "source_id": pSourceId,
        "title": f"Développeur Python {pSourceId}",
        "company": "Entreprise A",
        "location": "Lille",
        "url": f"https://www.adzuna.fr/details/{pSourceId}",
        "contract": "CDI",
        "description": "Développement d'API",
    }

    rOffer.update(pValues)

    return rOffer


@pytest.fixture
def client(tmp_path):
    """Fournit un client de test branché sur une base temporaire remplie."""

    vDatabaseFile = tmp_path / "scraper.db"

    app.dependency_overrides[get_database_file] = lambda: vDatabaseFile

    with TestClient(app) as rClient:
        save_offers(
            vDatabaseFile,
            pd.DataFrame(
                [
                    build_offer(
                        "old",
                        title="Développeur Java",
                        contract="CDD",
                        salary_net_monthly_min=2000,
                    )
                ]
            ),
            datetime.now() - timedelta(days=30),
        )

        save_offers(
            vDatabaseFile,
            pd.DataFrame(
                [
                    build_offer(
                        "new",
                        remote=True,
                        salary_net_monthly_min=3000,
                        has_13th_month=True,
                        skills='["python", "django"]',
                    ),
                    build_offer(
                        "xss",
                        source="hackernews",
                        title="<script>alert(1)</script>",
                        url="javascript:alert(1)",
                    ),
                ]
            ),
            datetime.now(),
        )

        yield rClient

    app.dependency_overrides.clear()


def test_list_offers_displays_all_offers(client):
    """Vérifie l'affichage de la page complète des offres."""

    vResponse = client.get("/")

    assert vResponse.status_code == 200
    assert '<form class="filters"' in vResponse.text
    assert "3 offres" in vResponse.text
    assert "Nouvelle" in vResponse.text


def test_list_offers_filters_by_search_and_contract(client):
    """Vérifie l'application des filtres de recherche et de contrat."""

    vResponse = client.get("/", params={"q": "java", "contract": "CDD"})

    assert "1 offre" in vResponse.text
    assert "Développeur Java" in vResponse.text


@pytest.mark.parametrize(
    "pParams, pExpected",
    [
        ({"remote": "1"}, "Développeur Python new"),
        ({"min_salary": "2 500"}, "Développeur Python new"),
        ({"new": "1", "source": "adzuna"}, "Développeur Python new"),
    ],
)
def test_list_offers_filters(client, pParams, pExpected):
    """Vérifie les filtres télétravail, salaire et nouveauté."""

    vResponse = client.get("/", params=pParams)

    assert "1 offre" in vResponse.text
    assert pExpected in vResponse.text


def test_list_offers_ignores_invalid_values(client):
    """Vérifie qu'une saisie invalide n'empêche pas l'affichage."""

    vResponse = client.get(
        "/", params={"min_salary": "abc", "source": "inconnue", "contract": "X"}
    )

    assert vResponse.status_code == 200
    assert "3 offres" in vResponse.text


def test_list_offers_returns_table_for_htmx(client):
    """Vérifie qu'une requête HTMX ne reçoit que le tableau."""

    vResponse = client.get("/", headers={"HX-Request": "true"})

    assert "<table" in vResponse.text
    assert "<form" not in vResponse.text


def test_list_offers_escapes_untrusted_content(client):
    """Vérifie que le contenu des sources ne peut pas injecter de script."""

    vResponse = client.get("/")

    assert "<script>alert(1)</script>" not in vResponse.text
    assert "&lt;script&gt;" in vResponse.text
    assert "javascript:alert" not in vResponse.text


def test_show_offer(client):
    """Vérifie l'affichage de la fiche détaillée d'une offre."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "new"})

    assert vResponse.status_code == 200
    assert "Voir l'offre sur Adzuna" in vResponse.text
    assert "https://www.adzuna.fr/details/new" in vResponse.text
    assert "13e mois" in vResponse.text
    assert "python, django" in vResponse.text


def test_show_offer_not_found(client):
    """Vérifie la réponse pour une offre inconnue."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "inconnue"})

    assert vResponse.status_code == 404


def test_format_euros():
    """Vérifie le format français des montants."""

    assert format_euros(2187.6) == "2 188 €"
    assert format_euros(None) == ""


@pytest.mark.parametrize(
    "pUrl, pExpected",
    [
        ("https://example.com/job", "https://example.com/job"),
        ("javascript:alert(1)", "#"),
        ("JaVaScRiPt:alert(1)", "#"),
        (None, "#"),
    ],
)
def test_safe_url(pUrl, pExpected):
    """Vérifie que seules les URL http et https sont conservées."""

    assert safe_url(pUrl) == pExpected


def test_show_offer_displays_application_form(client):
    """Vérifie la présence du formulaire de suivi sur la fiche."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "new"})

    assert "Aucun suivi" in vResponse.text
    assert 'name="follow_up_date"' in vResponse.text


def test_update_application_saves_status_and_notes(client):
    """Vérifie l'enregistrement d'un statut et de notes."""

    vResponse = client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": "",
            "notes": "Envoyée via le site",
        },
    )

    assert vResponse.status_code == 200
    assert "Suivi enregistré" in vResponse.text
    assert "Envoyée via le site" in vResponse.text
    assert "Candidature envoyée le" in vResponse.text
    assert "relancé aujourd" in vResponse.text

    vList = client.get("/", params={"status": "APPLIED"})

    assert "1 offre" in vList.text
    assert "Postulé" in vList.text


def test_update_application_without_status_deletes_tracking(client):
    """Vérifie qu'un statut vide supprime le suivi."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "IGNORED"},
    )

    assert "2 offres" in client.get("/").text

    client.post(
        "/offer/application", data={"source": "adzuna", "id": "new", "status": ""}
    )

    assert "3 offres" in client.get("/").text


def test_update_application_rejects_unknown_values(client):
    """Vérifie le refus d'un statut ou d'une offre inconnus."""

    vBadStatus = client.post(
        "/offer/application", data={"source": "adzuna", "id": "new", "status": "HACK"}
    )
    vUnknownOffer = client.post(
        "/offer/application", data={"source": "adzuna", "id": "x", "status": "APPLIED"}
    )

    assert vBadStatus.status_code == 400
    assert vUnknownOffer.status_code == 404


def test_add_follow_up(client):
    """Vérifie l'enregistrement d'une relance."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "APPLIED"},
    )

    vResponse = client.post("/offer/follow-up", data={"source": "adzuna", "id": "new"})

    assert "Relance enregistrée" in vResponse.text
    assert "1 relance" in vResponse.text


def test_add_follow_up_requires_tracking(client):
    """Vérifie qu'une relance exige un suivi existant."""

    vResponse = client.post("/offer/follow-up", data={"source": "adzuna", "id": "new"})

    assert vResponse.status_code == 400


def test_list_offers_shows_follow_ups_due(client):
    """Vérifie le filtre des candidatures à relancer."""

    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": "2020-01-01",
        },
    )

    vResponse = client.get("/", params={"status": "FOLLOW_UP"})

    assert "1 offre" in vResponse.text
    assert "Relance le 01/01/2020" in vResponse.text
