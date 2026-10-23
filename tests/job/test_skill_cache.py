"""Tests des compétences repérées une fois puis lues en base"""

from datetime import datetime

import pandas as pd

import job.skill_cache as skill_cache
from job.preparation import get_offer_skills
from job.skill_cache import SKILLS_VERSION_KEY, refresh_detected_skills
from storage.database import initialize_database
from storage.job_offers import get_offers, save_offers
from storage.settings_repository import get_setting_values

NOW = datetime(2026, 10, 23, 12)


def save_offer(pDatabaseFile, pDescription):
    """Enregistre l'offre lever/1 avec cette description."""

    save_offers(
        pDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Développeur",
                    "description": pDescription,
                }
            ]
        ),
        NOW,
    )


def read_offer(pDatabaseFile):
    """Relit l'offre lever/1 telle que la liste des offres la reçoit."""

    rOffer = get_offers(pDatabaseFile).to_dict("records")[0]

    return rOffer


def test_skills_are_detected_once_then_read(tmp_path, monkeypatch):
    """Vérifie l'analyse, la lecture en base et le recalcul d'un texte modifié."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offer(vDatabaseFile, "Java et SQL")

    assert refresh_detected_skills(vDatabaseFile) == 1
    assert refresh_detected_skills(vDatabaseFile) == 0
    assert get_setting_values(vDatabaseFile)[SKILLS_VERSION_KEY] == (
        skill_cache.SKILLS_VERSION
    )

    # Lu en base : la détection n'est plus appelée.
    monkeypatch.setattr("job.preparation.detect_skills", lambda pText: ["Faux"])

    assert get_offer_skills(read_offer(vDatabaseFile)) == ["Java", "SQL"]

    # Même texte : le résultat reste ; texte modifié : il est à recalculer.
    save_offer(vDatabaseFile, "Java et SQL")

    assert read_offer(vDatabaseFile)["detected_skills"] == '["Java", "SQL"]'

    save_offer(vDatabaseFile, "Python")

    assert get_offer_skills(read_offer(vDatabaseFile)) == ["Faux"]


def test_new_dictionary_reanalyses_every_offer(tmp_path, monkeypatch):
    """Vérifie qu'un dictionnaire modifié relance l'analyse de toutes les offres."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offer(vDatabaseFile, "Java")
    refresh_detected_skills(vDatabaseFile)

    monkeypatch.setattr(skill_cache, "SKILLS_VERSION", "nouvelle")

    assert refresh_detected_skills(vDatabaseFile) == 1


def test_failure_is_logged_without_stopping(tmp_path, monkeypatch, caplog):
    """Vérifie qu'une erreur d'analyse est journalisée sans être relevée."""

    def fail(*_pArgs):
        raise OSError("disque")

    monkeypatch.setattr(skill_cache, "refresh_detected_skills", fail)

    skill_cache.refresh_detected_skills_safely(tmp_path / "scraper.db")

    assert "Échec de l'analyse des compétences" in caplog.text
