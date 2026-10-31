"""Tests du dessin des widgets peints à la main : machine d'automate et célébration"""

import pytest
from PySide6.QtWidgets import QWidget

from gui.ladder_machine import MachineView
from gui.progress_widgets import CelebrationOverlay, SidebarProgress, show_xp_gain
from job.ladder_game import load_levels


@pytest.mark.parametrize(
    "pLevel", list(load_levels().values()), ids=lambda pLevel: pLevel["id"]
)
def test_machine_is_drawn_at_rest_and_running(qt_application, pLevel):
    """Vérifie que chaque machine se dessine, sorties éteintes puis toutes allumées."""

    vView = MachineView()
    vView.resize(520, 260)
    vNames = [vVariable["name"] for vVariable in pLevel["variables"]]

    vView.set_state(pLevel, dict.fromkeys(vNames, 0), {"position": 0, "run": 0})

    assert not vView.grab().isNull()

    for vPosition in (0.5, 1):
        vView.set_state(
            pLevel, dict.fromkeys(vNames, 1), {"position": vPosition, "run": 3}
        )

        assert not vView.grab().isNull()


def test_empty_machine_draws_nothing(qt_application):
    """Vérifie qu'une vue sans niveau se peint sans erreur."""

    assert not MachineView().grab().isNull()


def test_celebration_and_progress_are_drawn(qt_application):
    """Vérifie le dessin de la célébration, de la progression et du gain d'XP."""

    vWindow = QWidget()
    vWindow.resize(800, 600)
    vOverlay = CelebrationOverlay(vWindow, "Niveau 3", "Technicien", "Série de 5 jours")

    assert not vOverlay.grab().isNull()

    vOverlay.tick()
    vOverlay.close_celebration()

    vSidebar = SidebarProgress()
    vSidebar.resize(240, 120)

    assert not vSidebar.grab().isNull()

    show_xp_gain(vWindow, vSidebar, "+15 XP")
    vWindow.close()
