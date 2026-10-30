"""Tests de l'export des données personnelles"""

import io
import json
import zipfile
from datetime import datetime

import pandas as pd

from job.personal_export import build_attachment_name, export_personal_data
from job.profile import EMPTY_PROFILE, save_profile
from storage.attachments import add_attachment
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers
from storage.settings_repository import save_setting_values

NOW = datetime(2026, 10, 24, 16, 0)


def test_export_contains_personal_data_but_no_secret(tmp_path):
    """Vérifie l'archive : candidature lisible, profil, pièce jointe, aucun jeton."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [{"source": "lever", "source_id": "1", "title": "Dev", "company": "Acme"}]
        ),
        NOW,
    )
    save_application(
        vDatabaseFile, "lever", "1", "APPLIED", pNotes="Appel RH", pNow=NOW
    )
    save_profile(vDatabaseFile, {**EMPTY_PROFILE, "skills": ["Python"]})
    save_setting_values(vDatabaseFile, {"mobile_api_token": "secret-du-telephone"})
    add_attachment(vDatabaseFile, "lever", "1", "CV Acme.pdf", b"%PDF-1.4", NOW)

    vBuffer = io.BytesIO()
    vCount = export_personal_data(vDatabaseFile, vBuffer, NOW)

    with zipfile.ZipFile(vBuffer) as vArchive:
        vNames = vArchive.namelist()
        vApplications = json.loads(vArchive.read("candidatures.json"))
        vSettings = json.loads(vArchive.read("reglages.json"))
        vContent = b"".join(vArchive.read(vName) for vName in vNames)
        vReadme = vArchive.read("LISEZMOI.txt").decode("utf-8")

    assert vCount == 13
    assert "tests_recrutement.json" in vNames
    assert "pieces_jointes/1-CV Acme.pdf" in vNames
    assert vApplications[0]["company"] == "Acme"
    assert vApplications[0]["notes"] == "Appel RH"
    assert vSettings["candidate_profile"]["skills"] == ["Python"]
    assert b"secret-du-telephone" not in vContent
    assert "24/10/2026" in vReadme


def test_attachment_name_is_made_safe():
    """Vérifie qu'un nom de fichier ne peut pas sortir du dossier des pièces jointes."""

    assert build_attachment_name(3, "../../lettre?.docx") == (
        "pieces_jointes/3-.._.._lettre_.docx"
    )
    assert build_attachment_name(4, None) == "pieces_jointes/4-piece-jointe"
