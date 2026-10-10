"""Tests du tableau de bord web"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from storage.job_offers import save_offers
from web.app import (
    app,
    build_bar_chart,
    build_pie,
    format_euros,
    get_database_file,
    render_icon,
    safe_url,
)


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

    vResponse = client.get("/offers")

    assert vResponse.status_code == 200
    assert '<form class="filters' in vResponse.text
    assert "3 offres" in vResponse.text
    assert "Nouvelle" in vResponse.text


def test_list_offers_filters_by_search_and_contract(client):
    """Vérifie l'application des filtres de recherche et de contrat."""

    vResponse = client.get("/offers", params={"q": "java", "contract": "CDD"})

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

    vResponse = client.get("/offers", params=pParams)

    assert "1 offre" in vResponse.text
    assert pExpected in vResponse.text


def test_list_offers_ignores_invalid_values(client):
    """Vérifie qu'une saisie invalide n'empêche pas l'affichage."""

    vResponse = client.get(
        "/offers", params={"min_salary": "abc", "source": "inconnue", "contract": "X"}
    )

    assert vResponse.status_code == 200
    assert "3 offres" in vResponse.text


def test_list_offers_returns_table_for_htmx(client):
    """Vérifie qu'une requête HTMX ne reçoit que le tableau."""

    vResponse = client.get("/offers", headers={"HX-Request": "true"})

    assert "<table" in vResponse.text
    assert "<form" not in vResponse.text


def test_list_offers_escapes_untrusted_content(client):
    """Vérifie que le contenu des sources ne peut pas injecter de script."""

    vResponse = client.get("/offers")

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

    assert format_euros(2187.6) == "2\u202f188 €"
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

    vList = client.get("/offers", params={"status": "APPLIED"})

    assert "1 offre" in vList.text
    assert "Postulé" in vList.text


def test_update_application_without_status_deletes_tracking(client):
    """Vérifie qu'un statut vide supprime le suivi."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "IGNORED"},
    )

    assert "2 offres" in client.get("/offers").text

    client.post(
        "/offer/application", data={"source": "adzuna", "id": "new", "status": ""}
    )

    assert "3 offres" in client.get("/offers").text


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

    vResponse = client.get("/offers", params={"status": "FOLLOW_UP"})

    assert "1 offre" in vResponse.text
    assert "Relance le 01/01/2020" in vResponse.text


def test_dashboard_shows_statistics(client):
    """Vérifie le tableau de bord : indicateurs, graphique et menu actif."""

    vResponse = client.get("/")

    assert vResponse.status_code == 200
    assert "Tableau de bord" in vResponse.text
    assert "Offres actives en base" in vResponse.text
    assert 'class="chart chart-dense"' in vResponse.text
    assert "Candidatures" in vResponse.text
    assert 'aria-current="page"' in vResponse.text
    assert "Aucune recherche lancée pour le moment." in vResponse.text


def test_history_page(client):
    """Vérifie que l'historique s'affiche, même vide."""

    vResponse = client.get("/history")

    assert vResponse.status_code == 200
    assert "Taux de réussite" in vResponse.text
    assert "built-in" not in vResponse.text
    assert "Aucune exécution enregistrée pour le moment." in vResponse.text


def test_settings_page_never_shows_secret_values(client, monkeypatch):
    """Vérifie que seuls les noms des variables manquantes sont affichés."""

    monkeypatch.setenv("JOOBLE_API_KEY", "valeur-secrete")
    monkeypatch.delenv("LEVER_SITE", raising=False)

    vResponse = client.get("/settings")

    assert vResponse.status_code == 200
    assert "LEVER_SITE" in vResponse.text
    assert "valeur-secrete" not in vResponse.text


def test_assets_are_served(client):
    """Vérifie la mise à disposition du logo partagé avec l'interface de bureau."""

    vResponse = client.get("/assets/logo.png")

    assert vResponse.status_code == 200
    assert vResponse.headers["content-type"] == "image/png"


@pytest.mark.parametrize("pName", ["../logo", "inconnue", "House", "house.svg"])
def test_render_icon_rejects_unknown_names(pName):
    """Vérifie qu'un nom hors du dossier d'icônes ne produit rien."""

    assert render_icon(pName) == ""


def test_render_icon_sets_size():
    """Vérifie l'insertion d'une icône à la taille demandée."""

    vIcon = render_icon("house", 20)

    assert vIcon.startswith('<svg aria-hidden="true"')
    assert 'width="20"' in vIcon


def test_build_bar_chart_uses_a_common_scale():
    """Vérifie que les séries partagent la même échelle, sans barre nulle."""

    vChart = build_bar_chart(
        ["09/10", "10/10"],
        [("Offres", "#3B82F6", [0, 40]), ("Candidatures", "#F59E0B", [10, 4])],
    )

    assert [vBar["height"] for vBar in vChart["series"][0]["bars"]] == [2, 100]
    assert [vBar["height"] for vBar in vChart["series"][1]["bars"]] == [25, 10]


def test_build_pie_builds_conic_gradient():
    """Vérifie les segments du camembert et leur couleur."""

    vPie = build_pie(
        [
            {"label": "Adzuna", "count": 3, "percent": 75},
            {"label": "Jooble", "count": 1, "percent": 25},
        ]
    )

    assert vPie["total"] == 4
    assert vPie["gradient"] == (
        "conic-gradient(#3B82F6 0.00% 75.00%, #F59E0B 75.00% 100.00%)"
    )
    assert build_pie([])["gradient"] == ""


def test_unknown_offer_renders_error_page(client):
    """Vérifie qu'une offre introuvable affiche une page du site, pas du JSON."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "inconnue"})

    assert vResponse.status_code == 404
    assert "Page introuvable" in vResponse.text
    assert "Offre introuvable" in vResponse.text


def test_build_bar_chart_with_independent_scales():
    """Vérifie qu'une série de faibles valeurs garde des barres visibles."""

    vChart = build_bar_chart(
        ["09/10", "10/10"],
        [("Offres", "#3B82F6", [0, 500]), ("Relances", "#8B5CF6", [1, 2])],
        pIndependentScales=True,
    )

    assert [vBar["height"] for vBar in vChart["series"][1]["bars"]] == [50, 100]


def test_settings_are_saved_from_the_form(client):
    """Vérifie l'enregistrement des règles de calcul depuis le formulaire."""

    vResponse = client.post(
        "/settings",
        data={
            "net_salary_percent": "80",
            "income_tax_rate": "0",
            "new_offer_days": "5",
            "follow_up_days": "10",
        },
    )

    assert vResponse.status_code == 200
    assert "Règles enregistrées" in vResponse.text
    assert 'name="follow_up_days" value="10"' in vResponse.text


def test_settings_form_rejects_invalid_values(client):
    """Vérifie qu'une valeur hors bornes est refusée sans rien enregistrer."""

    vResponse = client.post("/settings", data={"new_offer_days": "0"})

    assert vResponse.status_code == 400
    assert "Nouvelle offre : valeur attendue entre 1 et 30" in vResponse.text


def test_legal_page(client):
    """Vérifie la page des mentions légales et le lien vers la licence."""

    vResponse = client.get("/legal")

    assert vResponse.status_code == 200
    assert "Données personnelles" in vResponse.text
    assert "/blob/main/LICENSE" in vResponse.text
    assert "linkedin.com/in/" in vResponse.text


@pytest.mark.parametrize(
    "pPath",
    [
        "/assets/../config.py",
        "/assets/%2e%2e/config.py",
        "/static/..%2f..%2fconfig.py",
        "/assets/icons/../../.env",
    ],
)
def test_static_files_refuse_path_traversal(client, pPath):
    """Vérifie qu'aucun fichier hors des dossiers publics n'est servi."""

    vResponse = client.get(pPath)

    assert vResponse.status_code == 404
    assert "APPLICATION_NAME" not in vResponse.text
