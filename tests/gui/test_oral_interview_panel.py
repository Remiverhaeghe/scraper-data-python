"""Tests du panneau d'entretien oral simulé"""

import pytest

from gui.oral_interview_panel import OralInterviewPanel, format_clock
from gui.speech import Speaker
from job.oral_interview import SESSION_LENGTH, load_oral
from storage.database import initialize_database


@pytest.mark.parametrize(
    "pSeconds, pExpected", [(90, "1:30"), (5.7, "0:05"), (-12, "-0:12")]
)
def test_clock_is_formatted(pSeconds, pExpected):
    """Vérifie l'affichage du chrono, négatif une fois le temps dépassé."""

    assert format_clock(pSeconds) == pExpected


def test_speaker_without_voice_ends_at_once(qt_application):
    """Vérifie qu'une lecture impossible rend la main aussitôt."""

    vSpeaker = Speaker()
    vEnded = []
    vSpeaker.finished.connect(lambda: vEnded.append(True))

    vSpeaker.speak("Bonjour")

    assert not vSpeaker.is_available() and vEnded == [True]


def test_oral_session_is_played_and_summed_up(qt_application, tmp_path):
    """Vérifie une séance : chrono lancé, note manquante refusée, bilan et progression."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = OralInterviewPanel(vDatabaseFile)
    vPanel.refresh()

    assert "Aucune séance" in vPanel.progress_label.text()

    vPanel.start()

    for vPosition in range(SESSION_LENGTH):
        assert vPanel.question_label.text().startswith(f"Question {vPosition + 1} sur")
        assert vPanel.timer.isActive()

        vPanel.finish_answer()

        if vPosition == 0:
            vPanel.validate()

            assert vPanel.message_label.text() == "Notez la structure et l'exemple."

        for vGroup in vPanel.rating_groups.values():
            vGroup.button(2).setChecked(True)

        vPanel.validate()

        assert vPanel.message_label.text().startswith("Réponse notée")

        vPanel.next_button.click()

    assert len(load_oral(vDatabaseFile)["history"]) == 1
    assert vPanel.progress_label.text().startswith("1 séance(s)")
    assert not vPanel.start_widget.isHidden()
