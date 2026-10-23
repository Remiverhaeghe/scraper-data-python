"""Tests du panneau d'auto-évaluation"""

from gui.self_assessment_panel import SelfAssessmentPanel
from job.profile import load_profile
from storage.database import initialize_database


def test_levels_are_entered_added_and_saved(qt_application, tmp_path):
    """Vérifie la saisie des niveaux, l'ajout d'une compétence et l'enregistrement."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = SelfAssessmentPanel(vDatabaseFile)
    vPanel.refresh()

    vPanel.spins["Java"].setValue(8)
    vPanel.new_skill_edit.setText("Kafka")
    vPanel.add_skill()
    vPanel.new_skill_edit.setText("kafka")
    vPanel.add_skill()
    vPanel.spins["Kafka"].setValue(3)
    vPanel.save()

    assert load_profile(vDatabaseFile)["skill_levels"] == {"Java": 8, "Kafka": 3}
    assert vPanel.message_label.text() == "2 compétence(s) notée(s)."
    assert vPanel.spins["Kafka"].value() == 3
