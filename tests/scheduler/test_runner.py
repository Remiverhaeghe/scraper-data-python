"""Tests de l'exécution de la recherche planifiée"""

import smtplib
import threading
from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

import scheduler.runner as runner
from job.profile import build_profile, save_profile
from job.schedule import (
    load_schedule,
    request_immediate_run,
    save_extra_searches,
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from job.sources.aggregator import ScrapingCancelled
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers
from storage.saved_searches import save_search

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
def test_notify_new_offers_skips_email(database_file, sent_emails, pEmail, pItems):
    """Vérifie qu'aucun e-mail ne part sans adresse ou sans nouvelle offre."""

    vSchedule = {"email": pEmail, "search": None, "min_score": 0}

    assert runner.notify_new_offers(database_file, vSchedule, pItems) is False
    assert sent_emails == []


def test_notify_new_offers_reports_sending_failure(database_file, monkeypatch, caplog):
    """Vérifie qu'un échec d'envoi est journalisé sans interrompre le planificateur."""

    def refuse(*pArgs):
        raise smtplib.SMTPAuthenticationError(535, b"refus")

    monkeypatch.setattr(runner, "send_email", refuse)

    vSchedule = {"email": "moi@example.com", "search": None, "min_score": 0}

    assert (
        runner.notify_new_offers(database_file, vSchedule, build_items(True)) is False
    )
    assert "Échec de l'envoi" in caplog.text


@pytest.mark.parametrize("pError", [ScrapingCancelled(), RuntimeError("panne")])
def test_run_forever_survives_errors_until_stop(monkeypatch, tmp_path, pError):
    """Vérifie que la boucle continue après une erreur et s'arrête à la demande."""

    vStopEvent = threading.Event()
    vCalls = []

    def fake_run(pDatabaseFile, pNow, pCancelEvent):
        vCalls.append(pNow)

        if len(vCalls) == 2:
            vStopEvent.set()

        raise pError

    vTasks = []

    monkeypatch.setattr(runner, "run_due_search", fake_run)
    monkeypatch.setattr(
        runner,
        "BACKGROUND_TASKS",
        (("test", lambda pDatabaseFile, pNow: vTasks.append(pNow)),),
    )

    runner.run_forever(tmp_path / "scraper.db", vStopEvent, pPollSeconds=0)

    assert len(vCalls) == 2
    assert len(vTasks) == 2
    assert (tmp_path / "scheduler.heartbeat").exists()


def test_run_due_search_handles_web_request(database_file, monkeypatch, sent_emails):
    """Vérifie qu'une demande du web lance la recherche, planification désactivée."""

    save_schedule_options(database_file, False, 6)
    runner.mark_schedule_run(database_file, NOW)
    request_immediate_run(database_file, NOW)

    monkeypatch.setattr(
        runner,
        "process_jobs",
        lambda pConfig, pCancelEvent=None, pTrigger=None: SimpleNamespace(
            items=build_items(False)
        ),
    )

    assert runner.run_due_search(database_file, NOW) is not None
    assert load_schedule(database_file)["run_requested"] is None


def test_notify_follow_ups_once_a_day(database_file, sent_emails):
    """Vérifie le rappel des relances dues, envoyé une seule fois par jour."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Java",
                    "company": "Acme",
                    "url": "https://acme.example",
                }
            ]
        ),
        NOW,
    )
    vSchedule = load_schedule(database_file)

    assert runner.notify_follow_ups(database_file, vSchedule, NOW) is False

    save_application(
        database_file, "remotive", "1", "APPLIED", pFollowUpDate=NOW, pNow=NOW
    )

    assert runner.notify_follow_ups(database_file, vSchedule, NOW) is True
    assert sent_emails[0][1] == "JobBoard Perso : 1 relance(s) à faire"
    assert "Acme · relance prévue le 10/10/2026" in sent_emails[0][2]
    assert runner.notify_follow_ups(database_file, vSchedule, NOW) is False
    assert len(sent_emails) == 1


def build_scored_items():
    """Construit trois nouvelles offres plus ou moins proches d'un profil Java.

    Trois compétences par offre : le score est rapporté à trois au minimum.
    """

    rItems = pd.DataFrame(
        [
            {"title": "Développeur Java SQL", "url": "https://example.com/1"},
            {"title": "Développeur Java PHP", "url": "https://example.com/2"},
            {"title": "Développeur PHP", "url": "https://example.com/3"},
        ]
    ).assign(
        is_new=True,
        skills=[
            ["Java", "SQL", "Git"],
            ["Java", "PHP", "Git"],
            ["PHP", "Symfony", "Docker"],
        ],
    )

    return rItems


def test_notify_new_offers_keeps_offers_above_min_score(database_file, sent_emails):
    """Vérifie que seules les offres assez proches du profil sont envoyées, triées."""

    save_profile(database_file, build_profile("", "", "Java, SQL, Git", "", ""))
    vSchedule = {"email": "moi@example.com", "search": None, "min_score": 50}

    assert runner.notify_new_offers(database_file, vSchedule, build_scored_items())

    vSubject, vText = sent_emails[0][1], sent_emails[0][2]

    assert "2 nouvelle(s) offre(s)" in vSubject
    assert vText.index("Java SQL") < vText.index("Java PHP")
    assert "correspondance 100 %" in vText
    assert "Développeur PHP" not in vText


def test_notify_new_offers_skips_email_below_min_score(
    database_file, sent_emails, caplog
):
    """Vérifie qu'aucun e-mail ne part quand aucune offre n'atteint le score."""

    save_profile(database_file, build_profile("", "", "Python", "", ""))
    vSchedule = {"email": "moi@example.com", "search": None, "min_score": 90}

    assert not runner.notify_new_offers(database_file, vSchedule, build_scored_items())
    assert sent_emails == []
    assert "au-dessus du score minimal" in caplog.text


def test_notify_new_offers_ignores_min_score_without_profile(
    database_file, sent_emails, caplog
):
    """Vérifie que tout est envoyé, avec un avertissement, sans profil renseigné."""

    vSchedule = {"email": "moi@example.com", "search": None, "min_score": 70}

    assert runner.notify_new_offers(database_file, vSchedule, build_scored_items())
    assert "3 nouvelle(s) offre(s)" in sent_emails[0][1]
    assert "aucune compétence dans le profil" in caplog.text


def test_run_due_search_runs_extra_searches(database_file, monkeypatch, sent_emails):
    """Vérifie l'enchaînement des recherches, l'échec isolé et un seul e-mail."""

    save_search(database_file, "Python", ["remotive"], {"keyword": "Python"}, NOW)
    save_search(database_file, "Go", ["remotive"], {"keyword": "Go"}, NOW)
    save_extra_searches(database_file, ["Python", "Go"])

    vKeywords = []

    def fake_process_jobs(pConfig, pCancelEvent=None, pTrigger=None):
        vKeywords.append(pConfig.keyword)

        if pConfig.keyword == "Python":
            raise RuntimeError("source en panne")

        return SimpleNamespace(
            items=pd.DataFrame(
                [{"title": f"Offre {pConfig.keyword}", "url": None, "is_new": True}]
            )
        )

    monkeypatch.setattr(runner, "process_jobs", fake_process_jobs)

    rResults = runner.run_due_search(database_file, NOW)

    assert vKeywords == ["Java", "Python", "Go"]
    assert len(rResults) == 2
    assert len(sent_emails) == 1
    assert "2 nouvelle(s) offre(s)" in sent_emails[0][1]


def test_merge_items_keeps_the_new_version():
    """Vérifie qu'une offre trouvée deux fois garde sa version nouvelle."""

    vFirst = pd.DataFrame(
        [{"title": "A", "url": "https://a", "is_new": False}],
    )
    vSecond = pd.DataFrame(
        [
            {"title": "A", "url": "https://a", "is_new": True},
            {"title": "B", "url": "https://b", "is_new": True},
        ]
    )

    rItems = runner.merge_items([vFirst, pd.DataFrame(), vSecond])

    assert rItems["title"].tolist() == ["A", "B"]
    assert rItems["is_new"].tolist() == [True, True]


def test_failing_task_does_not_stop_the_others(caplog):
    """Vérifie qu'une tâche en échec est journalisée et que la suivante s'exécute."""

    vCalls = []

    def fail(pDatabaseFile, pNow):
        raise OSError("disque plein")

    runner.run_background_tasks(
        "base",
        NOW,
        (("en échec", fail), ("suivante", lambda *pArgs: vCalls.append(pArgs))),
    )

    assert vCalls == [("base", NOW)]
    assert "Échec de la tâche « en échec » : disque plein" in caplog.text


def test_web_certificate_is_renewed_only_in_https(monkeypatch):
    """Vérifie que le renouvellement du certificat ne concerne que le HTTPS."""

    vCalls = []
    monkeypatch.setattr(
        runner, "renew_certificate_if_due", lambda *pArgs: vCalls.append(pArgs)
    )
    monkeypatch.setattr(runner, "WEB_SCHEME", "http")
    runner.renew_web_certificate("scraper.db", datetime(2026, 10, 23))

    assert not vCalls

    monkeypatch.setattr(runner, "WEB_SCHEME", "https")
    monkeypatch.setattr(runner, "WEB_PUBLIC_HOST", "serveur.chat-tigre.ts.net")
    runner.renew_web_certificate("scraper.db", datetime(2026, 10, 23))

    assert vCalls[0][0] == "serveur.chat-tigre.ts.net"
