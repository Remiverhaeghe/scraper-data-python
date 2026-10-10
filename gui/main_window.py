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

from gui.home_page import HomePage


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

        self.add_page("Accueil", HomePage(pDatabaseFile))

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
