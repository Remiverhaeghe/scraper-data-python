"""Tests web du tableau de bord, de la progression et du planning"""

from datetime import date, datetime
import re

import pandas as pd

from job.progress import build_progress
from job.schedule import save_scheduled_search
from job.season_review import build_season_review
from job.weekly_planning import load_planned_revisions
from storage.job_offers import save_offers
from web.app import app, get_database_file

from tests.web.helpers import build_offer


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


def test_dashboard_shows_the_mascot(client):
    """Vérifie la mascotte du tableau de bord : dessin, humeur et phrase."""

    vPage = client.get("/").text

    assert 'class="card mascot"' in vPage
    assert "<title>Boulon, robot de maintenance</title>" in vPage
    assert 'class="mascot-bubble">' in vPage


def test_focus_session_is_started_and_stopped_on_the_dashboard(client):
    """Vérifie la session de concentration du tableau de bord : début, anneau, arrêt."""

    assert 'id="focus"' in client.get("/").text
    assert client.post("/focus/start", data={"goal": "x"}).status_code == 400

    vRunning = client.post("/focus/start", data={"goal": "revise"}).text

    assert "data-focus-ring" in vRunning and "Objectif : Réviser" in vRunning
    assert client.post("/focus/start", data={"goal": "revise"}).status_code == 400

    vStopped = client.post("/focus/stop").text

    assert "Session arrêtée avant la fin : pas de bonus." in vStopped


def test_start_quests_and_tour_on_the_web(client):
    """Vérifie les premiers pas du tableau de bord et la visite, étape par étape."""

    vDashboard = client.get("/").text

    assert "Premiers pas · " in vDashboard and "/tour" in vDashboard

    vFirst = client.get("/tour").text
    vLast = client.get("/tour?step=99").text

    assert (
        "Bienvenue" in vFirst
        and "Étape 1 sur 7" in vFirst
        and "Précédent" not in vFirst
    )
    assert "Paramètres" in vLast and "Terminer" in vLast and 'href="/settings"' in vLast


def test_planning_lists_moves_and_plans_revisions(client):
    """Vérifie le planning web : semaine, révision ajoutée, déplacée puis retirée."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()

    assert "Rien de prévu" in client.get("/planning").text
    assert client.get("/planning?week=hier").status_code == 400
    assert (
        client.post(
            "/planning/revision", data={"day": "2026-10-27", "label": " "}
        ).status_code
        == 400
    )

    vPage = client.post(
        "/planning/revision", data={"day": "2026-10-27", "label": "Hydraulique"}
    ).text
    vRevision = load_planned_revisions(vDatabaseFile)[0]["id"]

    assert "Réviser : Hydraulique" in vPage and "Mardi 27/10" in vPage

    vMoved = client.post(
        "/planning/move",
        data={"item": f"revision|{vRevision}", "day": "2026-10-29"},
        headers={"X-Requested-With": "fetch"},
    )

    assert vMoved.status_code == 204
    assert load_planned_revisions(vDatabaseFile)[0]["day"] == "2026-10-29"
    assert (
        client.post(
            "/planning/move", data={"item": "x|y", "day": "2026-10-29"}
        ).status_code
        == 400
    )

    client.post(
        "/planning/revision/delete", data={"revision": vRevision, "week": "2026-10-26"}
    )

    assert load_planned_revisions(vDatabaseFile) == []


def test_rewards_are_chosen_on_the_progress_page(client):
    """Vérifie les récompenses : verrouillée refusée, choix, son coupé, encart du menu."""

    vPage = client.get("/progress").text

    assert 'id="rewards"' in vPage and "Vert sécurité · niveau 2" in vPage
    assert (
        client.post("/progress/reward", data={"kind": "accent", "id": "or"}).status_code
        == 400
    )

    client.post("/progress/reward", data={"kind": "accent", "id": "bleu"})
    vSummary = client.get("/progress/summary").text

    assert 'data-accent="bleu"' in vSummary and 'data-sounds="1"' in vSummary
    assert "Activer le son de réussite" in client.post("/progress/sounds").text
    assert 'data-sounds="0"' in client.get("/progress/summary").text


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
    assert "sans activité" in vPage.text


def test_progress_page_shows_the_season_review(client, monkeypatch):
    """Vérifie le bilan de la semaine écoulée sur la page Progression."""

    monkeypatch.setattr(
        "web.routes.progress.build_progress",
        lambda *pArgs: {
            **build_progress(app.dependency_overrides[get_database_file]()),
            "season": build_season_review(
                {date(2026, 10, 28): {"xp": 250, "actions": {"daily_quest": 9}}},
                date(2026, 11, 2),
                22,
            ),
        },
    )

    vPage = client.get("/progress").text

    assert "Saison 44" in vPage and "du 26/10/2026 au 01/11/2026" in vPage
    assert "Médaille d&#39;argent : 9 quêtes sur 22" in vPage
    assert "Meilleur jour : le 28/10/2026, 250 XP" in vPage


def test_certifications_page_saves_details_and_documents(client):
    """Vérifie la page, l'enregistrement, le document joint puis sa suppression."""

    assert "Habilitation électrique" in client.get("/certifications").text

    vSaved = client.post(
        "/certifications/save",
        data={
            "id": "sst",
            "owned": "1",
            "obtained": "2025-06-02",
            "organism": "INRS <script>",
            "number": "SST-42",
        },
        follow_redirects=False,
    )

    assert vSaved.headers["location"] == "/certifications#cert-sst"

    vUploaded = client.post(
        "/certifications/documents",
        data={"id": "sst"},
        files={"file": ("carte SST.jpg", b"JPEG", "image/jpeg")},
        follow_redirects=False,
    )

    assert vUploaded.status_code == 303

    vPage = client.get("/certifications").text
    vAttachmentId = re.search(r"/attachment\?id=(\d+)", vPage).group(1)

    assert "carte SST.jpg" in vPage
    assert "SST-42" in vPage
    assert "INRS &lt;script&gt;" in vPage
    assert "Valide jusqu&#39;au 02/06/2027" in vPage

    vDeleted = client.post(
        "/attachment/delete", data={"id": vAttachmentId}, follow_redirects=False
    )

    assert vDeleted.headers["location"] == "/certifications#cert-sst"
    assert (
        client.post(
            "/certifications/save", data={"id": "sst", "verify_link": "javascript:x"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/certifications/documents",
            data={"id": "inconnue"},
            files={"file": ("a.pdf", b"%PDF", "application/pdf")},
        ).status_code
        == 404
    )
