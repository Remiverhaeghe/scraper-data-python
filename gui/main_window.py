"""Fenêtre principale : menu latéral et pages de l'application"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.history_page import HistoryPage
from gui.home_page import HomePage
from gui.offers_page import OffersPage
from gui.search_page import SearchPage


class MainWindow(QMainWindow):
    """Affiche le menu latéral et la page sélectionnée."""

    def __init__(self, pDatabaseFile, pTitle):
        """Construit la fenêtre et ses pages."""
        super().__init__()

        self.setWindowTitle(pTitle)
        self.setMinimumSize(1100, 720)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")

        self.pages = QStackedWidget()

        self.search_page = SearchPage()

        self.add_page("Accueil", HomePage(pDatabaseFile))
        self.add_page("Recherche", self.search_page)
        self.add_page("Offres", OffersPage(pDatabaseFile))
        self.add_page("Historique", HistoryPage(pDatabaseFile))

        self.search_page.show_offers_requested.connect(
            lambda: self.navigation.setCurrentRow(2)
        )

        vSidebar = QWidget()
        vSidebar.setObjectName("sidebar")
        vSidebar.setFixedWidth(220)

        vSidebarLayout = QVBoxLayout(vSidebar)
        vSidebarLayout.setContentsMargins(12, 20, 12, 20)

        vBrand = QLabel(pTitle)
        vBrand.setObjectName("brand")

        vSidebarLayout.addWidget(vBrand)
        vSidebarLayout.addWidget(self.navigation)

        vCentral = QWidget()

        vLayout = QHBoxLayout(vCentral)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(vSidebar)
        vLayout.addWidget(self.pages, 1)

        self.setCentralWidget(vCentral)

        self.navigation.currentRowChanged.connect(self.show_page)
        self.navigation.setCurrentRow(0)

    def add_page(self, pLabel, pPage):
        """Ajoute une page au menu latéral."""
        self.navigation.addItem(pLabel)
        self.pages.addWidget(pPage)

    def show_page(self, pIndex):
        """Affiche la page choisie et rafraîchit ses données si elle le permet."""
        self.pages.setCurrentIndex(pIndex)

        vPage = self.pages.currentWidget()

        if hasattr(vPage, "refresh"):
            vPage.refresh()

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
