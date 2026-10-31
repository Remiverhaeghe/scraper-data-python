"""Tests des notifications natives du bureau"""

from PySide6.QtWidgets import QSystemTrayIcon, QWidget

import gui.desktop_notifier as desktop_notifier
from gui.desktop_notifier import DesktopNotifier


class FakeTray:
    """Icône de notification simulée : garde les messages montrés."""

    def __init__(self):
        self.messages = []

    def showMessage(self, *pArgs):  # pylint: disable=invalid-name
        self.messages.append(pArgs)


def test_notification_is_shown_then_opens_its_page(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la notification montrée, puis la page ouverte d'un clic."""

    vOpened = []
    vNotifier = DesktopNotifier(QWidget(), tmp_path / "scraper.db", vOpened.append)
    vNotifier.tray = FakeTray()
    monkeypatch.setattr(
        desktop_notifier,
        "pick_notification",
        lambda *pArgs: {
            "title": "2 relance(s) à faire",
            "text": "Technicien",
            "page": "applications",
        },
    )

    vNotifier.check()
    vNotifier.open_page()

    assert vNotifier.tray.messages[0][:3] == (
        "2 relance(s) à faire",
        "Technicien",
        QSystemTrayIcon.MessageIcon.Information,
    )
    assert vOpened == ["applications"]


def test_nothing_happens_without_tray_or_on_error(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie l'absence d'icône sans zone de notification, et une erreur journalisée."""

    vNotifier = DesktopNotifier(QWidget(), tmp_path / "scraper.db", lambda pPage: None)
    vNotifier.tray = None
    vNotifier.check()

    def fail(*_pArgs):
        raise RuntimeError("base indisponible")

    vNotifier.tray = FakeTray()
    monkeypatch.setattr(desktop_notifier, "pick_notification", fail)
    vNotifier.check()

    assert vNotifier.tray.messages == [] and vNotifier.page is None
