"""Tests de l'état de santé de l'application"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import job.health as health
from job.health import build_health, find_silent_sources, format_age
from job.geocoding import HOME_KEY
from job.mobile_sync import build_offer_list, renew_mobile_token
from job.schedule import mark_schedule_run, save_schedule_options, save_scheduled_search
from storage.backup import backup_database
from storage.database import initialize_database
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
    assert len(vChecks) == 13
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
