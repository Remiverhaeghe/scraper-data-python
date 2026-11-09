"""Tests web des réglages, des sauvegardes, des journaux et de la sécurité"""

from datetime import datetime
import io
import re
import zipfile

import pytest

from job.schedule import (
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from storage.backup import backup_database, copy_to_nas
import job.page_timings as page_timings
import storage.backup as storage_backup
import web.routes.settings as web_settings


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


def test_slow_page_is_logged_without_its_parameters(client, monkeypatch, caplog):
    """Vérifie qu'une page lente est signalée par son chemin seul."""

    monkeypatch.setattr(page_timings, "SLOW_PAGE_SECONDS", -1)

    client.get("/offers?keyword=secret")

    vMessages = [
        vRecord.getMessage()
        for vRecord in caplog.records
        if vRecord.name == "job.page_timings"
    ]

    assert any(
        vMessage.startswith("Page lente : site /offers en") for vMessage in vMessages
    )
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


def test_alerts_min_score_is_saved(client, tmp_path):
    """Vérifie l'enregistrement du score minimal des alertes et le refus d'un autre."""

    vResponse = client.post("/settings/alerts", data={"min_score": "70"})

    assert vResponse.status_code == 200
    assert "Alertes enregistrées." in vResponse.text
    assert 'value="70" selected' in vResponse.text
    assert client.post("/settings/alerts", data={"min_score": "42"}).status_code == (
        400
    )


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


def test_dashboard_lists_settings_to_do(client):
    """Vérifie la carte À faire de l'accueil, avec le lien vers chaque réglage."""

    vPage = client.get("/").text

    assert "À faire pour bien démarrer" in vPage
    assert '<a href="/settings">' in vPage


def test_unknown_place_is_corrected_from_the_quality_page(client, monkeypatch):
    """Vérifie la correction d'un lieu depuis la page Qualité."""

    monkeypatch.setattr(
        "web.routes.monitoring.resolve_place",
        lambda pDatabaseFile, pKey, pCommune: "Roubaix",
    )

    assert "Lieux introuvables" in client.get("/quality").text

    vPage = client.post("/quality/place", data={"key": "x", "commune": "Roubaix"}).text

    assert "Lieu associé à Roubaix" in vPage
