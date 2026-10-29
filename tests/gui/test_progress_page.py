"""Tests de la progression dans l'application de bureau"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel

import gui.main_window as main_window
from gui.main_window import MainWindow
from gui.progress_widgets import GAME_MODE_SETTING, CelebrationOverlay
from storage.database import connect_database, initialize_database


def answer(pDatabaseFile, pCount):
    """Enregistre des réponses justes aujourd'hui."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "INSERT INTO quiz_answer (question_id, theme, correct, answered_at)"
            " VALUES (?, 'sql', 1, datetime('now', 'localtime'))",
            [(f"q{vIndex}",) for vIndex in range(pCount)],
        )
        vConnection.commit()

    finally:
        vConnection.close()


def create_window(pTmpPath):
    """Ouvre la fenêtre sur une base vide, progression de départ relue."""

    vDatabaseFile = pTmpPath / "scraper.db"
    initialize_database(vDatabaseFile)

    rWindow = MainWindow(vDatabaseFile, "Test")
    rWindow.check_progress()

    return rWindow, vDatabaseFile


def test_points_gained_are_shown_then_level_is_celebrated(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie le « +XP », la quête réussie, puis la fête du passage de niveau."""

    # Le réglage d'accessibilité du PC de test ne doit pas rendre le jeu discret.
    monkeypatch.setattr(main_window, "get_game_mode", lambda: "full")
    vWindow, vDatabaseFile = create_window(tmp_path)
    vShown = []
    vCelebrated = []
    monkeypatch.setattr(
        main_window,
        "show_xp_gain",
        lambda pWindow, pAnchor, pText, pDelayMs=0: vShown.append(pText),
    )
    monkeypatch.setattr(
        main_window,
        "CelebrationOverlay",
        lambda pWindow, pTitle, pSubtitle, pDetail: vCelebrated.append(pTitle),
    )

    assert vWindow.progress_box.title_label.text() == "Apprenti"

    answer(vDatabaseFile, 2)
    vWindow.check_progress()

    assert vShown == ["+10 XP"]
    assert not vCelebrated

    answer(vDatabaseFile, 18)
    vWindow.check_progress()

    assert "Quête réussie : Réviser 10 questions" in vShown
    assert vCelebrated == ["Niveau 2"]
    assert vWindow.progress_box.title_label.text() == "Apprenti confirmé"


def test_progress_page_lists_quests_and_rules(qt_application, tmp_path):
    """Vérifie la page : niveau, quêtes du jour et de la semaine, règles."""

    vWindow, _ = create_window(tmp_path)
    vWindow.navigate("progress")

    vTexts = [vLabel.text() for vLabel in vWindow.progress_page.findChildren(QLabel)]

    assert vWindow.progress_page.title_label.text() == "Niveau 1 · Apprenti"
    assert "Réviser 10 questions" in vTexts
    assert any(vText.startswith("Semaine · ") for vText in vTexts)
    assert "Candidature envoyée" in vTexts


def test_game_can_be_turned_off(qt_application, tmp_path):
    """Vérifie le mode Désactivé : encart masqué, plus aucune relecture."""

    vWindow, vDatabaseFile = create_window(tmp_path)
    vWindow.show()
    vWindow.navigate("settings")

    next(
        vButton
        for vButton in vWindow.settings_page.game_mode_buttons.buttons()
        if vButton.text() == "Désactivé"
    ).click()
    answer(vDatabaseFile, 5)
    vWindow.check_progress()

    assert QSettings().value(GAME_MODE_SETTING) == "off"
    assert vWindow.progress_box.isHidden()
    assert vWindow.last_progress["xp"] == 0


def test_celebration_closes_on_click(qt_application, tmp_path):
    """Vérifie que la célébration couvre la fenêtre et se ferme d'un clic."""

    vWindow, _ = create_window(tmp_path)
    vWindow.resize(800, 600)
    vOverlay = CelebrationOverlay(vWindow, "Niveau 2", "Apprenti confirmé")

    assert vOverlay.geometry() == vWindow.rect()

    vOverlay.close_celebration()

    assert vOverlay.isHidden()
