"""Tests du tableau de bord web"""

import io
import json
import re
import zipfile
from datetime import datetime, timedelta

import pandas as pd
import pytest
import requests
from fastapi.testclient import TestClient

import web.app as web_app
import web.rendering as web_rendering
import storage.backup as storage_backup
import web.routes.applications as web_applications
import web.routes.offers as web_offers
import web.routes.settings as web_settings
import job.quiz_packs as quiz_packs

from job.education import save_education_levels
from job.schedule import (
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from job.profile import build_profile, save_profile
from job.challenges import get_expected_answers, get_seed
from job.quiz_import import import_questions, import_questions_file
from tools.quiz_lot import build_pack as build_lot_pack
from tests.job.test_quiz_types import NUMERIC, ORDER, PAIRS
from job.quiz_generation import MIN_QUALITY_SAMPLE
from job.settings import load_settings, save_settings
from storage.backup import backup_database, copy_to_nas
from storage.job_applications import get_application
from storage.job_offers import get_offer, save_offers, set_availability
from tests.job.test_quiz_import import build_pack
from tools.quiz_lot import build_pack as build_lot_pack
from tests.job.test_quiz_generation import build_lot_text, build_question
from web.app import app, get_database_file
from job.geocoding import HOME_KEY
from storage.geo_cache import save_offer_positions
from storage.settings_repository import save_json_setting
from web.rendering import (
    build_bar_chart,
    build_pie,
    format_euros,
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
def client(tmp_path, web_login):
    """Fournit un client connecté, branché sur une base temporaire remplie."""

    vDatabaseFile = tmp_path / "scraper.db"

    app.dependency_overrides[get_database_file] = lambda: vDatabaseFile

    with TestClient(app) as rClient:
        web_login(rClient)

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
            datetime.now() - timedelta(days=20),
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
    # Description française, entreprise sans pays connu : pas de traduction
    assert "Traduire en français" not in vResponse.text
    assert "Infos sur l'entreprise (France)</button>" in vResponse.text


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
    assert 'class="chart"' in vResponse.text
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
    assert "Comparaison des sources" in vResponse.text
    assert "<td>Hacker News</td>" in vResponse.text


def test_settings_page_never_shows_secret_values(client, monkeypatch):
    """Vérifie que seuls les noms des variables manquantes sont affichés."""

    monkeypatch.setenv("JOOBLE_API_KEY", "valeur-secrete")
    monkeypatch.delenv("GREENHOUSE_BOARD", raising=False)

    vResponse = client.get("/settings")

    assert vResponse.status_code == 200
    assert "Aucune entreprise suivie" in vResponse.text
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
    assert render_icon("trash-2", 16).startswith("<svg")


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
    assert vChart["scale"] == [
        {"value": 500, "color": "#3B82F6"},
        {"value": 2, "color": "#8B5CF6"},
    ]


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
    assert "Limitation de responsabilité" in vResponse.text
    assert "Remiverhaeghe" in vResponse.text
    assert 'href="/license"' in vResponse.text
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


def test_list_offers_new_filters(client):
    """Vérifie les filtres de salaire maximum, de salaire présent et de publication."""

    vResponse = client.get(
        "/offers", params={"max_salary": "1500", "has_salary": "1", "published": "7"}
    )

    assert vResponse.status_code == 200
    assert "0 offre" in vResponse.text


def test_list_offers_ignores_unknown_publication_period(client):
    """Vérifie qu'une période inconnue est ignorée plutôt que refusée."""

    vResponse = client.get("/offers", params={"published": "999"})

    assert vResponse.status_code == 200
    assert "3 offres" in vResponse.text


def test_license_is_shown_without_leaving_the_site(client):
    """Vérifie que la licence est affichée depuis le fichier du projet."""

    vResponse = client.get("/license")

    assert vResponse.status_code == 200
    assert "PolyForm Strict License 1.0.0" in vResponse.text
    assert "seul le texte anglais fait foi" in vResponse.text
    assert "Lucide Contributors" in vResponse.text


def test_settings_page_shows_schedule_without_email(client, tmp_path, monkeypatch):
    """Vérifie la planification affichée en lecture seule, sans l'adresse e-mail."""

    vDatabaseFile = tmp_path / "scraper.db"

    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    save_scheduled_search(vDatabaseFile, ["remotive"], {"keyword": "Kotlin"})
    save_schedule_options(vDatabaseFile, True, 12)
    save_notification_email(vDatabaseFile, "secret@example.com")

    vResponse = client.get("/settings")

    assert vResponse.status_code == 200
    assert "Kotlin" in vResponse.text
    assert "Toutes les 12 heures" in vResponse.text
    assert "Adresse renseignée" in vResponse.text
    assert "secret@example.com" not in vResponse.text
    assert "GMAIL_APP_PASSWORD" in vResponse.text


def test_logs_page_shows_filtered_entries(client, monkeypatch):
    """Vérifie l'affichage des logs filtrés, avec la trace d'erreur au survol."""

    vCalls = []

    def fake_read(pLevel=None, pSearch=None):
        vCalls.append((pLevel, pSearch))

        return [
            {
                "time": "2026-10-10 09:00:00",
                "level": "ERROR",
                "level_label": "Erreur",
                "module": "web.app",
                "message": "Erreur <b>inattendue</b>\nTraceback détaillé",
            }
        ]

    monkeypatch.setattr("web.routes.monitoring.read_log_entries", fake_read)

    vResponse = client.get("/logs?level=ERROR&search=%20web%20")

    assert vResponse.status_code == 200
    assert vCalls == [("ERROR", "web")]
    assert "tone-danger" in vResponse.text
    assert "Erreur &lt;b&gt;inattendue&lt;/b&gt;" in vResponse.text
    assert "<b>inattendue</b>" not in vResponse.text


def test_logs_page_ignores_unknown_level(client, monkeypatch):
    """Vérifie qu'un niveau inconnu revient à afficher tous les logs."""

    vCalls = []

    monkeypatch.setattr(
        "web.routes.monitoring.read_log_entries",
        lambda pLevel=None, pSearch=None: vCalls.append(pLevel) or [],
    )

    vResponse = client.get("/logs?level=DEBUG")

    assert vResponse.status_code == 200
    assert vCalls == [None]
    assert "Aucune entrée ne correspond aux filtres." in vResponse.text


def test_reset_requires_confirmation(client):
    """Vérifie qu'une réinitialisation sans la case cochée ne change rien."""

    vResponse = client.post("/settings/reset", data={})

    assert vResponse.status_code == 400
    assert "Cochez la case de confirmation" in vResponse.text
    assert "Développeur Java" in client.get("/offers").text


def test_reset_backs_up_then_empties_data(client, tmp_path):
    """Vérifie la sauvegarde puis l'effacement des offres."""

    vResponse = client.post("/settings/reset", data={"confirm": "1"})

    assert vResponse.status_code == 200
    assert "Données réinitialisées. Sauvegarde : scraper-" in vResponse.text
    assert len(list((tmp_path / "backups").glob("scraper-*.db"))) == 1
    assert "Développeur Java" not in client.get("/offers").text


def test_logs_can_be_downloaded_and_cleared(client, monkeypatch):
    """Vérifie le téléchargement des journaux et leur remise à zéro protégée."""

    vCleared = []

    monkeypatch.setattr(
        "web.routes.monitoring.export_logs", lambda: "ligne de journal\n"
    )
    monkeypatch.setattr(
        "web.routes.monitoring.clear_logs", lambda: vCleared.append(True)
    )

    vDownload = client.get("/logs/download")

    assert vDownload.text == "ligne de journal\n"
    assert "attachment" in vDownload.headers["content-disposition"]

    vClear = client.post("/logs/clear", data={"confirm": "on"}, follow_redirects=False)

    assert vClear.status_code == 303
    assert vCleared == [True]


@pytest.mark.parametrize("pValues, pEmptyText", [([0, 0], "Vide"), ([1, 0], "")])
def test_build_bar_chart_empty_state_and_axes(pValues, pEmptyText):
    """Vérifie le texte d'état vide et les libellés d'axes transmis au gabarit."""

    vChart = build_bar_chart(
        ["a", "b"],
        [("Offres", "#000", pValues)],
        pAxes=("Jour", "Nombre"),
        pEmptyText="Vide",
    )

    assert vChart["empty_text"] == pEmptyText
    assert (vChart["x_axis"], vChart["y_axis"]) == ("Jour", "Nombre")


def test_quality_page_and_export(client):
    """Vérifie la page de qualité et le téléchargement des offres à vérifier."""

    vPage = client.get("/quality")
    vExport = client.get("/quality/export")

    assert vPage.status_code == 200
    assert "Remplissage global" in vPage.text
    assert "Aucune offre à vérifier." in vPage.text
    assert "tone-success" in vPage.text
    assert "Remplissage moyen" in vPage.text
    assert "Toutes sources" in vPage.text
    assert "attachment" in vExport.headers["content-disposition"]
    assert vExport.text.lstrip("﻿").startswith("source;source_id;problems")


def test_quality_purge_previews_then_deletes(client):
    """Vérifie l'aperçu, la confirmation exigée et la suppression des offres."""

    vShort = client.post("/quality/purge/preview", data={"words": "it"})
    vPreview = client.post("/quality/purge/preview", data={"words": "java, script"})
    vRefused = client.post("/quality/purge", data={"words": "java"})
    vDeleted = client.post(
        "/quality/purge", data={"words": "java", "confirm": "1", "exclude": "1"}
    )

    assert vShort.status_code == 400
    assert "Mots trop courts" in vShort.text
    assert "2 offre(s) seraient supprimées." in vPreview.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in vPreview.text
    assert vRefused.status_code == 400
    assert "1 offre(s) supprimée(s), sauvegarde" in vDeleted.text
    assert "2 offres" in client.get("/offers").text
    assert 'value="java"' in vDeleted.text
    assert (
        client.post("/quality/excluded-words", data={"words": "it"}).status_code == 400
    )
    assert "Mots exclus enregistrés." in (
        client.post("/quality/excluded-words", data={"words": ""}).text
    )


def test_offers_show_colored_badges(client):
    """Vérifie les badges de contrat et d'avantages, aux couleurs partagées."""

    vText = client.get("/offers").text

    assert 'badge-first badge-warning">CDD</span>' in vText
    assert 'badge badge-muted">13e mois</span>' in vText


def test_expired_offers_are_hidden_by_default(client, tmp_path):
    """Vérifie le masquage par défaut, le filtre et le badge des offres retirées."""

    set_availability(
        tmp_path / "scraper.db", "adzuna", "new", "expired", datetime.now()
    )

    vDefault = client.get("/offers").text
    vExpired = client.get("/offers?availability=expired").text

    assert "Développeur Python new" not in vDefault
    assert "Développeur Python new" in vExpired
    assert "Probablement expirée" in vExpired


@pytest.mark.parametrize(
    "pResult, pMessage, pSaved",
    [
        ("available", "toujours en ligne", "available"),
        (None, "n'a pas permis de conclure", None),
    ],
)
def test_check_availability(client, tmp_path, monkeypatch, pResult, pMessage, pSaved):
    """Vérifie le message renvoyé et l'enregistrement du seul résultat net."""

    monkeypatch.setattr("web.routes.offers.check_offer_link", lambda pUrl: pResult)

    vResponse = client.post(
        "/offer/availability", data={"source": "adzuna", "id": "new"}
    )

    assert pMessage in vResponse.text
    assert get_offer(tmp_path / "scraper.db", "adzuna", "new")["availability"] == pSaved


def test_duplicate_offers_are_grouped_and_decided(client, tmp_path):
    """Vérifie le regroupement, la comparaison sur la fiche et la décision."""

    vDatabaseFile = tmp_path / "scraper.db"

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer(
                    "dup1", title="Data Analyst", fingerprint="data|acme|lille"
                ),
                build_offer(
                    "dup2",
                    source="jooble",
                    title="Data Analyst",
                    contract="CDD",
                    fingerprint="data|acme|lille",
                ),
            ]
        ),
        datetime.now(),
    )

    vList = client.get("/offers?multiple=1").text
    vOffer = client.get("/offer?source=adzuna&id=dup1").text

    assert vList.count("Data Analyst") == 1
    assert "2 annonces" in vList
    assert "À valider" in vList
    assert "Annonces de cette offre" in vOffer
    assert "Différences : Contrat" in vOffer

    vResponse = client.post(
        "/offer/duplicates",
        data={"source": "adzuna", "id": "dup1", "decision": "separate"},
        follow_redirects=False,
    )

    assert vResponse.status_code == 303
    assert client.get("/offers").text.count("Data Analyst") == 2
    assert (
        client.post(
            "/offer/duplicates",
            data={"source": "adzuna", "id": "dup1", "decision": "autre"},
        ).status_code
        == 400
    )


def test_profile_page_and_offer_preparation(client):
    """Vérifie l'enregistrement du profil et la préparation affichée sur la fiche."""

    vEmpty = client.get("/offer?source=adzuna&id=new").text

    vSaved = client.post(
        "/profile",
        data={
            "skills": "Python, Django",
            "experiences": "Développeur | Python | Livré une API",
            "cv_variants": "CV Python | Python, Django",
        },
    )
    vOffer = client.get("/offer?source=adzuna&id=new").text

    assert "Renseignez d'abord vos compétences" in vEmpty
    assert "Profil enregistré : 2 compétence(s)" in vSaved.text
    assert "CV conseillé : <strong>CV Python</strong>" in vOffer
    assert "Brouillon de lettre de motivation" in vOffer
    assert "Pourquoi ce score ?" in vOffer
    assert client.post("/profile", data={"skills": "x" * 30000}).status_code == 400


def test_diploma_is_compared_to_the_offer(client):
    """Vérifie le diplôme du profil, son écart sur l'offre et le filtre « À ma portée »."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_education_levels(vDatabaseFile, [(7, "adzuna", "new")])

    client.post(
        "/profile",
        data={
            "skills": "Java",
            "diploma": "Bac pro MEI\nBTS Maintenance industrielle",
            "education_level": "",
        },
    )
    vProfile = client.get("/profile").text
    vOffer = client.get("/offer?source=adzuna&id=new").text
    vList = client.get("/offers").text
    vReachable = client.get("/offers?reach=1").text

    assert "Bac pro MEI\nBTS Maintenance industrielle</textarea>" in vProfile
    assert "Niveau retenu : Bac+2 (BTS, DUT)" in vProfile
    assert "Bac+5 (master, ingénieur) · Diplôme probablement bloquant" in vOffer
    assert "Diplôme demandé au-dessus du vôtre" in vList
    assert "Diplôme demandé au-dessus du vôtre" not in vReachable


def test_preparation_sheet_page(client):
    """Vérifie la fiche imprimable : lien depuis l'offre, contenu échappé, 404."""

    client.post(
        "/profile",
        data={
            "skills": "Python",
            "experiences": "Développeur | Python | Livré une API",
        },
    )

    vOffer = client.get("/offer?source=adzuna&id=new").text
    vSheet = client.get("/offer/sheet?source=adzuna&id=new")
    vXss = client.get("/offer/sheet?source=hackernews&id=xss").text

    assert "/offer/sheet?source=adzuna&amp;id=new" in vOffer
    assert vSheet.status_code == 200
    assert "Exemples à citer" in vSheet.text
    assert "Python : Développeur : Livré une API" in vSheet.text
    assert "<script>alert(1)</script>" not in vXss
    assert client.get("/offer/sheet?source=adzuna&id=absent").status_code == 404


def test_dashboard_shows_offers_close_to_retained_ones(client):
    """Vérifie la carte des offres proches d'une offre retenue."""

    assert "Offres proches de vos candidatures" not in client.get("/").text

    save_offers(
        app.dependency_overrides[get_database_file](),
        pd.DataFrame([build_offer("twin", title="Développeur Java senior")]),
        datetime.now(),
    )
    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "old", "status": "INTERESTED"},
    )
    vPage = client.get("/").text

    assert "Offres proches de vos candidatures" in vPage
    assert "proche de « Développeur Java »" in vPage


def test_dashboard_requests_a_search(client):
    """Vérifie la demande de recherche transmise au planificateur."""

    vRefused = client.post("/search/run").text

    save_scheduled_search(
        client.app.dependency_overrides[get_database_file](), ["remotive"], {}
    )

    vAccepted = client.post("/search/run").text

    assert "Enregistrez d'abord une recherche" in vRefused
    assert "le planificateur la lance dans la minute" in vAccepted
    assert "Lancer la recherche enregistrée" in client.get("/").text


def test_manifest_and_icons_are_public(client):
    """Vérifie que le manifeste d'installation est servi, même sans session."""

    client.cookies.clear()

    vManifest = client.get("/static/manifest.webmanifest")

    assert vManifest.status_code == 200
    assert vManifest.json()["display"] == "standalone"
    assert client.get("/static/icon-192.png").status_code == 200

    # Service worker servi à la racine, sans session, jamais gardé en cache
    vWorker = client.get("/service-worker.js")

    assert vWorker.status_code == 200
    assert vWorker.headers["content-type"].startswith("text/javascript")
    assert vWorker.headers["cache-control"] == "no-cache"
    assert "OFFLINE_URL" in vWorker.text
    assert '"/settings"' not in vWorker.text
    assert "MAX_PAGES = 40" in vWorker.text
    assert client.get("/static/offline.html").status_code == 200


def test_spontaneous_draft_is_prepared_without_saving(client):
    """Vérifie le brouillon renvoyé à part, sans candidature enregistrée."""

    vBoard = client.get("/applications").text
    vDraft = client.get(
        "/applications/spontaneous/draft", params={"company": "Acme", "title": "Dev"}
    ).text

    assert "Préparer le message" in vBoard
    assert "candidature spontanée chez Acme pour un poste de Dev." in vDraft
    assert client.get("/applications").text == vBoard


def test_slow_page_is_logged_without_its_parameters(client, monkeypatch, caplog):
    """Vérifie qu'une page lente est signalée par son chemin seul."""

    monkeypatch.setattr(web_app, "SLOW_PAGE_SECONDS", -1)

    client.get("/offers?keyword=secret")

    vMessages = [
        vRecord.getMessage() for vRecord in caplog.records if vRecord.name == "web.app"
    ]

    assert any(vMessage.startswith("Page lente : /offers en") for vMessage in vMessages)
    assert not any("secret" in vMessage for vMessage in vMessages)


def test_security_headers(client):
    """Vérifie les en-têtes de sécurité sur une page et sur une redirection."""

    vPage = client.get("/")

    client.cookies.clear()
    vRedirect = client.get("/offers", follow_redirects=False)

    for vResponse in (vPage, vRedirect):
        assert "script-src 'self';" in vResponse.headers["Content-Security-Policy"]
        assert vResponse.headers["X-Frame-Options"] == "DENY"
        assert vResponse.headers["X-Content-Type-Options"] == "nosniff"
        assert vResponse.headers["Referrer-Policy"] == "same-origin"

    assert vRedirect.status_code == 303


def test_pages_have_no_inline_script(client):
    """Vérifie qu'aucun script en ligne, bloqué par la CSP, ne reste dans les pages."""

    for vPath in (
        "/",
        "/offers",
        "/offers/new",
        "/applications",
        "/quiz?theme=java",
        "/logs",
        "/settings",
    ):
        vText = client.get(vPath).text

        assert re.search(r"\son[a-z]+=", vText) is None
        assert "<script>" not in vText


def test_manual_offer_is_created_or_refused(client):
    """Vérifie la création d'une offre saisie et le refus d'une offre incomplète."""

    vRefused = client.post("/offers/new", data={"title": "Analyste"})

    assert vRefused.status_code == 400
    assert "entreprise manquante, lien ou description manquant" in vRefused.text
    assert 'value="Analyste"' in vRefused.text

    vCreated = client.post(
        "/offers/new",
        data={"title": "Analyste", "company": "Data SA", "url": "https://d.example"},
        follow_redirects=False,
    )

    assert vCreated.status_code == 303
    assert vCreated.headers["location"].startswith("/offer?source=manual&id=")
    assert "Saisie manuelle" in client.get(vCreated.headers["location"]).text


def test_offers_import_reports_rejected_lines(client):
    """Vérifie l'import d'un fichier envoyé et les lignes refusées affichées."""

    vContent = (
        "Titre;Entreprise;Lien\n"
        "Analyste;Data SA;https://d.example\n"
        "Sans entreprise;;https://d.example/2\n"
    ).encode("utf-8")

    vResponse = client.post(
        "/offers/import", files={"file": ("offres.csv", vContent, "text/csv")}
    )

    assert "1 offre(s) importée(s) sur 2" in vResponse.text
    assert "Ligne 3 : entreprise manquante" in vResponse.text

    vRefused = client.post(
        "/offers/import", files={"file": ("offres.txt", b"x", "text/plain")}
    )

    assert vRefused.status_code == 400
    assert "Format non pris en charge" in vRefused.text


def test_company_rules_from_offer_and_settings(client):
    """Vérifie l'avertissement, l'exclusion depuis la fiche et les listes des Paramètres."""

    vCreated = []

    for vTitle in ("Analyste Kotlin", "Architecte Rust"):
        vResponse = client.post(
            "/offers/new",
            data={"title": vTitle, "company": "Acme", "url": "https://a.example"},
            follow_redirects=False,
        )
        vCreated.append(vResponse.headers["location"])

    vFirstId = vCreated[0].rsplit("=", 1)[1]
    client.post(
        "/offer/application",
        data={"source": "manual", "id": vFirstId, "status": "APPLIED"},
    )

    vOffer = client.get(vCreated[1]).text

    assert "Déjà 1 candidature(s) dans cette entreprise : Analyste Kotlin" in vOffer

    vSecondId = vCreated[1].rsplit("=", 1)[1]
    vExcluded = client.post(
        "/offer/company",
        data={"source": "manual", "id": vSecondId, "kind": "excluded"},
        headers={"HX-Request": "true"},
    )

    assert vExcluded.headers["HX-Redirect"] == "/offers"
    assert "Architecte Rust" not in client.get("/offers").text

    vSettings = client.post(
        "/settings/companies", data={"excluded": "Acme", "preferred": "acme sas"}
    )

    assert vSettings.status_code == 400
    assert "à la fois exclue et privilégiée" in vSettings.text


def test_applications_page_and_status_change(client):
    """Vérifie les colonnes, les statistiques et le changement de statut."""

    vCreated = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    )
    vSourceId = vCreated.headers["location"].rsplit("=", 1)[1]
    client.post(
        "/offer/application",
        data={"source": "manual", "id": vSourceId, "status": "APPLIED"},
    )

    vPage = client.get("/applications").text

    assert 'Postulé <span class="muted">(1)</span>' in vPage
    assert "Analyste Kotlin" in vPage
    assert "data-autosubmit" in vPage

    vMoved = client.post(
        "/applications/status",
        data={"source": "manual", "id": vSourceId, "status": "INTERVIEW"},
        follow_redirects=False,
    )

    assert vMoved.status_code == 303
    assert (
        'Entretien <span class="muted">(1)</span>' in client.get("/applications").text
    )

    vRefused = client.post(
        "/applications/status",
        data={"source": "manual", "id": vSourceId, "status": "IGNORED"},
    )

    assert vRefused.status_code == 400


def test_attachments_upload_download_delete(client):
    """Vérifie l'envoi, le téléchargement et la suppression d'une pièce jointe."""

    vOfferUrl = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    ).headers["location"]
    vSourceId = vOfferUrl.rsplit("=", 1)[1]

    vUploaded = client.post(
        "/offer/attachments",
        data={"source": "manual", "id": vSourceId},
        files={"file": ("../CV Rémi.pdf", b"%PDF", "application/pdf")},
        follow_redirects=False,
    )

    assert vUploaded.status_code == 303

    vPage = client.get(vOfferUrl).text
    vAttachmentId = re.search(r"/attachment\?id=(\d+)", vPage).group(1)

    assert "CV Rémi.pdf" in vPage

    vDownload = client.get(f"/attachment?id={vAttachmentId}")

    assert vDownload.content == b"%PDF"
    assert vDownload.headers["content-disposition"].startswith("attachment;")

    vRefused = client.post(
        "/offer/attachments",
        data={"source": "manual", "id": vSourceId},
        files={"file": ("outil.exe", b"MZ", "application/octet-stream")},
    )

    assert vRefused.status_code == 400

    client.post("/attachment/delete", data={"id": vAttachmentId})

    assert client.get(f"/attachment?id={vAttachmentId}").status_code == 404


def test_chatgpt_prompts_and_company_info(client, monkeypatch):
    """Vérifie les demandes affichées et la recherche d'entreprise qui les complète."""

    vOfferUrl = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    ).headers["location"]
    vSourceId = vOfferUrl.rsplit("=", 1)[1]

    vPage = client.get(vOfferUrl).text

    assert 'data-copy="prompt-interview"' in vPage
    assert "Tu es recruteur pour le poste ci-dessous" in vPage

    monkeypatch.setattr(
        web_offers,
        "lookup_company",
        lambda pName, _pHome: [
            {
                "name": "DATA SA",
                "siren": "123456789",
                "activity": "Information et communication",
                "activity_code": "62.01Z",
                "employees": "10 à 19 salariés",
                "category": "PME",
                "created": "2015",
                "city": "LILLE",
                "revenue": None,
                "active": True,
                "url": "https://annuaire.example/123456789",
            }
        ],
    )

    vInfo = client.get(f"/offer/company-info?source=manual&id={vSourceId}").text

    assert "Information et communication, PME, 10 à 19 salariés" in vInfo
    assert "https://annuaire.example/123456789" in vInfo
    assert 'id="prompt-company" class="prompt" hx-swap-oob="true"' in vInfo
    assert "Informations publiques déjà trouvées : DATA SA" in vInfo

    monkeypatch.setattr(
        web_offers,
        "lookup_company",
        lambda pName, _pHome: (_ for _ in ()).throw(
            ValueError("Service indisponible.")
        ),
    )

    assert (
        "Service indisponible."
        in client.get(f"/offer/company-info?source=manual&id={vSourceId}").text
    )


def test_quiz_question_answer_and_review(client):
    """Vérifie une question, sa correction et la question ratée proposée à revoir."""

    vOverview = client.get("/quiz").text

    assert "Révision" in vOverview
    assert "?theme=sql&mode=spaced" in vOverview

    vQuestion = client.get("/quiz?theme=sql&mode=discover").text
    vQuestionId = re.search(r'name="question_id" value="([^"]+)"', vQuestion).group(1)

    assert vQuestion.count('name="choice"') >= 2

    vAnswer = client.post(
        "/quiz/answer",
        data={"question_id": "sql-null", "choice": "0", "mode": "discover"},
    ).text

    assert "Réponse incorrecte" in vAnswer
    assert "Réponse : Aucune ligne" in vAnswer
    assert "1 ratée(s)" in vAnswer
    assert vQuestionId.startswith("sql-")

    vReview = client.get("/quiz?theme=sql&mode=review").text

    assert 'name="question_id" value="sql-null"' in vReview

    vRefused = client.post(
        "/quiz/answer",
        data={"question_id": "inconnue", "choice": "0", "mode": "discover"},
    )

    assert vRefused.status_code == 400


def test_code_review_question_on_the_web(client):
    """Vérifie une revue de code : cases à cocher, réponse juste, case oubliée."""

    vRight = client.post(
        "/quiz/answer",
        data={
            "question_id": "ent-java-revue-equals",
            "indexes": ["1", "0"],
            "mode": "discover",
        },
    ).text
    vEmpty = client.post(
        "/quiz/answer",
        data={"question_id": "ent-java-revue-equals", "mode": "discover"},
    )

    assert "Bonne réponse" in vRight
    assert vEmpty.status_code == 400
    assert "Cochez au moins un constat." in vEmpty.text
    assert 'type="checkbox" name="indexes"' in vEmpty.text


def test_interview_simulation_on_the_web(client):
    """Vérifie une série de simulation sur le web jusqu'au bilan."""

    assert "Simulation d'entretien technique" in client.get("/profile").text
    assert (
        client.post("/profile/simulation/start", data={"theme": "Cobol"}).status_code
        == 400
    )

    client.post("/profile/simulation/start", data={"theme": "Android"})

    for vIndex in range(5):
        vPage = client.get("/profile").text

        assert f"question {vIndex + 1} sur 5" in vPage

        client.post("/profile/simulation/answer", data={"points": ["0", "1"]})

    vSummary = client.get("/profile").text

    assert "Série terminée" in vSummary
    assert "Dernières séries : Android" in vSummary
    assert client.post("/profile/simulation/answer", data={}).status_code == 400

    client.post("/profile/simulation/stop")

    assert "Série terminée" not in client.get("/profile").text


def test_self_assessment_on_the_web(client):
    """Vérifie la grille d'auto-évaluation et les thèmes à renforcer en Révision."""

    assert "Auto-évaluation des compétences" in client.get("/profile").text

    vSaved = client.post(
        "/profile/levels",
        data={
            "skill": ["Java", "Android"],
            "level": ["8", "2"],
            "new_skill": "Kafka",
            "new_level": "4",
        },
        follow_redirects=False,
    )
    vQuiz = client.get("/quiz").text

    assert vSaved.status_code == 303
    assert 'name="skill" value="Kafka"' in client.get("/profile").text
    assert "Entretien Android · Android 2/10" in vQuiz
    assert (
        client.post(
            "/profile/levels", data={"skill": ["Java"], "level": ["12"]}
        ).status_code
        == 400
    )
    assert client.post("/profile/levels", data={"skill": ["Java"]}).status_code == 400


def test_offer_page_shows_the_market_salary(client):
    """Vérifie la ligne Marché de la fiche, même sans offre comparable."""

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Marché" in vPage
    assert "Pas encore assez d" in vPage


def test_interview_date_and_calendar_export(client):
    """Vérifie la date d'entretien saisie et le fichier agenda téléchargé."""

    vOfferUrl = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    ).headers["location"]
    vSourceId = vOfferUrl.rsplit("=", 1)[1]

    client.post(
        "/offer/application",
        data={
            "source": "manual",
            "id": vSourceId,
            "status": "INTERVIEW",
            "interview_at": "2026-10-20T14:30",
        },
    )

    assert 'value="2026-10-20T14:30"' in client.get(vOfferUrl).text

    vCalendar = client.get("/applications/calendar.ics")

    assert vCalendar.headers["content-type"].startswith("text/calendar")
    assert "SUMMARY:Entretien : Analyste Kotlin – Data SA" in vCalendar.text


def test_alerts_min_score_is_saved(client, tmp_path):
    """Vérifie l'enregistrement du score minimal des alertes et le refus d'un autre."""

    vResponse = client.post("/settings/alerts", data={"min_score": "70"})

    assert vResponse.status_code == 200
    assert "Alertes enregistrées." in vResponse.text
    assert 'value="70" selected' in vResponse.text
    assert client.post("/settings/alerts", data={"min_score": "42"}).status_code == (
        400
    )


def test_calendar_subscription_requires_valid_token(client):
    """Vérifie la création de l'adresse, sa lecture sans session et le refus du reste."""

    assert "Aucune adresse créée." in client.get("/settings").text

    vPage = client.post("/settings/calendar").text
    vUrl = re.search(r"http://testserver/calendar/[\w-]+\.ics", vPage).group(0)
    vPath = vUrl.removeprefix("http://testserver")

    client.cookies.clear()

    vCalendar = client.get(vPath)

    assert vCalendar.status_code == 200
    assert vCalendar.headers["content-type"].startswith("text/calendar")
    assert vCalendar.text.startswith("BEGIN:VCALENDAR")
    assert client.get("/calendar/mauvais-jeton.ics").status_code == 404


def test_personal_data_can_be_downloaded(client):
    """Vérifie l'export lisible des données personnelles depuis les Paramètres."""

    vSettings = client.get("/settings").text
    vExport = client.get("/settings/personal-data")

    with zipfile.ZipFile(io.BytesIO(vExport.content)) as vArchive:
        vNames = vArchive.namelist()

    assert "/settings/personal-data" in vSettings
    assert vExport.headers["content-type"] == "application/zip"
    assert "mes-donnees-jobboard-" in vExport.headers["content-disposition"]
    assert {"LISEZMOI.txt", "candidatures.json", "reglages.json"} <= set(vNames)


def test_archive_can_be_downloaded_and_restored(client, tmp_path):
    """Vérifie l'export de la sauvegarde complète puis sa restauration confirmée."""

    vArchive = client.get("/settings/archive")

    assert vArchive.status_code == 200
    assert vArchive.headers["content-type"] == "application/zip"

    vFiles = {"file": ("sauvegarde.zip", vArchive.content, "application/zip")}

    vRefused = client.post("/settings/archive", files=vFiles)

    assert vRefused.status_code == 400
    assert "Cochez la case de confirmation" in vRefused.text

    client.post("/settings/reset", data={"confirm": "1"})
    vRestored = client.post("/settings/archive", files=vFiles, data={"confirm": "1"})

    assert "Sauvegarde restaurée." in vRestored.text
    assert "Développeur Java" in client.get("/offers").text


def test_archive_restore_reports_invalid_file(client):
    """Vérifie le message d'une archive refusée, sans rien modifier."""

    vResponse = client.post(
        "/settings/archive",
        files={"file": ("faux.zip", b"pas une archive", "application/zip")},
        data={"confirm": "1"},
    )

    assert vResponse.status_code == 400
    assert "ce n&#39;est pas un fichier .zip" in vResponse.text
    assert "Développeur Java" in client.get("/offers").text


def test_profile_cv_import_prefills_without_saving(client):
    """Vérifie le pré-remplissage depuis un CV envoyé, sans enregistrement."""

    vResponse = client.post(
        "/profile/cv",
        files={"file": ("cv.txt", "Rémi Verhaeghe\nJava, SQL".encode(), "text/plain")},
    )

    assert vResponse.status_code == 200
    assert 'value="Rémi Verhaeghe"' in vResponse.text
    assert "--- Mon CV ---" in vResponse.text
    assert 'value=""' in client.get("/profile").text

    vRefused = client.post(
        "/profile/cv", files={"file": ("cv.odt", b"x", "application/octet-stream")}
    )

    assert vRefused.status_code == 400
    assert "formats acceptés" in vRefused.text


def test_build_bar_chart_with_colors_per_bar_and_full_width():
    """Vérifie une couleur par barre et l'occupation de toute la largeur."""

    vChart = build_bar_chart(
        ["Titre", "Salaire"],
        [("Remplissage", ["var(--success)", "var(--danger)"], [97, 11])],
        pFillWidth=True,
    )

    assert [vBar["color"] for vBar in vChart["series"][0]["bars"]] == [
        "var(--success)",
        "var(--danger)",
    ]
    assert vChart["fill"] is True


def test_quiz_questions_prompt_import_and_flag(client):
    """Vérifie la demande ChatGPT, l'import d'une archive et le signalement."""

    vPrompt = client.post(
        "/quiz/prompt", data={"theme": "Kafka", "level": "confirmé", "count": "20"}
    )

    assert "Thème : Kafka. Lot n° 1.\n20 questions : 20 confirmé." in vPrompt.text
    assert (
        client.post("/quiz/prompt", data={"theme": " ", "count": "20"}).status_code
        == 400
    )

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        vArchive.writestr(
            "kafka.json",
            json.dumps(
                [
                    {
                        "id": "kafka-topic",
                        "level": "débutant",
                        "question": "Qu'est-ce qu'un topic ?",
                        "choices": ["Un flux de messages", "Une table"],
                        "answer": 0,
                        "explanation": "Un topic regroupe des messages.",
                    }
                ]
            ),
        )

    vImport = client.post(
        "/quiz/import",
        data={"theme": "Kafka"},
        files={"file": ("questions.zip", vBuffer.getvalue(), "application/zip")},
    )

    assert "1 question(s) ajoutée(s) : Kafka." in vImport.text
    assert "?theme=kafka&mode=spaced" in vImport.text

    vRefused = client.post("/quiz/import", data={"theme": "Kafka", "text": "rien"})

    assert vRefused.status_code == 400
    assert "Aucune question" in vRefused.text

    vFlag = client.post(
        "/quiz/flag",
        data={"question_id": "kafka-topic", "theme": "kafka", "mode": "discover"},
        follow_redirects=False,
    )

    assert vFlag.status_code == 303
    assert 'value="kafka-topic"' not in client.get(vFlag.headers["location"]).text


def test_quiz_pack_visual_references_and_guides(client):
    """Vérifie le schéma, les références et les guides d'un pack importé."""

    vPack = build_pack()

    client.post(
        "/quiz/import",
        files={"file": ("pack.zip", vPack, "application/zip")},
    )

    vResult = client.post(
        "/quiz/answer",
        data={"question_id": "ram-jvm-001", "choice": "0", "mode": "discover"},
    ).text

    assert '<img src="/quiz/asset/ram.svg" alt="RAM">' in vResult
    assert 'href="https://docs.oracle.com/"' in vResult
    assert "Guides pratiques" in vResult
    assert "/quiz/guide/ram-jvm-analyse" in vResult

    vAsset = client.get("/quiz/asset/ram.svg")

    assert vAsset.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in vAsset.headers["content-security-policy"]
    assert client.get("/quiz/asset/absent.svg").status_code == 404
    assert client.get("/quiz/asset/..%2Fscraper.db").status_code == 404

    vGuide = client.get("/quiz/guide/ram-jvm-analyse")

    assert "Analyser la RAM" in vGuide.text
    assert "<li>Heap</li>" in vGuide.text
    assert client.get("/quiz/guide/absent").status_code == 404


def test_quiz_pack_export(client):
    """Vérifie le téléchargement des questions importées, et son absence."""

    vEmpty = client.get("/quiz/export")

    assert vEmpty.status_code == 400
    assert "Aucune question importée" in vEmpty.text

    client.post(
        "/quiz/import", files={"file": ("pack.zip", build_pack(), "application/zip")}
    )

    vExport = client.get("/quiz/export")

    assert vExport.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(vExport.content)) as vArchive:
        assert "questions/ram-jvm.json" in vArchive.namelist()


def test_quiz_exam_on_the_web(client, qcm_only_quiz):
    """Vérifie l'examen sur le web : début, réponse, résultat et fermeture."""

    assert "Mode examen (20 questions)" in client.get("/quiz").text
    assert client.get("/quiz/exam", follow_redirects=False).status_code == 303

    vStart = client.post("/quiz/exam/start", data={"domain": "Informatique"})

    assert "Question 1 / 20" in vStart.text

    for vIndex in range(20):
        vPage = client.get("/quiz/exam").text
        vChoice = re.search(r'name="choice" value="(\d+)"', vPage).group(1)
        vAnswer = client.post("/quiz/exam/answer", data={"choice": vChoice}).text

        assert "Réponse :" in vAnswer

    vResult = client.get("/quiz/exam").text

    assert "Examen terminé" in vResult
    assert "Note :" in vResult
    assert "Fermer l'examen" in vResult

    client.post("/quiz/exam/stop")

    assert client.get("/quiz/exam", follow_redirects=False).status_code == 303
    assert (
        client.post("/quiz/exam/start", data={"domain": "Industrie"}).status_code == 400
    )
    assert client.post("/quiz/exam/answer", data={"choice": "0"}).status_code == 400


def test_list_offers_filters_by_match(client, tmp_path):
    """Vérifie le filtre de correspondance minimale de la liste des offres."""

    save_profile(
        tmp_path / "scraper.db", build_profile("", "", "Python, Django", "", "")
    )

    vAll = client.get("/offers").text
    vClose = client.get("/offers", params={"match": "70"}).text

    assert "Développeur Java" in vAll
    assert "Développeur Java" not in vClose
    assert "Développeur Python new" in vClose
    assert '<option value="70" selected>' in vClose
    assert "Développeur Java" in client.get("/offers", params={"match": "42"}).text


def test_quiz_category_navigation(client):
    """Vérifie les catégories : filtre, second clic, statut des thèmes et examen."""

    vAll = client.get("/quiz").text

    assert 'class="quiz-tab is-active"' in vAll
    assert 'class="quiz-chip is-empty"' in vAll
    assert "Tous les thèmes (" in vAll
    assert "<h2>Informatique</h2>" in vAll
    assert "questions acquises" in vAll
    assert '<span class="subdomain-badge">' in vAll

    vFiltered = client.get(
        "/quiz", params={"domain": "Informatique", "subdomain": "Données"}
    ).text

    assert "<h2>Informatique › Données</h2>" in vFiltered
    assert ">SQL</h2>" in vFiltered
    assert ">Java</h2>" not in vFiltered
    # Lien de la catégorie active : il ramène au domaine, sans le sous-domaine.
    assert 'href="/quiz?domain=Informatique"' in vFiltered
    assert 'name="subdomain" value="Données"' in vFiltered

    vEmpty = client.get(
        "/quiz", params={"domain": "Industrie", "subdomain": "Maintenance"}
    ).text

    assert "Aucune question dans cette rubrique" in vEmpty
    assert 'name="theme" value="' in vEmpty

    client.post(
        "/quiz/answer",
        data={"question_id": "sql-null", "choice": "1", "mode": "spaced"},
    )

    assert 'class="tone-primary" title="Révision commencée"' in client.get("/quiz").text


def test_settings_mobile_token(client):
    """Vérifie la carte de l'application mobile : adresse, création du jeton."""

    vPage = client.get("/settings").text

    assert "http://testserver/api/v1" in vPage
    assert "Aucun jeton créé." in vPage
    assert "Afficher le QR code" not in vPage

    vCreated = client.post("/settings/mobile").text

    assert "Afficher le QR code" in vCreated and "<svg" in vCreated

    assert "Jeton créé : saisissez-le dans l&#39;application." in vCreated or (
        "Jeton créé : saisissez-le dans l'application." in vCreated
    )
    assert 'id="mobile-token"' in vCreated


@pytest.mark.parametrize(
    "pStatusCode, pTone", [(200, "success"), (400, "warning"), (500, "danger")]
)
def test_get_message_tone(pStatusCode, pTone):
    """Vérifie la couleur d'un message selon le résultat de la requête."""

    assert web_rendering.get_message_tone(pStatusCode) == pTone


def test_settings_messages_are_colored(client):
    """Vérifie un message d'erreur de saisie en orange et un succès en vert."""

    vRefused = client.post(
        "/settings/companies", data={"excluded": "acme", "preferred": "acme"}
    ).text
    vSaved = client.post(
        "/settings/companies", data={"excluded": "acme", "preferred": "globex"}
    ).text

    assert 'class="application-message tone-warning"' in vRefused
    assert 'class="application-message tone-success"' in vSaved


def test_quiz_imported_questions_cleared_after_confirmation(client):
    """Vérifie l'effacement des questions importées depuis le web, confirmé."""

    client.post(
        "/quiz/import", files={"file": ("pack.zip", build_pack(), "application/zip")}
    )

    vRefused = client.post("/quiz/clear", data={})

    assert vRefused.status_code == 400
    assert "Cochez la case" in vRefused.text

    vCleared = client.post("/quiz/clear", data={"confirm": "1"}).text

    assert "2 question(s) importée(s) effacée(s)" in vCleared
    assert "Analyse RAM et JVM" not in vCleared


def test_biased_lot_shows_a_correction_prompt(client):
    """Vérifie la demande de correction affichée après l'import d'un lot biaisé."""

    vResponse = client.post(
        "/quiz/import",
        data={
            "text": build_lot_text(
                [
                    build_question(vIndex, pAnswer=1, pLongest=True)
                    for vIndex in range(MIN_QUALITY_SAMPLE)
                ]
            )
        },
    )

    assert vResponse.status_code == 200
    assert "tone-warning" in vResponse.text
    assert 'id="quiz-correction"' in vResponse.text
    assert "Questions concernées : grafcet-l1-000" in vResponse.text


def test_validated_packs_are_imported_from_the_dashboard(client, tmp_path, monkeypatch):
    """Vérifie le bouton web des lots validés et le message sans archive."""

    vFolder = tmp_path / "packs"
    vFolder.mkdir()
    monkeypatch.setattr(quiz_packs, "QUIZ_PACKS_DIRECTORY", str(vFolder))

    assert "Importer les lots validés" not in client.get("/quiz").text
    assert client.post("/quiz/import-packs").status_code == 400

    vName, vContent = build_lot_pack("grafcet")
    (vFolder / vName).write_bytes(vContent)

    assert "Importer les lots validés (1)" in client.get("/quiz").text

    vResponse = client.post("/quiz/import-packs")

    assert vResponse.status_code == 200
    assert "100 question(s) ajoutée(s)" in vResponse.text


def test_priority_themes_are_shown_on_the_quiz_page(client):
    """Vérifie la carte des thèmes prioritaires et sa demande préparée."""

    assert "Aucun thème n'est encore demandé" in client.get("/quiz").text

    save_offers(
        app.dependency_overrides[get_database_file](),
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "99",
                    "title": "Dev",
                    "skills": ["SCADA"],
                }
            ]
        ),
        datetime.now(),
    )
    vPage = client.get("/quiz").text

    assert "<strong>Supervision, SCADA et IHM</strong>" in vPage
    assert '<input type="hidden" name="count" value="100">' in vPage


def test_challenges_are_listed_downloaded_and_answered(client):
    """Vérifie les défis sur le web : liste, données, réponses et refus."""

    vList = client.get("/challenges")

    assert vList.status_code == 200
    assert "Les arrêts de la ligne 3" in vList.text
    assert client.get("/challenges/inconnu").status_code == 404

    vPage = client.get("/challenges/engrenages?hints=1")

    assert "Partie 1" in vPage.text and "Partie 2" not in vPage.text
    assert "<li>Après t tours" in vPage.text
    assert "?hints=2" in vPage.text

    vInput = client.get("/challenges/engrenages/input")

    assert vInput.status_code == 200
    assert "engrenages.txt" in vInput.headers["content-disposition"]

    vWrong = client.post(
        "/challenges/engrenages/answer", data={"part": "1", "answer": "1"}
    )

    assert "Ce n&#39;est pas la bonne réponse." in vWrong.text
    assert (
        client.post(
            "/challenges/engrenages/answer", data={"part": "1", "answer": " "}
        ).status_code
        == 400
    )
    assert (
        client.post("/challenges/inconnu/answer", data={"answer": "1"}).status_code
        == 404
    )

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    vExpected = get_expected_answers(
        "pieces-bonnes", get_seed(vDatabaseFile, "pieces-bonnes", datetime.now())
    )

    for vPart, vAnswer in enumerate(vExpected, start=1):
        vSolved = client.post(
            "/challenges/pieces-bonnes/answer",
            data={"part": str(vPart), "answer": vAnswer},
        )

    assert "Solution commentée" in vSolved.text
    assert "★★" in vSolved.text


def test_git_levels_are_listed_played_and_solved(client):
    """Vérifie le bac à sable Git sur le web : liste, commandes, annulation et réussite."""

    vList = client.get("/git")

    assert vList.status_code == 200
    assert "Enregistrer son travail" in vList.text
    assert "git cherry-pick" in vList.text
    assert client.get("/git/inconnu").status_code == 404
    assert client.post("/git/inconnu/command", data={}).status_code == 404

    vPage = client.get("/git/premiers-commits")

    assert vPage.text.count("<svg") >= 2 and "Objectif" in vPage.text

    vFirst = client.post(
        "/git/premiers-commits/command", data={"command": "git commit"}
    )

    assert "Commit C1 enregistré" in vFirst.text
    assert 'name="history" value="git commit"' in vFirst.text

    vUndone = client.post(
        "/git/premiers-commits/command",
        data={"history": ["git commit"], "action": "undo"},
    )

    assert 'name="history"' not in vUndone.text

    vSolved = client.post(
        "/git/premiers-commits/command",
        data={"history": ["git commit"], "command": "git commit"},
    )

    assert "parcours optimal" in vSolved.text
    assert "Niveau suivant" in vSolved.text
    assert "Serveur attendu" not in vSolved.text
    assert "Serveur attendu" in client.get("/git/push").text
    assert (
        client.post(
            "/git/premiers-commits/command",
            data={"history": ["git stash"], "command": "git commit"},
        ).status_code
        == 400
    )


def test_typed_quiz_questions_on_the_web(client):
    """Vérifie les questions interactives sur le web : champs, saisie refusée, réussite."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    import_questions(
        vDatabaseFile,
        "",
        json.dumps({"theme": "Électricité", "questions": [NUMERIC, ORDER, PAIRS]}),
        datetime.now(),
    )

    vRetry = client.post(
        "/quiz/answer", data={"question_id": "ohm-courant", "text": "2,3 V"}
    )

    assert vRetry.status_code == 400
    assert "Unité attendue : A" in vRetry.text
    assert 'name="text"' in vRetry.text and "ohm-courant" in vRetry.text

    vOrder = client.post(
        "/quiz/answer",
        data={"question_id": "consignation-ordre", "indexes": ["0", "0", "1", "2"]},
    )

    assert vOrder.text.count('name="indexes"') == 4

    vPairs = client.post(
        "/quiz/answer", data={"question_id": "grandeurs-unites", "indexes": ["0"]}
    )

    assert "Réponse incomplète" in vPairs.text
    assert '<option value="">Choisir…</option>' in vPairs.text

    vSolved = client.post(
        "/quiz/answer", data={"question_id": "ohm-courant", "text": "2,3 mA"}
    )

    assert "Bonne réponse" in vSolved.text and "0,0023 A" in vSolved.text
    assert (
        client.post(
            "/quiz/answer", data={"question_id": "inconnue", "choice": "0"}
        ).status_code
        == 400
    )


def test_symbol_question_shows_its_visual_on_the_web(client):
    """Vérifie qu'un symbole à reconnaître est montré avec la question sur le web."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vPage = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-024", "indexes": ["0"]},
    ).text

    assert "Réponse incomplète" in vPage
    assert "electricite-symboles-commande.svg" in vPage


def test_zone_question_is_answered_by_clicking_the_image(client):
    """Vérifie une zone sur le web : image cliquable, coordonnées reçues et corrigées."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vRetry = client.post("/quiz/answer", data={"question_id": "electricite-l1-021"})

    assert vRetry.status_code == 400
    assert 'type="image" name="point"' in vRetry.text
    assert "Valider</button>" not in vRetry.text.split("quiz-flag")[0]

    vRight = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-021", "point.x": "390", "point.y": "115"},
    )

    assert "Bonne réponse" in vRight.text

    vWrong = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-021", "point.x": "80", "point.y": "115"},
    )

    assert "Votre réponse : Fusible" in vWrong.text


def test_schema_question_is_built_and_graded_on_the_web(client):
    """Vérifie un schéma à construire sur le web : éditeur, JSON reçu et correction."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vEditor = client.post(
        "/quiz/answer", data={"question_id": "electricite-l1-015", "text": ""}
    )

    assert vEditor.status_code == 400
    assert "Placez au moins un composant" in vEditor.text
    assert "data-schema-editor" in vEditor.text and 'data-type="prise"' in vEditor.text

    vChain = ["reseau", "differentiel", "disjoncteur", "prise"]
    vSchema = {
        "components": [
            {"type": vType, "x": 0, "y": vIndex} for vIndex, vType in enumerate(vChain)
        ],
        "wires": [
            ["reseau", "sortie", "differentiel", "1"],
            ["differentiel", "2", "disjoncteur", "1"],
            ["disjoncteur", "2", "prise", "entrée"],
        ],
    }
    vRight = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-015", "text": json.dumps(vSchema)},
    )

    assert "Bonne réponse" in vRight.text
    assert "schema-expected" in vRight.text and ">Votre schéma</text>" in vRight.text


def test_offer_revision_and_mock_exam(client):
    """Vérifie les thèmes à revoir sur la fiche d'offre et l'examen blanc associé."""

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Réviser pour l'entretien" in vPage
    assert "Examen blanc (16 questions)" in vPage
    assert 'name="id" value="new"' in vPage

    vStart = client.post("/quiz/exam/start", data={"source": "adzuna", "id": "new"})

    assert "Entretien : Développeur Python new chez Entreprise A" in vStart.text
    assert "Question 1 / 16" in vStart.text
    assert 'data-remaining="960"' in vStart.text or "Temps restant : 15:" in vStart.text

    client.post("/quiz/exam/stop")

    assert (
        client.post(
            "/quiz/exam/start", data={"source": "adzuna", "id": "inconnue"}
        ).status_code
        == 404
    )


def test_skills_page(client):
    """Vérifie le tableau des compétences : chiffres clés, actions et menu."""

    vPage = client.get("/skills").text

    assert "À travailler en premier" in vPage
    assert "<strong>Python</strong>" in vPage
    assert 'href="/skills"' in vPage
    assert "?theme=python" in vPage
    assert "Glossaire des compétences" in vPage
    assert 'title="Langage polyvalent' in vPage

    vPrompt = client.post("/quiz/prompt", data={"theme": "Cloud et infrastructure"})

    assert vPrompt.status_code == 200


def test_skill_is_added_to_profile_from_the_web(client):
    """Vérifie le formulaire d'ajout d'une compétence au profil."""

    vResponse = client.post("/skills/profile", data={"skill": "Python"})
    vPage = client.get("/skills").text

    assert vResponse.status_code == 200
    assert 'name="skill" value="Python"' not in vPage
    assert 'name="skill" value="Django"' in vPage


def test_week_follow_ups_on_applications_page(client):
    """Vérifie le brouillon de relance affiché et la relance notée."""

    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": datetime.now().date().isoformat(),
        },
    )

    vPage = client.get("/applications")
    vMissing = client.post(
        "/applications/follow-up", data={"source": "adzuna", "id": "old"}
    )
    vDone = client.post(
        "/applications/follow-up",
        data={"source": "adzuna", "id": "new"},
        follow_redirects=False,
    )

    assert "Relances de la semaine" in vPage.text
    assert "Objet : ma candidature au poste de" in vPage.text
    assert vMissing.status_code == 400
    assert vDone.status_code == 303
    assert "1 relance(s) déjà faite(s)" in client.get("/applications").text


def test_follow_up_is_sent_from_applications_page(client, monkeypatch):
    """Vérifie l'envoi d'une relance : formulaire, messages fixes, adresse gardée."""

    vSent = []

    monkeypatch.setattr(web_applications, "get_missing_email_settings", lambda: [])
    monkeypatch.setattr(
        "job.application_tracking.send_email",
        lambda pRecipient, pSubject, pText: vSent.append(pRecipient),
    )
    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": datetime.now().date().isoformat(),
        },
    )

    vForm = client.get("/applications").text
    vInvalid = client.post(
        "/applications/follow-up/send",
        data={"source": "adzuna", "id": "new", "recipient": "x", "draft": "Bonjour"},
        follow_redirects=False,
    )
    vSentPage = client.post(
        "/applications/follow-up/send",
        data={
            "source": "adzuna",
            "id": "new",
            "recipient": "rh@acme.fr",
            "draft": "Objet : relance\n\nBonjour",
        },
    )

    assert "Envoyer et noter la relance" in vForm
    assert vInvalid.headers["location"].endswith("?follow_up=invalid")
    assert "Relance envoyée et notée" in vSentPage.text
    assert vSent == ["rh@acme.fr"]

    def fail(*_pArgs):
        raise OSError("hors ligne")

    monkeypatch.setattr("job.application_tracking.send_email", fail)
    vFailed = client.post(
        "/applications/follow-up/send",
        data={
            "source": "adzuna",
            "id": "new",
            "recipient": "rh@acme.fr",
            "draft": "Objet : relance\n\nBonjour",
        },
        follow_redirects=False,
    )

    assert vFailed.headers["location"].endswith("?follow_up=failed")

    monkeypatch.setattr(
        web_applications, "get_missing_email_settings", lambda: ["GMAIL_ADDRESS"]
    )
    vUnconfigured = client.post(
        "/applications/follow-up/send",
        data={"source": "adzuna", "id": "new", "recipient": "rh@acme.fr"},
    )

    assert "Envoyer et noter la relance" not in vUnconfigured.text
    assert "renseignez GMAIL_ADDRESS" in vUnconfigured.text
    assert (
        client.post(
            "/applications/follow-up/send",
            data={"source": "adzuna", "id": "absente"},
        ).status_code
        == 400
    )


def test_profile_star_answers(client):
    """Vérifie l'enregistrement d'une réponse STAR et son refus si invalide."""

    vSaved = client.post(
        "/profile/star",
        data={"question": "echec", "experience": "", "action": "Revu les tests"},
    )
    vRefused = client.post("/profile/star", data={"question": "inconnue"})

    assert "Réponse enregistrée." in vSaved.text
    assert "1 réponse(s) préparée(s) sur 7" in vSaved.text
    assert vRefused.status_code == 400


def test_offers_sorted_by_freshness(client):
    """Vérifie la colonne de fraîcheur et le tri des plus fraîches en tête."""

    vText = client.get("/offers", params={"sort": "fresh"}).text

    assert "Fraîcheur" in vText
    assert 'value="fresh" selected' in vText
    assert vText.index("Développeur Java") > vText.index("Développeur Python new")


def test_offers_near_home_sorted_by_distance(client):
    """Vérifie la colonne Distance, le tri des plus proches et le filtre de rayon."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_json_setting(
        vDatabaseFile,
        HOME_KEY,
        {
            "address": "Lille",
            "label": "Lille",
            "latitude": 50.6366,
            "longitude": 3.0635,
        },
    )
    save_offer_positions(
        vDatabaseFile,
        [
            (45.758, 4.835, "69", "adzuna", "old"),
            (50.6942, 3.1746, "59", "adzuna", "new"),
        ],
    )

    vSorted = client.get("/offers", params={"sort": "distance"}).text

    assert 'value="distance" selected' in vSorted
    assert ">10 km<" in vSorted
    assert vSorted.index("Développeur Python new") < vSorted.index("Développeur Java")

    vNear = client.get("/offers", params={"distance": "25"}).text

    assert "Développeur Python new" in vNear
    assert "Développeur Java" not in vNear


def test_interview_journal_on_offer_page(client):
    """Vérifie l'ajout d'une entrée au journal depuis la fiche d'une offre."""

    vEmpty = client.post(
        "/offer/interview-note", data={"source": "adzuna", "id": "new"}
    )
    vAdded = client.post(
        "/offer/interview-note",
        data={"source": "adzuna", "id": "new", "questions": "Votre plus grand défi ?"},
    )
    client.post("/profile", data={"skills": "Java"})
    vPage = client.get("/offer", params={"source": "adzuna", "id": "old"}).text

    assert vEmpty.status_code == 400
    assert "Entrée ajoutée au journal." in vAdded.text
    assert "Votre plus grand défi ?" in vAdded.text
    assert "Questions déjà posées en entretien" in vPage


def test_offer_page_charts_mock_exam_scores(client, monkeypatch):
    """Vérifie le graphique des notes d'examen blanc à partir de deux examens."""

    vResults = [
        {"finished_at": "2026-10-14T10:00:00", "score": 80, "offer": ["adzuna", "new"]},
        {"finished_at": "2026-10-12T10:00:00", "score": 40, "offer": ["adzuna", "new"]},
    ]
    monkeypatch.setattr(
        "web.routes.offers.load_exam_results", lambda pDatabaseFile, pKey: vResults
    )

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Notes des examens blancs" in vPage
    assert "meilleure note 80 %" in vPage


def test_quiz_exam_errors_are_reviewed_on_the_web(client):
    """Vérifie l'enchaînement sur les erreurs, refusé tant qu'il n'y en a pas."""

    assert client.post("/quiz/exam/errors").status_code == 400

    client.post("/quiz/exam/start", data={"source": "adzuna", "id": "new"})

    for _ in range(16):
        client.post("/quiz/exam/answer", data={"choice": "0"})

    vResult = client.get("/quiz/exam").text

    assert "Revoir les" in vResult

    vReview = client.post("/quiz/exam/errors")

    assert "Erreurs : Entretien" in vReview.text


def test_database_backup_restored_from_settings(client, tmp_path):
    """Vérifie la liste des sauvegardes et la restauration confirmée sur le web."""

    vBackup = backup_database(
        tmp_path / "scraper.db", datetime(2026, 10, 18, 9, 0), "auto"
    )
    vPage = client.get("/settings").text
    vRefused = client.post("/settings/backup", data={"name": vBackup.name})
    vUnknown = client.post("/settings/backup", data={"name": "../x.db", "confirm": "1"})
    vRestored = client.post(
        "/settings/backup", data={"name": vBackup.name, "confirm": "1"}
    )

    assert "18/10/2026 09:00 · automatique" in vPage
    assert vRefused.status_code == 400
    assert "Sauvegarde introuvable." in vUnknown.text
    assert "Sauvegarde restaurée." in vRestored.text


def test_database_restored_from_the_nas_on_the_web(client, tmp_path, monkeypatch):
    """Vérifie la liste des copies du NAS lue à la demande et leur restauration."""

    vNas = tmp_path / "nas"
    vBackup = backup_database(
        tmp_path / "scraper.db", datetime(2026, 10, 18, 2, 0), "auto"
    )
    copy_to_nas(tmp_path / "scraper.db", vNas)
    vBackup.unlink()

    assert "Lire les copies du NAS" not in client.get("/settings").text

    monkeypatch.setattr(web_settings, "BACKUP_NAS_DIRECTORY", str(vNas))
    monkeypatch.setattr(storage_backup, "BACKUP_NAS_DIRECTORY", str(vNas))
    vCopies = client.get("/settings/nas-copies").text
    vRestored = client.post(
        "/settings/backup",
        data={"name": vBackup.name, "confirm": "1", "origin": "nas"},
    )

    assert "Lire les copies du NAS" in client.get("/settings").text
    assert "18/10/2026 02:00 · automatique" in vCopies
    assert "Sauvegarde restaurée." in vRestored.text

    monkeypatch.setattr(storage_backup, "BACKUP_NAS_DIRECTORY", str(tmp_path / "x"))

    assert "injoignable" in client.get("/settings/nas-copies").text


def test_offers_comparison_on_the_web(client):
    """Vérifie l'ajout depuis la fiche, la page de comparaison et son vidage."""

    vAdded = client.post(
        "/offer/compare", data={"source": "adzuna", "id": "new"}, follow_redirects=False
    )
    vPage = client.get("/compare").text
    vOffer = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    client.post("/compare/clear")

    assert vAdded.status_code == 303
    assert "Télétravail" in vPage
    assert "Retirer de la comparaison" in vOffer
    assert "Aucune offre à comparer" in client.get("/compare").text


def test_interview_drill_on_the_web(client):
    """Vérifie la question affichée puis notée depuis la page Profil."""

    client.post("/profile/star", data={"question": "echec", "result": "Leçon"})

    vPage = client.get("/profile").text
    vCard = vPage.split('name="card" value="')[1].split('"')[0]
    vGraded = client.post("/profile/drill", data={"card": vCard, "known": "1"})

    assert "Racontez un échec" in vPage
    assert "Aucune question à revoir aujourd" in vGraded.text


def test_menu_alerts_badge(client):
    """Vérifie le badge du menu, vide sans action en attente."""

    assert client.get("/alerts").text == ""
    assert 'hx-get="/alerts"' in client.get("/applications").text

    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": "2026-01-01",
        },
    )

    vBadge = client.get("/alerts").text

    assert ">1</span>" in vBadge
    assert "1 relance(s) à faire" in vBadge


def test_offer_description_translated_in_place(client, monkeypatch):
    """Vérifie la traduction sur place de la description, puis le retour au texte."""

    monkeypatch.setattr(web_offers, "can_translate", lambda _pText: True)
    monkeypatch.setattr(
        web_offers,
        "translate_with_cache",
        lambda _pDatabaseFile, _pText: "Nous recherchons",
    )
    vOfferUrl = client.post(
        "/offers/new",
        data={
            "title": "Entwickler",
            "company": "GmbH",
            "url": "https://de.example",
            "description": "Wir suchen neue Mitarbeiter für unser Team in Berlin",
        },
        follow_redirects=False,
    ).headers["location"]
    vSourceId = vOfferUrl.rsplit("=", 1)[1]

    assert 'hx-get="/offer/translation?source=manual' in client.get(vOfferUrl).text

    vParams = {"source": "manual", "id": vSourceId}
    vTranslated = client.get("/offer/translation", params=vParams).text

    assert "Nous recherchons" in vTranslated and "Texte d'origine" in vTranslated

    vOriginal = client.get("/offer/translation", params={**vParams, "original": 1})

    assert "Wir suchen" in vOriginal.text
    assert (
        client.get("/offer/translation", params={**vParams, "id": "x"}).status_code
        == 404
    )


def test_settings_company_pages_saved_and_checked(client, monkeypatch):
    """Vérifie l'enregistrement des pages carrière suivies et leur vérification."""

    monkeypatch.delenv("LEVER_COMPANIES", raising=False)

    vSaved = client.post("/settings/company-pages", data={"lever": "qonto, inconnue"})

    assert "Listes enregistrées" in vSaved.text
    assert 'value="qonto, inconnue"' in vSaved.text

    def count(_pPlatform, pCompany):
        if pCompany == "inconnue":
            raise ValueError("404")
        return 7

    monkeypatch.setattr("job.company_pages.count_published_offers", count)

    vChecked = client.post(
        "/settings/company-pages/check", data={"lever": "qonto, inconnue"}
    )

    assert "Lever · qonto : 7 offre(s)" in vChecked.text
    assert "Lever · inconnue : introuvable" in vChecked.text


def test_offers_map_offers_match_shortcuts(client):
    """Vérifie les raccourcis de correspondance de la carte, autres filtres gardés."""

    vPage = client.get("/offers?view=map&q=Python&match=50").text

    assert 'href="?view=map&amp;q=Python&amp;match=70"' in vPage
    assert (
        'class="button button-primary" href="?view=map&amp;q=Python&amp;match=50"'
        in vPage
    )
    assert "Pastille d'autant plus grande" in vPage


def test_dashboard_lists_settings_to_do(client):
    """Vérifie la carte À faire de l'accueil, avec le lien vers chaque réglage."""

    vPage = client.get("/").text

    assert "À faire pour bien démarrer" in vPage
    assert '<a href="/settings">' in vPage


def test_labour_market_is_downloaded_from_the_market_page(client, monkeypatch):
    """Vérifie le bouton de téléchargement de l'enquête, puis le message d'échec."""

    vPage = client.get("/market").text

    assert "Télécharger l&#39;enquête" in vPage

    def fail():
        raise requests.ConnectionError("hors ligne")

    monkeypatch.setattr("web.routes.skills.refresh_labour_market", fail)
    vFailed = client.post("/market/france-travail", follow_redirects=False)

    assert vFailed.headers["location"].endswith("?outlook=failed")
    assert "Téléchargement impossible" in client.get("/market?outlook=failed").text


def test_market_page(client):
    """Vérifie la page Mon marché et son entrée dans le menu."""

    vPage = client.get("/market").text

    assert "Net mensuel médian" in vPage
    assert "Compétences les plus demandées" in vPage
    assert 'href="/market"' in client.get("/").text


def test_recruiter_replies_are_read_and_handled(client, monkeypatch):
    """Vérifie la lecture des réponses Gmail, puis leur application ou leur oubli."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)

    assert "À renseigner dans .env" in client.post("/applications/replies").text
    assert "Lire mes réponses Gmail" in client.get("/applications").text

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "old", "status": "APPLIED"},
    )
    monkeypatch.setattr(
        web_applications,
        "check_replies",
        lambda pDatabaseFile, pNow: [
            {
                "message_id": "<1>",
                "subject": "Votre candidature",
                "date": datetime(2026, 10, 22),
                "source": "adzuna",
                "source_id": "old",
                "title": "Développeur Java",
                "company": "Entreprise A",
                "current_status": "APPLIED",
                "status": "INTERVIEW",
            }
        ],
    )

    vReplies = client.post("/applications/replies").text
    vApplied = client.post(
        "/applications/replies/handle",
        data={
            "action": "apply",
            "message_id": "<1>",
            "source": "adzuna",
            "id": "old",
            "status": "INTERVIEW",
        },
    ).text
    vIgnored = client.post(
        "/applications/replies/handle",
        data={
            "action": "ignore",
            "message_id": "<2>",
            "source": "adzuna",
            "id": "old",
            "status": "REJECTED",
        },
    ).text

    assert "« Votre candidature »" in vReplies
    assert "Statut « Entretien » appliqué." in vApplied
    assert "Réponse ignorée." in vIgnored
    assert (
        get_application(app.dependency_overrides[get_database_file](), "adzuna", "old")[
            "status"
        ]
        == "INTERVIEW"
    )


def test_tailored_cv_is_downloaded(client):
    """Vérifie le CV adapté : refusé sans profil, puis fichier Word nommé d'après l'offre."""

    assert client.get("/offer/cv?source=adzuna&id=new").status_code == 400

    client.post("/profile", data={"skills": "Python, Django", "experiences": ""})
    vResponse = client.get("/offer/cv?source=adzuna&id=new")

    assert vResponse.status_code == 200
    assert vResponse.content[:2] == b"PK"
    assert "CV%20-%20Entreprise%20A" in vResponse.headers["content-disposition"]


def test_list_offers_hides_consulting_and_training(client):
    """Vérifie les cases Clients finaux seulement et Sans stage ni alternance."""

    save_offers(
        app.dependency_overrides[get_database_file](),
        pd.DataFrame(
            [
                build_offer(
                    "esn",
                    company="Alten",
                    title="Ingénieur Java",
                    fingerprint="ingenieur java|alten|lille",
                ),
                build_offer("stage", title="Stage développeur"),
            ]
        ),
        datetime.now(),
    )

    vAll = client.get("/offers").text
    vFiltered = client.get("/offers?no_consulting=1&no_training=1").text

    assert ">ESN</span>" in vAll
    assert "Ingénieur Java" in vAll and "Stage développeur" in vAll
    assert "Ingénieur Java" not in vFiltered
    assert "Stage développeur" not in vFiltered


def test_company_page_is_added_from_its_address(client, monkeypatch):
    """Vérifie l'ajout d'une entreprise depuis l'adresse de son site carrière."""

    monkeypatch.setattr(
        "job.company_pages.count_published_offers", lambda pPlatform, pCompany: 5
    )

    vAdded = client.post(
        "/settings/company-pages/url", data={"url": "https://jobs.lever.co/doctolib"}
    ).text
    vRefused = client.post(
        "/settings/company-pages/url", data={"url": "https://www.exemple.fr"}
    ).text

    assert "doctolib ajoutée : 5 offre(s)" in vAdded
    assert "Adresse non reconnue" in vRefused


def test_letter_is_downloaded_as_edited(client):
    """Vérifie la lettre téléchargée telle que modifiée dans la page."""

    vResponse = client.post(
        "/offer/letter",
        data={"source": "adzuna", "id": "new", "letter": "Bonjour,\nMa lettre"},
    )

    assert vResponse.status_code == 200
    assert vResponse.content[:2] == b"PK"
    assert "Lettre%20-%20Entreprise%20A" in vResponse.headers["content-disposition"]


def test_search_journal_is_downloaded(client):
    """Vérifie le téléchargement du journal de recherche pour une période."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "old", "status": "APPLIED"},
    )

    vResponse = client.get("/applications/journal.csv?start=2000-01-01&end=2100-01-01")

    assert vResponse.status_code == 200
    assert "Candidature envoyée" in vResponse.content.decode("utf-8-sig")
    assert "journal-recherche-20000101-21000101.csv" in (
        vResponse.headers["content-disposition"]
    )
    assert "Journal de recherche" in client.get("/applications").text


def test_priority_skills_exam_is_started(client):
    """Vérifie l'examen blanc lancé sur des compétences, puis le refus sans thème."""

    vRefused = client.post("/quiz/exam/start", data={"skills": "Inconnue"})
    vStarted = client.post("/quiz/exam/start", data={"skills": "SQL"})

    assert vStarted.url.path == "/quiz/exam"
    assert vRefused.status_code == 400
    assert "Aucun thème de révision ne couvre ces compétences" in vRefused.text


def test_offers_above_experience_are_flagged_and_hidden(client):
    """Vérifie le badge d'expérience demandée et le filtre À ma portée."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_settings(
        vDatabaseFile, {**load_settings(vDatabaseFile), "experience_years": 2}
    )
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                build_offer(
                    "senior", title="Architecte logiciel", experience_level="8 ans"
                )
            ]
        ),
        datetime.now(),
    )

    vAll = client.get("/offers").text
    vReach = client.get("/offers?reach=1").text

    assert "8 ans demandés" in vAll
    assert "Architecte logiciel" not in vReach


def test_spontaneous_application_is_added(client):
    """Vérifie la candidature spontanée ajoutée à la colonne Postulé."""

    vPage = client.post(
        "/applications/spontaneous",
        data={"company": "OVHcloud", "title": "Développeur Java"},
    ).text

    assert "Candidature spontanée · Développeur Java" in vPage
    assert client.post("/applications/spontaneous", data={}).status_code == 400


def test_unknown_place_is_corrected_from_the_quality_page(client, monkeypatch):
    """Vérifie la correction d'un lieu depuis la page Qualité."""

    monkeypatch.setattr(
        "web.routes.monitoring.resolve_place",
        lambda pDatabaseFile, pKey, pCommune: "Roubaix",
    )

    assert "Lieux introuvables" in client.get("/quality").text

    vPage = client.post("/quality/place", data={"key": "x", "commune": "Roubaix"}).text

    assert "Lieu associé à Roubaix" in vPage


def test_offer_is_added_from_a_link(client, monkeypatch):
    """Vérifie l'ajout depuis un lien, puis le message quand la page ne suffit pas."""

    monkeypatch.setattr(
        "web.routes.offers.add_offer_from_link",
        lambda pDatabaseFile, pUrl, pNow: "abc",
    )

    vCreated = client.post(
        "/offers/from-link",
        data={"url": "https://exemple.fr/offre"},
        follow_redirects=False,
    )

    assert vCreated.status_code == 303
    assert "id=abc" in vCreated.headers["location"]

    def refuse(pDatabaseFile, pUrl, pNow):
        raise ValueError("Aucune fiche d'offre structurée sur cette page")

    monkeypatch.setattr("web.routes.offers.add_offer_from_link", refuse)

    vRefused = client.post("/offers/from-link", data={"url": "https://exemple.fr"})

    assert vRefused.status_code == 400
    assert "Aucune fiche" in vRefused.text


def test_status_history_is_shown_on_the_offer(client):
    """Vérifie l'historique des statuts dans le bloc de suivi de la fiche."""

    vPage = client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "APPLIED"},
    ).text

    assert "Historique : Postulé le" in vPage


def test_progress_page_and_sidebar_summary(client):
    """Vérifie la page Progression et l'encart du menu lu par progress.js."""

    vPage = client.get("/progress")
    vSummary = client.get("/progress/summary").text

    assert vPage.status_code == 200
    assert "Niveau 1 · Apprenti" in vPage.text
    assert "Réviser 10 questions" in vPage.text
    assert "Candidature envoyée" in vPage.text
    assert 'data-xp="0"' in vSummary and 'data-level="1"' in vSummary
    assert 'hx-get="/progress/summary"' in client.get("/").text
