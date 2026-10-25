"""Tests de l'état de santé de l'application"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

import job.health as health
from job.health import build_health, find_silent_sources, format_age
from job.geocoding import HOME_KEY
from job.mobile_sync import build_offer_list, renew_mobile_token
from job.schedule import (
    get_scheduler_heartbeat,
    mark_schedule_run,
    mark_scheduler_alive,
    save_schedule_options,
    save_scheduled_search,
)
from scraper.history import HistoryEntry
from storage.backup import backup_database
from storage.database import initialize_database
from storage.history_repository import save_history
from storage.job_offers import save_offers
from storage.settings_repository import save_json_setting
from utils.tls import create_certificate, read_expiry

NOW = datetime(2026, 10, 19, 12, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def get_checks(pDatabaseFile):
    """Retourne les indicateurs indexés par libellé."""

    rChecks = {
        vCheck["label"]: (vCheck["value"], vCheck["tone"])
        for vCheck in build_health(pDatabaseFile, NOW)
    }

    return rChecks


def test_health_of_a_new_database(database_file):
    """Vérifie les indicateurs d'une base neuve : rien n'a encore eu lieu."""

    vChecks = get_checks(database_file)

    assert vChecks["Sauvegarde automatique"] == (
        "Aucune sauvegarde automatique",
        "warning",
    )
    assert vChecks["Recherche planifiée"] == ("Désactivée", "muted")
    assert vChecks["Dernière recherche"][1] == "muted"
    assert vChecks["Place occupée"][0].startswith("Base ")


def test_health_reports_late_schedule_and_recent_backup(database_file):
    """Vérifie la sauvegarde récente et la planification en retard."""

    backup_database(database_file, NOW - timedelta(days=1), "auto")
    save_scheduled_search(database_file, ["remotive"], {})
    save_schedule_options(database_file, True, 6)
    mark_schedule_run(database_file, NOW - timedelta(hours=13))

    vChecks = get_checks(database_file)

    assert vChecks["Sauvegarde automatique"] == ("18/10/2026 12:00 (hier)", "success")
    assert vChecks["Recherche planifiée"][1] == "warning"
    assert "en retard" in vChecks["Recherche planifiée"][0]


def test_unreadable_check_does_not_hide_the_others(database_file, monkeypatch):
    """Vérifie qu'un indicateur en erreur est signalé sans masquer les autres."""

    def fail():
        raise OSError("disque")

    monkeypatch.setattr(health, "check_sources", fail)

    vChecks = get_checks(database_file)

    assert vChecks["Sources"] == ("Illisible : voir les journaux", "danger")
    assert len(vChecks) == 19
    assert format_age(NOW - timedelta(days=5), NOW) == "il y a 5 jours"


def test_silent_source_is_reported_after_three_empty_runs():
    """Vérifie qu'une source qui renvoyait des offres et n'en renvoie plus est repérée."""

    def run(**pCounts):
        return SimpleNamespace(parameters={"source_counts": pCounts})

    vHistory = [
        run(adzuna=0, remotive=4),
        run(adzuna=0, remotive=0),
        SimpleNamespace(parameters={"keyword": "java"}),
        run(adzuna=0, remotive=3),
        run(adzuna=12, remotive=5),
    ]

    assert find_silent_sources(vHistory) == ["adzuna"]
    # Une source jamais productive n'est pas « cassée » : rien ne la distingue.
    assert find_silent_sources([run(jooble=0)] * 5) == []


def test_certificate_end_is_reported(tmp_path, monkeypatch):
    """Vérifie les jours restants du certificat, en couleur selon l'urgence."""

    vCertificate = tmp_path / "certificate.pem"
    create_certificate("127.0.0.1", vCertificate, tmp_path / "key.pem", NOW)
    vExpiry = read_expiry(vCertificate)

    assert health.check_certificate(NOW) == ("HTTP, sans certificat", "muted")
    assert health.check_certificate(NOW, vCertificate)[1] == "success"
    assert (
        health.check_certificate(vExpiry - timedelta(days=20), vCertificate)[1]
        == "warning"
    )
    assert health.check_certificate(vExpiry + timedelta(days=1), vCertificate) == (
        f"Valable jusqu'au {vExpiry:%d/%m/%Y} (0 jours)",
        "danger",
    )
    assert health.check_certificate(NOW, tmp_path / "absent.pem")[1] == "danger"


def test_geocoding_and_phone_checks(database_file):
    """Vérifie le placement des offres et la dernière synchronisation du téléphone."""

    vChecks = get_checks(database_file)

    assert vChecks["Placement des offres"][1] == "muted"
    assert vChecks["Application mobile"] == ("Application mobile non reliée", "muted")

    save_json_setting(
        database_file,
        HOME_KEY,
        {"address": "Lille", "label": "Lille", "latitude": 50.6, "longitude": 3.0},
    )
    renew_mobile_token(database_file)

    vChecks = get_checks(database_file)

    assert vChecks["Placement des offres"] == (
        "0 offre(s) placée(s) sur 0 en France",
        "success",
    )
    assert vChecks["Application mobile"] == ("Jamais synchronisée", "warning")

    build_offer_list(database_file, NOW - timedelta(hours=3))

    assert get_checks(database_file)["Application mobile"][1] == "success"


def test_backup_integrity_check(database_file):
    """Vérifie l'indicateur des sauvegardes vérifiées, puis d'une endommagée."""

    vBackupFile = backup_database(database_file, NOW, "auto")

    assert get_checks(database_file)["Sauvegarde vérifiée"][1] == "success"

    vBackupFile.rename(vBackupFile.with_name(vBackupFile.name + ".endommagee"))

    vValue, vTone = get_checks(database_file)["Sauvegarde vérifiée"]

    assert vTone == "danger"
    assert vValue.startswith("1 sauvegarde(s) endommagée(s)")


def test_last_run_partial_and_success(database_file):
    """Vérifie la dernière recherche réussie, puis partielle avec sa source en erreur."""

    def save_run(pStatus, pError=None, pHour=8):
        save_history(
            database_file,
            HistoryEntry(
                started_at=datetime(2026, 10, 19, pHour, 30),
                scraper_type="job",
                url="multi-source",
                page_count=2,
                item_count=42,
                duration_seconds=3.0,
                status=pStatus,
                error_message=pError,
            ),
        )

    save_run("success")

    assert get_checks(database_file)["Dernière recherche"] == (
        "19/10/2026 08:30 : 42 offre(s)",
        "success",
    )

    save_run("partial", "Careerjet : adresse IP 192.0.2.7 refusée", 9)
    vValue, vTone = get_checks(database_file)["Dernière recherche"]

    assert vTone == "warning"
    assert vValue.endswith(
        "source(s) en erreur : Careerjet : adresse IP 192.0.2.7 refusée"
    )


def test_gmail_and_description_checks(database_file, monkeypatch):
    """Vérifie l'indicateur Gmail, sans puis avec configuration, et les descriptions."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)

    assert get_checks(database_file)["Réponses Gmail"][1] == "muted"

    monkeypatch.setenv("GMAIL_ADDRESS", "moi@exemple.fr")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret")
    save_json_setting(database_file, "last_reply_check", "2026-10-19T09:00:00")

    vValue, vTone = get_checks(database_file)["Réponses Gmail"]

    assert vTone == "success"
    assert vValue.startswith("Lu aujourd'hui à 09:00")
    assert get_checks(database_file)["Descriptions"][1] == "success"


def test_scheduler_check_follows_the_heartbeat(tmp_path):
    """Vérifie l'indicateur du planificateur : jamais vu, en marche, puis arrêté."""

    vDatabaseFile = tmp_path / "scraper.db"

    assert health.check_scheduler(vDatabaseFile, NOW)[1] == "warning"

    mark_scheduler_alive(vDatabaseFile)
    vNow = datetime.now()

    assert health.check_scheduler(vDatabaseFile, vNow)[1] == "success"
    assert health.check_scheduler(vDatabaseFile, vNow + timedelta(hours=1)) == (
        f"Arrêté depuis le {get_scheduler_heartbeat(vDatabaseFile):%d/%m/%Y %H:%M} "
        ": les tâches de fond attendent",
        "danger",
    )


def test_format_changes_name_the_source_and_the_field():
    """Vérifie le signalement d'un champ vide pour plus de la moitié des offres."""

    vCounts = [
        {
            "source": "labonnealternance",
            "total": 85,
            "title": 0,
            "location": 85,
            "company": 8,
        },
        {"source": "adzuna", "total": 1000, "title": 0, "location": 0, "company": 70},
        {"source": "remotive", "total": 4, "title": 4, "location": 4, "company": 4},
    ]

    assert health.find_format_changes(vCounts) == [
        "La bonne alternance : lieu vide pour 100 %"
    ]


def test_source_formats_check_reads_recent_offers(tmp_path):
    """Vérifie l'indicateur sur une base : source propre, puis lieu disparu."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert health.check_source_formats(vDatabaseFile, NOW)[1] == "success"

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": str(vIndex), "title": "Dev"}
                for vIndex in range(12)
            ]
        ),
        NOW,
    )

    assert health.check_source_formats(vDatabaseFile, NOW)[0].startswith(
        "Lever : lieu vide pour 100 %"
    )
