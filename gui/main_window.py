"""Fenêtre principale : menu latéral et pages de l'application"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.history_page import HistoryPage
from gui.home_page import HomePage
from gui.icons import get_icon
from gui.offers_page import OffersPage
from gui.search_page import SearchPage
from gui.theme import COLORS

TAGLINE = "Vos offres d'emploi, centralisées"


class MainWindow(QMainWindow):
    """Affiche le menu latéral et la page sélectionnée."""

    def __init__(self, pDatabaseFile, pTitle):
        """Construit la fenêtre et ses pages."""
        super().__init__()

        self.setWindowTitle(pTitle)
        self.setMinimumSize(1180, 760)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setIconSize(QSize(20, 20))

        self.pages = QStackedWidget()
        self.page_rows = {}

        self.home_page = HomePage(pDatabaseFile)
        self.search_page = SearchPage()
        self.offers_page = OffersPage(pDatabaseFile)

        self.add_page("home", "Accueil", "house", self.home_page)
        self.add_page("search", "Recherche", "search", self.search_page)
        self.add_page("offers", "Offres", "briefcase", self.offers_page)
        self.add_page("history", "Historique", "history", HistoryPage(pDatabaseFile))

        self.home_page.navigation_requested.connect(self.navigate)
        self.search_page.show_offers_requested.connect(lambda: self.navigate("offers"))
        self.search_page.search_started.connect(
            lambda: self.set_status("Recherche en cours", COLORS["warning"])
        )
        self.search_page.search_ended.connect(
            lambda: self.set_status("Prêt", COLORS["success"])
        )

        vCentral = QWidget()

        vLayout = QHBoxLayout(vCentral)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(self.create_sidebar(pTitle))
        vLayout.addWidget(self.pages, 1)

        self.setCentralWidget(vCentral)

        self.navigation.currentRowChanged.connect(self.show_page)
        self.navigation.setCurrentRow(0)
        self.set_status("Prêt", COLORS["success"])

    def create_sidebar(self, pTitle):
        """Construit le menu latéral : marque, navigation et état."""
        vLogo = QLabel("RV")
        vLogo.setObjectName("logo")
        vLogo.setFixedSize(44, 44)
        vLogo.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self.status_dot = QLabel("●")

        self.status_label = QLabel()
        self.status_label.setObjectName("sidebarStatus")

        vStatus = QHBoxLayout()
        vStatus.addWidget(self.status_dot)
        vStatus.addWidget(self.status_label, 1)

        rSidebar = QWidget()
        rSidebar.setObjectName("sidebar")
        rSidebar.setFixedWidth(240)

        vLayout = QVBoxLayout(rSidebar)
        vLayout.setContentsMargins(16, 22, 16, 18)
        vLayout.setSpacing(16)
        vLayout.addLayout(vBrand)
        vLayout.addWidget(vSeparator)
        vLayout.addWidget(self.navigation, 1)
        vLayout.addLayout(vStatus)

        return rSidebar

    def add_page(self, pKey, pLabel, pIcon, pPage):
        """Ajoute une page et son entrée dans le menu latéral."""
        vItem = QListWidgetItem(
            get_icon(pIcon, COLORS["muted"], 20, pSelectedColor=COLORS["surface"]),
            pLabel,
        )

        self.page_rows[pKey] = self.pages.count()
        self.navigation.addItem(vItem)
        self.pages.addWidget(pPage)

    def navigate(self, pKey):
        """Affiche une page à partir de sa clé ; follow_ups filtre les relances."""
        vKey = pKey

        if pKey == "follow_ups":
            self.offers_page.show_follow_ups()
            vKey = "offers"

        self.navigation.setCurrentRow(self.page_rows[vKey])

    def show_page(self, pIndex):
        """Affiche la page choisie et rafraîchit ses données si elle le permet."""
        self.pages.setCurrentIndex(pIndex)

        vPage = self.pages.currentWidget()

        if hasattr(vPage, "refresh"):
            vPage.refresh()

    def set_status(self, pText, pColor):
        """Affiche l'état de l'application en bas du menu latéral."""
        self.status_dot.setStyleSheet(f"color: {pColor};")
        self.status_label.setText(pText)

    def closeEvent(self, pEvent):
        """Diffère la fermeture tant qu'une recherche est en cours.

        Détruire un QThread actif fait planter l'application : la recherche est
        arrêtée et la fenêtre se ferme d'elle-même à la fin de la source en cours.
        """
        if self.search_page.is_running():
            self.search_page.search_ended.connect(self.close)
            self.search_page.stop_search()

            pEvent.ignore()
        else:
            pEvent.accept()
