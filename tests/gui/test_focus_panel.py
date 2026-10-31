"""Tests de la session de concentration de l'accueil"""

from datetime import datetime, timedelta

import gui.focus_panel as focus_panel
from gui.focus_panel import FocusPanel, format_remaining
from job.focus_sessions import load_focus
from storage.database import initialize_database


def test_remaining_time_is_formatted():
    """Vérifie l'affichage du temps restant."""

    assert format_remaining(25 * 60) == "25:00"
    assert format_remaining(65) == "01:05"


def test_session_is_started_followed_then_summed_up(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie une session : minuteur lancé, fin atteinte, bilan avec bonus, arrêt anticipé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = FocusPanel(vDatabaseFile)
    vPanel.refresh()
    vStart = datetime.now()

    assert "0 session(s)" in vPanel.status_label.text()

    vPanel.start()

    assert vPanel.timer.isActive() and vPanel.ring.text.startswith("2")
    assert vPanel.status_label.text() == "Objectif : Postuler"

    class Later(datetime):
        """Horloge avancée de 26 minutes, après la fin prévue."""

        @classmethod
        def now(cls, tz=None):
            return vStart + timedelta(minutes=26)

    monkeypatch.setattr(focus_panel, "datetime", Later)
    vPanel.tick()

    assert not vPanel.timer.isActive()
    assert "+0 XP de bonus" in vPanel.summary_label.text()
    assert load_focus(vDatabaseFile)["history"][-1]["completed"]

    vPanel.start()
    vPanel.stop()

    assert "pas de bonus" in vPanel.summary_label.text()
