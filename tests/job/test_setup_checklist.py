"""Tests de la liste des réglages restant à faire"""

from job.profile import load_profile, save_profile
from job.self_assessment import save_skill_levels
from job.settings import load_settings, save_settings
from job.setup_checklist import build_setup_checklist
from storage.database import initialize_database


def test_checklist_empties_as_settings_are_done(tmp_path, monkeypatch):
    """Vérifie que chaque réglage fait disparaît de la liste."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.delenv("FRANCE_TRAVAIL_ACCESS_GRANTED", raising=False)

    assert [vItem["page"] for vItem in build_setup_checklist(vDatabaseFile)] == [
        "profile",
        "profile",
        "settings",
        "logs",
        "logs",
    ]

    save_profile(vDatabaseFile, {**load_profile(vDatabaseFile), "skills": ["Java"]})
    save_skill_levels(vDatabaseFile, {"Java": 6})
    save_settings(
        vDatabaseFile, {**load_settings(vDatabaseFile), "target_net_salary": 2500}
    )

    assert [
        vItem["text"] for vItem in build_setup_checklist(vDatabaseFile, "/nas")
    ] == ["Demander l'accès à l'API France Travail"]
