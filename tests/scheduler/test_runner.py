"""Tests de l'exécution de la recherche planifiée"""

import smtplib
import threading
from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

import scheduler.runner as runner
from job.schedule import (
    load_schedule,
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from job.sources.aggregator import ScrapingCancelled
from storage.database import initialize_database

NOW = datetime(2026, 10, 10, 12, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une recherche planifiée active et une adresse."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_scheduled_search(rDatabaseFile, ["remotive"], {"keyword": "Java"})
    save_schedule_options(rDatabaseFile, True, 6)
    save_notification_email(rDatabaseFile, "moi@example.com")

    return rDatabaseFile


def build_items(*pNewFlags):
    """Construit des offres trouvées, nouvelles ou déjà connues."""

    rItems = pd.DataFrame(
        [
            {"title": f"Offre {vIndex}", "url": "https://example.com", "is_new": vNew}
            for vIndex, vNew in enumerate(pNewFlags)
        ],
        columns=["title", "url", "is_new"],
    )

    return rItems


@pytest.fixture
def sent_emails(monkeypatch):
    """Remplace l'envoi réel par une liste des e-mails envoyés."""

    rSent = []

    monkeypatch.setattr(runner, "send_email", lambda *pArgs: rSent.append(pArgs))

    return rSent


def test_run_due_search_runs_and_notifies(database_file, monkeypatch, sent_emails):
    """Vérifie le lancement, le déclencheur noté et l'e-mail des seules nouveautés."""

    vCalls = []

    def fake_process_jobs(pConfig, pCancelEvent=None, pTrigger=None):
        vCalls.append((pConfig, pTrigger))
        return SimpleNamespace(items=build_items(True, False))

    monkeypatch.setattr(runner, "process_jobs", fake_process_jobs)

    rResult = runner.run_due_search(database_file, NOW)

    vConfig, vTrigger = vCalls[0]

    assert rResult is not None
    assert vTrigger == "scheduled"
    assert vConfig.keyword == "Java"
    assert vConfig.sources["remotive"].enabled
    assert load_schedule(database_file)["last_run"] == NOW
    assert sent_emails[0][0] == "moi@example.com"
    assert "1 nouvelle(s) offre(s)" in sent_emails[0][1]
    assert "Offre 1" not in sent_emails[0][2]


def test_run_due_search_waits_for_next_run(database_file, monkeypatch):
    """Vérifie qu'aucune recherche n'est lancée avant l'échéance."""

    runner.mark_schedule_run(database_file, NOW)
    monkeypatch.setattr(runner, "process_jobs", pytest.fail)

    assert runner.run_due_search(database_file, NOW) is None


@pytest.mark.parametrize(
    "pEmail, pItems",
    [(None, build_items(True)), ("moi@example.com", build_items(False))],
)
def test_notify_new_offers_skips_email(sent_emails, pEmail, pItems):
    """Vérifie qu'aucun e-mail ne part sans adresse ou sans nouvelle offre."""

    vSchedule = {"email": pEmail, "search": None}

    assert runner.notify_new_offers(vSchedule, pItems) is False
    assert sent_emails == []


def test_notify_new_offers_reports_sending_failure(monkeypatch, caplog):
    """Vérifie qu'un échec d'envoi est journalisé sans interrompre le planificateur."""

    def refuse(*pArgs):
        raise smtplib.SMTPAuthenticationError(535, b"refus")

    monkeypatch.setattr(runner, "send_email", refuse)

    vSchedule = {"email": "moi@example.com", "search": None}

    assert runner.notify_new_offers(vSchedule, build_items(True)) is False
    assert "Échec de l'envoi" in caplog.text


@pytest.mark.parametrize("pError", [ScrapingCancelled(), RuntimeError("panne")])
def test_run_forever_survives_errors_until_stop(monkeypatch, pError):
    """Vérifie que la boucle continue après une erreur et s'arrête à la demande."""

    vStopEvent = threading.Event()
    vCalls = []

    def fake_run(pDatabaseFile, pNow, pCancelEvent):
        vCalls.append(pNow)

        if len(vCalls) == 2:
            vStopEvent.set()

        raise pError

    monkeypatch.setattr(runner, "run_due_search", fake_run)

    runner.run_forever("scraper.db", vStopEvent, pPollSeconds=0)

    assert len(vCalls) == 2
