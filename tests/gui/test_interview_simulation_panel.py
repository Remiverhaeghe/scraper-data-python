"""Tests du panneau de simulation d'entretien"""

from gui.interview_simulation_panel import InterviewSimulationPanel
from job.interview_simulation import SIMULATION_SIZE
from storage.database import initialize_database


def test_simulation_is_run_from_the_panel(qt_application, tmp_path):
    """Vérifie une série : question, réponse révélée, points cochés et bilan."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = InterviewSimulationPanel(vDatabaseFile)
    vPanel.refresh()

    assert vPanel.question is None
    assert vPanel.stop_button.isHidden()

    vPanel.theme_combo.setCurrentText("Android")
    vPanel.start_button.click()

    assert vPanel.position_label.text() == "Android · question 1 sur 5"
    assert vPanel.next_button.isHidden()

    for _ in range(SIMULATION_SIZE):
        vPanel.reveal_button.click()

        assert not vPanel.model_label.isHidden()

        for vCheck in vPanel.point_checks:
            vCheck.setChecked(True)

        vPanel.next_button.click()

    assert vPanel.position_label.text() == "Série terminée"
    assert vPanel.question_label.text().startswith("Score : 100 %")
    assert vPanel.history_label.text() == "Dernières séries : Android 100 %"

    vPanel.stop_button.click()

    assert vPanel.stop_button.isHidden()
