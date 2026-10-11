"""Fenêtre principale : menu latéral et pages de l'application"""

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import CONTACT_URL, LICENSE_NAME, REPOSITORY_URL, TAGLINE
from gui.branding import create_logo_icon
from gui.dialogs import show_legal_notice, show_license
from gui.history_page import HistoryPage
from gui.home_page import HomePage
from gui.logs_page import LogsPage
from gui.icons import get_icon
from gui.offers_page import OffersPage
from gui.quality_page import QualityPage
from gui.search_page import SearchPage
from gui.settings_page import SettingsPage
from gui.theme import COLORS
from job.schedule import save_scheduled_search
from utils.logger import get_logger

logger = get_logger(__name__)

# Liens internes du pied de menu, ouverts dans l'application
LEGAL_LINK = "#mentions-legales"
LICENSE_LINK = "#licence"

# Clés de navigation qui ouvrent la page des offres avec des filtres prédéfinis
OFFER_PRESETS = ("offers", "new_offers", "applications", "follow_ups")


class MainWindow(QMainWindow):
    """Affiche le menu latéral et la page sélectionnée."""

    # Thème choisi dans les paramètres : light ou dark
    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile, pTitle):
        """Construit la fenêtre et son contenu."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.title = pTitle

        self.setWindowTitle(pTitle)
        # En dessous, les cartes se chevauchent. Sur un petit écran ou un téléphone,
        # le tableau de bord web s'adapte à la largeur disponible.
        self.setMinimumSize(1180, 760)

        self.build_content()

    def build_content(self):
        """Construit le menu latéral et les pages.

        Appelée de nouveau après un changement de thème : les icônes et les
        cartes colorées sont dessinées à la construction.
        """
        pDatabaseFile = self.database_file
        self.page_labels = {}

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setIconSize(QSize(20, 20))

        self.pages = QStackedWidget()
        self.page_rows = {}

        self.home_page = HomePage(pDatabaseFile)
        self.search_page = SearchPage(pDatabaseFile=pDatabaseFile)
        self.offers_page = OffersPage(pDatabaseFile)

        # L'ordre d'ajout fixe l'ordre du menu ; la clé sert à navigate().
        self.add_page("home", "Accueil", "house", self.home_page)
        self.add_page("search", "Recherche", "search", self.search_page)
        self.add_page("offers", "Offres", "briefcase", self.offers_page)
        self.add_page("history", "Historique", "history", HistoryPage(pDatabaseFile))
        self.add_page("quality", "Qualité", "list-checks", QualityPage(pDatabaseFile))
        self.add_page("logs", "Journaux", "terminal", LogsPage())

        self.settings_page = SettingsPage(pDatabaseFile)
        self.add_page("settings", "Paramètres", "settings", self.settings_page)

        # Les pages ne se connaissent pas : elles émettent des signaux et la fenêtre
        # décide de la suite. Pour suivre l'effet d'un clic, partir de ces connexions.
        self.settings_page.theme_requested.connect(self.theme_requested)
        self.settings_page.data_reset.connect(self.show_reset_result)

        self.home_page.navigation_requested.connect(self.navigate)
        self.home_page.offer_requested.connect(self.show_search_results)
        self.search_page.show_offers_requested.connect(self.show_search_results)
        self.search_page.search_started.connect(self.on_search_started)
        self.search_page.search_ended.connect(self.on_search_ended)
        self.search_page.schedule_requested.connect(self.save_scheduled_search)

        vCentral = QWidget()

        vLayout = QHBoxLayout(vCentral)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(self.create_sidebar(self.title))
        vLayout.addWidget(self.pages, 1)

        self.setCentralWidget(vCentral)

        self.navigation.currentRowChanged.connect(self.show_page)
        self.navigation.setCurrentRow(0)
        self.set_status("Prêt", COLORS["success"])

    def create_sidebar(self, pTitle):
        """Construit le menu latéral : marque, navigation et état."""
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
        vLayout.addWidget(self.create_footer_links())
        vLayout.addLayout(vStatus)

        return rSidebar

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
            show_legal_notice(self)
        elif pTarget == LICENSE_LINK:
            show_license(self)
        else:
            QDesktopServices.openUrl(QUrl(pTarget))

    def add_page(self, pKey, pLabel, pIcon, pPage):
        """Ajoute une page et son entrée dans le menu latéral."""
        vItem = QListWidgetItem(
            get_icon(pIcon, COLORS["muted"], 20, pSelectedColor=COLORS["on_primary"]),
            pLabel,
        )

        self.page_rows[pKey] = self.pages.count()
        self.page_labels[self.pages.count()] = pLabel
        self.navigation.addItem(vItem)
        self.pages.addWidget(pPage)

    def navigate(self, pKey):
        """Affiche une page, ou la page des offres avec un préréglage de filtres."""
        vKey = pKey

        if pKey in OFFER_PRESETS:
            self.offers_page.apply_preset(pKey)
            vKey = "offers"

        self.navigation.setCurrentRow(self.page_rows[vKey])

    def rebuild(self, pPage):
        """Reconstruit le contenu dans la même fenêtre, sans la fermer.

        L'affichage est suspendu pendant la reconstruction pour éviter tout
        scintillement ; setCentralWidget détruit l'ancien contenu.
        """
        self.setUpdatesEnabled(False)

        try:
            self.build_content()
            self.navigate(pPage)

        finally:
            self.setUpdatesEnabled(True)

    def show_reset_result(self, pMessage):
        """Recharge toutes les pages après une réinitialisation des données."""
        self.rebuild("settings")
        self.settings_page.reset_message.setText(pMessage)

    def save_scheduled_search(self, pSources, pCriteria):
        """Enregistre la recherche du planificateur et l'indique sur la page."""
        try:
            save_scheduled_search(self.database_file, pSources, pCriteria)

        except Exception:
            logger.exception("Échec de l'enregistrement de la recherche planifiée")

            self.search_page.set_status(
                "error", "La recherche planifiée n'a pas pu être enregistrée."
            )

        else:
            self.search_page.set_status(
                "success",
                "Recherche planifiée enregistrée",
                "Activez-la et choisissez sa fréquence dans les Paramètres.",
            )
            self.settings_page.refresh_schedule()

    def show_search_results(self, pKeys, pDescription):
        """Ouvre la page des offres restreinte aux résultats d'une recherche."""
        self.offers_page.apply_preset("offers", pKeys, pDescription)
        self.navigation.setCurrentRow(self.page_rows["offers"])

    def show_page(self, pIndex):
        """Affiche la page choisie et rafraîchit ses données si elle le permet."""
        self.pages.setCurrentIndex(pIndex)
        self.setWindowTitle(f"{self.page_labels[pIndex]} · {self.title}")

        vPage = self.pages.currentWidget()

        if hasattr(vPage, "refresh"):
            vPage.refresh()

    def on_search_started(self):
        """Signale la recherche en cours et bloque le changement de thème."""
        self.set_status("Recherche en cours", COLORS["warning"])
        self.settings_page.set_actions_enabled(False)

    def on_search_ended(self):
        """Signale le retour au repos et réautorise le changement de thème."""
        self.set_status("Prêt", COLORS["success"])
        self.settings_page.set_actions_enabled(True)

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
