"""Tests web de la liste, du détail et de la qualité des offres"""

from datetime import datetime

import pandas as pd
import pytest
import requests

from job.geocoding import HOME_KEY
from job.local_employers import LOCAL_EMPLOYERS_KEY
from job.profile import build_profile, save_profile
from job.settings import load_settings, save_settings
from job.spontaneous_applications import load_spontaneous
from storage.geo_cache import save_offer_positions
from storage.job_offers import get_offer, save_offers, set_availability
from storage.settings_repository import save_json_setting
from web.app import app, get_database_file
import web.routes.offer_detail as web_offer_detail

from tests.web.helpers import build_offer


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


def test_unknown_offer_renders_error_page(client):
    """Vérifie qu'une offre introuvable affiche une page du site, pas du JSON."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "inconnue"})

    assert vResponse.status_code == 404
    assert "Page introuvable" in vResponse.text
    assert "Offre introuvable" in vResponse.text


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

    monkeypatch.setattr(
        "web.routes.offer_detail.check_offer_link", lambda pUrl: pResult
    )

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


def test_offer_page_shows_the_market_salary(client):
    """Vérifie la ligne Marché de la fiche, même sans offre comparable."""

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Marché" in vPage
    assert "Pas encore assez d" in vPage


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


def test_offer_description_translated_in_place(client, monkeypatch):
    """Vérifie la traduction sur place de la description, puis le retour au texte."""

    monkeypatch.setattr(web_offer_detail, "can_translate", lambda _pText: True)
    monkeypatch.setattr(
        web_offer_detail,
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


def test_offers_map_offers_match_shortcuts(client):
    """Vérifie les raccourcis de correspondance de la carte, autres filtres gardés."""

    vPage = client.get("/offers?view=map&q=Python&match=50").text

    assert 'href="?view=map&amp;q=Python&amp;match=70"' in vPage
    assert (
        'class="button button-primary" href="?view=map&amp;q=Python&amp;match=50"'
        in vPage
    )
    assert "Pastille d'autant plus grande" in vPage


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


def test_offer_is_added_from_a_link(client, monkeypatch):
    """Vérifie l'ajout depuis un lien, puis le message quand la page ne suffit pas."""

    monkeypatch.setattr(
        "web.routes.offer_creation.add_offer_from_link",
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

    monkeypatch.setattr("web.routes.offer_creation.add_offer_from_link", refuse)

    vRefused = client.post("/offers/from-link", data={"url": "https://exemple.fr"})

    assert vRefused.status_code == 400
    assert "Aucune fiche" in vRefused.text


def test_hybrid_offers_have_badge_filter_and_sort(client):
    """Vérifie le badge Double profil, le filtre et le tri qui les met en tête."""

    client.post(
        "/offers/new",
        data={
            "title": "Technicien informatique industrielle",
            "company": "Usine SA",
            "url": "https://usine.example",
        },
    )

    vFiltered = client.get("/offers?hybrid=1").text
    vSorted = client.get("/offers?sort=hybrid").text

    assert "Technicien informatique industrielle" in vFiltered
    assert "Développeur Java" not in vFiltered
    assert ">Double profil</span>" in vFiltered
    assert vSorted.index("Technicien informatique industrielle") < vSorted.index(
        "Développeur Java"
    )


def test_employers_page_updates_filters_and_follows(client, monkeypatch):
    """Vérifie la page des employeurs : mise à jour, filtre, suivi, service muet."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()

    def fake_fetch(pDatabaseFile, _pNow):
        save_json_setting(
            pDatabaseFile,
            LOCAL_EMPLOYERS_KEY,
            {
                "updated_at": "2026-10-30T09:00:00",
                "employers": [
                    {
                        "siren": "111",
                        "name": "Entreprise A",
                        "names": ["Entreprise A"],
                        "sector": "Énergie",
                        "city": "Lille",
                        "distance_km": 12,
                        "page": "https://annuaire-entreprises.data.gouv.fr/entreprise/111",
                    },
                    {
                        "siren": "222",
                        "name": "Fonderie B",
                        "names": ["Fonderie B"],
                        "sector": "Métallurgie et mécanique",
                        "headcount": "500 à 999 salariés",
                        "city": "Douai",
                        "distance_km": 40,
                        "latitude": 50.37,
                        "longitude": 3.08,
                        "page": "https://annuaire-entreprises.data.gouv.fr/entreprise/222",
                    },
                ],
            },
        )
        return 2

    assert "Liste encore vide" in client.get("/employers").text
    assert "/employers" in client.get("/market").text

    monkeypatch.setattr("web.routes.employers.fetch_local_employers", fake_fetch)
    vPage = client.post("/employers/update").text

    assert "2 employeur(s) trouvé(s)" in vPage and "Fonderie B" in vPage

    vFiltered = client.get("/employers?distance=20").text

    assert "Entreprise A" in vFiltered and "Fonderie B" not in vFiltered

    vFollowed = client.post(
        "/employers/follow", data={"siren": "111", "sector": "", "distance": 0}
    )

    assert vFollowed.status_code == 200
    assert "Suivi" in vFollowed.text
    assert client.post("/employers/follow", data={"siren": "999"}).status_code == 200

    vSent = client.post(
        "/employers/spontaneous",
        data={"siren": "222", "status": "sent", "contact": "sent"},
    )

    assert vSent.status_code == 200
    assert load_spontaneous(vDatabaseFile)["222"]["status"] == "sent"
    assert "Fonderie B" in vSent.text and "Entreprise A" not in vSent.text
    assert "1 candidature(s) spontanée(s), 0 à relancer" in vSent.text
    assert '"tone": "warning"' in vSent.text
    assert (
        client.post(
            "/employers/spontaneous", data={"siren": "222", "status": "oublié"}
        ).status_code
        == 400
    )

    def failing_fetch(_pDatabaseFile, _pNow):
        raise ValueError("Le service public ne répond pas.")

    monkeypatch.setattr("web.routes.employers.fetch_local_employers", failing_fetch)

    assert "ne répond pas" in client.post("/employers/update").text
