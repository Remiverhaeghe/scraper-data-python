"""Notifications natives de Windows, par l'icône de la zone de notification

Toutes les cinq minutes, la prochaine notification utile est montrée ; un clic
dessus ramène la fenêtre au premier plan sur la page concernée.
"""

from datetime import datetime

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QSystemTrayIcon

from job.desktop_notifications import pick_notification
from utils.logger import get_logger

logger = get_logger(__name__)

CHECK_MS = 5 * 60 * 1000
# Premier contrôle une minute après l'ouverture : le démarrage reste rapide
FIRST_CHECK_MS = 60 * 1000
SHOWN_MS = 10_000


class DesktopNotifier(QObject):
    """Montre les notifications et ouvre la page voulue d'un clic."""

    def __init__(self, pWindow, pDatabaseFile, pNavigate):
        """Crée l'icône si le système en a une, puis lance les contrôles réguliers."""
        super().__init__(pWindow)

        self.window = pWindow
        self.database_file = pDatabaseFile
        self.navigate = pNavigate
        self.page = None
        self.tray = None

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(pWindow.windowIcon(), self)
            self.tray.setToolTip("JobBoard Perso")
            self.tray.messageClicked.connect(self.open_page)
            self.tray.activated.connect(lambda _pReason: self.bring_to_front())
            self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(CHECK_MS)
        QTimer.singleShot(FIRST_CHECK_MS, self.check)

    def check(self):
        """Montre la prochaine notification utile, s'il y en a une."""
        if self.tray is None:
            return

        try:
            vNotification = pick_notification(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de préparer les notifications du bureau")
            return

        if vNotification is not None:
            self.page = vNotification["page"]
            self.tray.showMessage(
                vNotification["title"],
                vNotification["text"],
                QSystemTrayIcon.MessageIcon.Information,
                SHOWN_MS,
            )

    def bring_to_front(self):
        """Ramène la fenêtre au premier plan, même réduite."""
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def open_page(self):
        """Ouvre la page de la dernière notification."""
        self.bring_to_front()

        if self.page:
            self.navigate(self.page)
