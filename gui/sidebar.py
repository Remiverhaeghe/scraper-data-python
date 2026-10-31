"""Menu latéral : marque, progression, navigation, liens et état de la recherche"""

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import CONTACT_URL, LICENSE_NAME, REPOSITORY_URL, TAGLINE
from gui.branding import create_logo_icon
from gui.dialogs import show_legal_notice, show_license
from gui.icons import get_icon
from gui.progress_widgets import SidebarProgress, get_game_mode
from gui.theme import COLORS

# Liens internes du pied de menu, ouverts dans l'application
LEGAL_LINK = "#mentions-legales"
LICENSE_LINK = "#licence"


class Sidebar(QWidget):
    """Entoure la liste de navigation, que la fenêtre garde et pilote."""

    progress_requested = Signal()

    def __init__(self, pTitle, pNavigation):
        """Construit la marque, la progression, les liens et l'état."""
        super().__init__()

        self.setObjectName("sidebar")
        self.setFixedWidth(240)

        vLogo = QLabel()
        vLogo.setPixmap(create_logo_icon().pixmap(44, 44))
        vLogo.setFixedSize(44, 44)

        vName = QLabel(pTitle)
        vName.setObjectName("brandName")

        vTagline = QLabel(TAGLINE)
        vTagline.setObjectName("brandTagline")
        vTagline.setWordWrap(True)

        vBrandTexts = QVBoxLayout()
        vBrandTexts.setSpacing(2)
        vBrandTexts.addWidget(vName)
        vBrandTexts.addWidget(vTagline)

        vBrand = QHBoxLayout()
        vBrand.setSpacing(12)
        vBrand.addWidget(vLogo)
        vBrand.addLayout(vBrandTexts, 1)

        vSeparator = QFrame()
        vSeparator.setObjectName("separator")

        self.progress_box = SidebarProgress()
        self.progress_box.clicked.connect(self.progress_requested)
        self.progress_box.setVisible(get_game_mode() != "off")

        self.status_dot = QLabel("●")

        self.status_label = QLabel()
        self.status_label.setObjectName("sidebarStatus")

        # Visible seulement pendant une recherche, pour la suivre depuis une autre page
        self.status_bar = QWidget()
        self.status_bar.setVisible(False)

        vStatus = QHBoxLayout(self.status_bar)
        vStatus.setContentsMargins(0, 0, 0, 0)
        vStatus.addWidget(self.status_dot)
        vStatus.addWidget(self.status_label, 1)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(16, 22, 16, 18)
        vLayout.setSpacing(16)
        vLayout.addLayout(vBrand)
        vLayout.addWidget(vSeparator)
        vLayout.addWidget(self.progress_box)
        vLayout.addWidget(pNavigation, 1)
        vLayout.addWidget(self.create_footer_links())
        vLayout.addWidget(self.status_bar)

    def create_footer_links(self):
        """Construit les liens du pied de menu, identiques à ceux du web."""
        rLinks = QFrame()
        rLinks.setObjectName("sidebarLinks")

        vLayout = QVBoxLayout(rLinks)
        vLayout.setContentsMargins(0, 10, 0, 0)
        vLayout.setSpacing(2)

        for vTarget, vLabel, vIcon in (
            (LEGAL_LINK, "Mentions légales", "file-text"),
            (CONTACT_URL, "Me contacter", "linkedin"),
            (REPOSITORY_URL, "Code source", "github"),
            (LICENSE_LINK, f"Licence {LICENSE_NAME}", "scale"),
        ):
            vButton = QPushButton(get_icon(vIcon, COLORS["muted"], 16), vLabel)
            vButton.setObjectName("sidebarLink")
            vButton.setCursor(Qt.CursorShape.PointingHandCursor)
            vButton.clicked.connect(
                lambda _=False, pTarget=vTarget: self.open_footer_link(pTarget)
            )
            vLayout.addWidget(vButton)

        return rLinks

    def open_footer_link(self, pTarget):
        """Ouvre mentions et licence dans l'application, le contact au navigateur."""
        if pTarget == LEGAL_LINK:
            show_legal_notice(self.window())
        elif pTarget == LICENSE_LINK:
            show_license(self.window())
        else:
            QDesktopServices.openUrl(QUrl(pTarget))

    def show_search_running(self, pRunning):
        """Affiche ou masque l'état « Recherche en cours »."""
        if pRunning:
            self.status_dot.setStyleSheet(f"color: {COLORS['warning']};")
            self.status_label.setText("Recherche en cours")

        self.status_bar.setVisible(pRunning)
