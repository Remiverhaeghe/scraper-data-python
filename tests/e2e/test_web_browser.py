"""Tests de bout en bout du tableau de bord web, dans un vrai navigateur (Playwright)

Le serveur tourne dans un fil d'exécution sur un port libre, avec une base
temporaire. Sans Playwright ou sans Chromium installé, ces tests sont ignorés :
pip install playwright puis python -m playwright install chromium.
"""

import json
import socket
import threading
import time
from datetime import datetime

import pandas as pd
import pytest
import uvicorn

from job.quiz_import import import_questions
from storage.geo_cache import save_offer_positions
from storage.job_offers import save_offers
from tests.conftest import TEST_PASSWORD
from web.app import app, get_database_file
from web.auth import hash_password

sync_api = pytest.importorskip("playwright.sync_api")

PAGES = (
    "/",
    "/offers",
    "/applications",
    "/history",
    "/quiz",
    "/profile",
    "/settings",
    "/quality",
    "/logs",
    "/legal",
)

PHONE_VIEWPORT = {"width": 390, "height": 844}


def get_free_port():
    """Retourne un port TCP libre sur la machine locale."""

    with socket.socket() as vSocket:
        vSocket.bind(("127.0.0.1", 0))
        rPort = vSocket.getsockname()[1]

    return rPort


@pytest.fixture(scope="module")
def server_url(tmp_path_factory):
    """Démarre le tableau de bord sur une base remplie ; retourne son adresse."""

    vDatabaseFile = tmp_path_factory.mktemp("e2e") / "scraper.db"
    vPort = get_free_port()

    with pytest.MonkeyPatch.context() as vPatch:
        vPatch.setenv("WEB_USERNAME", "admin")
        vPatch.setenv("WEB_PASSWORD_HASH", hash_password(TEST_PASSWORD, 1000))
        vPatch.setenv("WEB_SESSION_SECRET", "secret-de-test")
        app.dependency_overrides[get_database_file] = lambda: vDatabaseFile

        vServer = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=vPort, log_level="warning")
        )
        vThread = threading.Thread(target=vServer.run, daemon=True)
        vThread.start()

        while not vServer.started:
            time.sleep(0.05)

        save_offers(
            vDatabaseFile,
            pd.DataFrame(
                [
                    {
                        "source": "remotive",
                        "source_id": str(vIndex),
                        "title": vTitle,
                        "company": "Acme",
                        "location": "Lille",
                        "url": f"https://example.com/{vIndex}",
                    }
                    for vIndex, vTitle in enumerate(
                        ("Développeur Java", "Développeur Python", "Data engineer")
                    )
                ]
            ),
            datetime.now(),
        )
        save_offer_positions(
            vDatabaseFile,
            [(50.63, 3.06, "remotive", "0"), (50.69, 3.17, "remotive", "1")],
        )

        yield f"http://127.0.0.1:{vPort}"

        vServer.should_exit = True
        vThread.join(timeout=10)
        app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def browser():
    """Lance Chromium sans fenêtre, ou ignore les tests s'il n'est pas installé."""

    with sync_api.sync_playwright() as vPlaywright:
        try:
            rBrowser = vPlaywright.chromium.launch()

        except sync_api.Error as vException:
            pytest.skip(f"Chromium absent : {vException.message.splitlines()[0]}")

        yield rBrowser

        rBrowser.close()


@pytest.fixture
def page(browser, server_url):
    """Ouvre une page connectée ; les erreurs de la console sont relevées."""

    vContext = browser.new_context(base_url=server_url)
    rPage = vContext.new_page()
    rPage.console_errors = []
    rPage.on(
        "console",
        lambda pMessage: (
            rPage.console_errors.append(pMessage.text)
            if pMessage.type == "error"
            else None
        ),
    )

    rPage.goto("/login")
    rPage.fill("input[name=username]", "admin")
    rPage.fill("input[name=password]", TEST_PASSWORD)
    rPage.click("button[type=submit]")
    rPage.wait_for_url(f"{server_url}/")

    yield rPage

    vContext.close()


@pytest.mark.parametrize("pPath", PAGES)
def test_pages_render_without_browser_errors(page, pPath):
    """Vérifie chaque page : réponse correcte, titre, aucune erreur ni blocage CSP."""

    vResponse = page.goto(pPath)

    assert vResponse.status == 200
    assert page.locator("h1").first.is_visible()
    assert page.console_errors == []


@pytest.mark.parametrize("pPath", PAGES)
def test_pages_fit_a_phone_screen(page, pPath):
    """Vérifie qu'aucune page ne défile horizontalement sur un téléphone."""

    page.set_viewport_size(PHONE_VIEWPORT)
    page.goto(pPath)

    vOverflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )

    assert vOverflow <= 1


def test_search_filters_offers_without_reload(page):
    """Vérifie la mise à jour de la liste par HTMX pendant la saisie."""

    page.goto("/offers")

    assert page.locator("#offers tbody tr").count() == 3

    page.fill("input[name=q]", "Python")
    # La CSP interdit d'évaluer du JavaScript : l'attente porte sur le sélecteur.
    sync_api.expect(page.locator("#offers tbody tr")).to_have_count(1)

    assert "q=Python" in page.url
    assert "Développeur Python" in page.locator("#offers").inner_text()


def test_theme_choice_is_remembered(page):
    """Vérifie que le thème choisi s'applique et reste après un rechargement."""

    page.goto("/settings")
    page.click("[data-theme-choice=dark]")

    assert page.evaluate("document.documentElement.dataset.theme") == "dark"

    page.reload()

    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


def test_card_collapse_is_remembered(page):
    """Vérifie qu'une carte repliée cache son contenu et le reste au rechargement."""

    page.goto("/quality")
    vCard = page.locator("article.card", has=page.locator("h2", has_text="Par source"))

    assert vCard.locator("p.card-subtitle").first.is_visible()

    vCard.locator(".card-toggle").click()

    assert not vCard.locator("p.card-subtitle").first.is_visible()

    page.reload()

    assert not vCard.locator("p.card-subtitle").first.is_visible()
    assert vCard.locator("h2").is_visible()


def test_calendar_address_is_created_and_served(page, server_url, browser):
    """Vérifie la création de l'adresse d'agenda et sa lecture sans session."""

    page.goto("/settings")
    page.get_by_role("button", name="Créer l'adresse").click()

    vUrl = page.locator("#calendar-url textarea").input_value()

    assert vUrl.startswith(f"{server_url}/calendar/")

    vAnonymous = browser.new_context()

    try:
        vResponse = vAnonymous.request.get(vUrl)

        assert vResponse.status == 200
        assert vResponse.text().startswith("BEGIN:VCALENDAR")

    finally:
        vAnonymous.close()


def test_schema_is_built_wired_and_graded_in_the_browser(page):
    """Vérifie l'éditeur de schéma : palette, câblage, déplacement et correction."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    import_questions(
        vDatabaseFile,
        "",
        json.dumps(
            {
                "theme": "Schémas de test",
                "questions": [
                    {
                        "id": "schema-test-moteur",
                        "level": "débutant",
                        "type": "construction",
                        "question": "Alimenter le moteur à travers un fusible.",
                        "explanation": "Le fusible protège la ligne du moteur.",
                        "components": [
                            {"type": "reseau", "x": 0, "y": 0},
                            {"type": "fusible", "x": 0, "y": 1},
                            {"type": "moteur", "x": 0, "y": 2},
                        ],
                        "connections": [
                            ["reseau", "sortie", "fusible", "1"],
                            ["fusible", "2", "moteur", "entrée"],
                        ],
                        "distractors": ["differentiel"],
                    }
                ],
            }
        ),
        datetime.now(),
    )

    page.goto("/quiz?theme=schemas-de-test&mode=discover")

    for vType in ("reseau", "fusible", "moteur"):
        page.click(f"[data-type={vType}]")

    assert page.locator("[data-type=fusible]").is_disabled()

    for vType, vPort in (
        ("reseau", "sortie"),
        ("fusible", "1"),
        ("fusible", "2"),
        ("moteur", "entrée"),
    ):
        page.locator(f'[data-component={vType}] [data-port="{vPort}"]').click()

    # Le moteur glisse d'une colonne vers la droite : ses fils le suivent.
    vMotor = page.locator("[data-component=moteur] .schema-frame").bounding_box()
    page.mouse.move(vMotor["x"] + 20, vMotor["y"] + 30)
    page.mouse.down()
    page.mouse.move(vMotor["x"] + 260, vMotor["y"] + 30, steps=5)
    page.mouse.up()

    vAnswer = json.loads(page.locator("[data-schema-answer]").input_value())

    assert {"id": "moteur", "type": "moteur", "x": 1, "y": 2} in vAnswer["components"]
    assert len(vAnswer["wires"]) == 2

    page.get_by_role("button", name="Valider").click()

    assert "Bonne réponse" in page.locator(".quiz-verdict").inner_text()
    assert page.locator(".schema-expected svg").count() == 1
    assert page.console_errors == []


def test_identical_components_are_numbered_in_the_browser(page):
    """Vérifie deux lampes identiques : numérotation, plafond et correction juste."""

    import_questions(
        app.dependency_overrides[get_database_file](),
        "",
        json.dumps(
            {
                "theme": "Schémas en double",
                "questions": [
                    {
                        "id": "schema-test-lampes",
                        "level": "débutant",
                        "type": "construction",
                        "question": "Alimenter deux points lumineux en parallèle.",
                        "explanation": "Chaque lampe reçoit la tension du réseau.",
                        "components": [
                            {"type": "reseau", "x": 0, "y": 0},
                            {"id": "l1", "type": "lampe", "x": 0, "y": 1},
                            {"id": "l2", "type": "lampe", "x": 1, "y": 1},
                        ],
                        "connections": [
                            ["reseau", "sortie", "l1", "entrée"],
                            ["reseau", "sortie", "l2", "entrée"],
                        ],
                    }
                ],
            }
        ),
        datetime.now(),
    )

    page.goto("/quiz?theme=schemas-en-double&mode=discover")
    page.click("[data-type=reseau]")
    page.click("[data-type=lampe]")

    assert "(1/2)" in page.locator("[data-type=lampe]").inner_text()

    page.click("[data-type=lampe]")

    assert page.locator("[data-type=lampe]").is_disabled()

    for vId in ("lampe-2", "lampe-1"):
        page.locator('[data-component=reseau] [data-port="sortie"]').click()
        page.locator(f'[data-component={vId}] [data-port="entrée"]').click()

    page.get_by_role("button", name="Valider").click()

    assert "Bonne réponse" in page.locator(".quiz-verdict").inner_text()
    assert page.console_errors == []


def test_offers_map_shows_placed_offers(page):
    """Vérifie le passage de la liste à la carte, ses pastilles et l'absence d'erreur."""

    # Fond de carte simulé : le test ne dépend pas d'Internet.
    page.route(
        "https://tile.openstreetmap.org/**",
        lambda pRoute: pRoute.fulfill(status=204),
    )
    page.goto("/offers?q=D%C3%A9veloppeur")
    page.click("button[value=map]")
    page.wait_for_url("**view=map**")

    assert "q=D%C3%A9veloppeur" in page.url
    sync_api.expect(page.locator(".leaflet-interactive")).to_have_count(2)
    assert "2 offre(s) placée(s) sur 2" in page.locator(".count").inner_text()

    page.locator(".leaflet-interactive").first.click(force=True)

    assert (
        page.locator(".leaflet-popup a")
        .first.get_attribute("href")
        .startswith("/offer?source=remotive")
    )
    assert page.console_errors == []
