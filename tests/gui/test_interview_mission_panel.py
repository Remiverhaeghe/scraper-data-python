"""Tests du panneau de mission d'entretien de l'assistant d'offre"""

from PySide6.QtWidgets import QCheckBox

from gui.interview_mission_panel import InterviewMissionPanel
from job.interview_mission import load_missions
from job.profile import load_profile, save_profile
from storage.database import initialize_database

OFFER = {"source": "lever", "source_id": "1", "title": "Dev Python", "company": "Acme"}


def test_mission_is_hidden_without_profile_then_ticked(qt_application, tmp_path):
    """Vérifie le panneau masqué sans profil, puis une étape cochée et décochée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = InterviewMissionPanel(vDatabaseFile)

    vPanel.set_offer(OFFER)

    assert vPanel.isHidden()

    save_profile(vDatabaseFile, {**load_profile(vDatabaseFile), "skills": ["Python"]})
    vPanel.set_offer(OFFER)

    assert not vPanel.isHidden()
    assert vPanel.title_label.text().startswith("Mission entretien · ")

    vChecks = [
        vWidget
        for vWidget in vPanel.findChildren(QCheckBox)
        if vWidget.text().startswith("Pitch")
    ]
    vChecks[-1].setChecked(True)

    assert "pitch" in load_missions(vDatabaseFile)["lever/1"]["steps"]

    vPanel.set_offer(None)

    assert vPanel.isHidden()
