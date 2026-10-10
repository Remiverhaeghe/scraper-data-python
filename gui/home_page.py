"""Page d'accueil : synthèse des offres, du suivi et des dernières exécutions"""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config import NEW_OFFER_DAYS
from gui.branding import REPOSITORY_URL
from gui.chart import BarChart
from gui.search_page import get_unavailability_reason
from gui.theme import COLORS, is_dark_theme
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.presentation import describe_search, describe_sources
from job.sources.registry import SOURCES
from storage.history_repository import get_history
from storage.job_offers import (
    FOLLOW_UP_STATUSES,
    count_new_offers_by_day,
    count_offers,
)
from utils.logger import get_logger

logger = get_logger(__name__)

RECENT_EXECUTIONS = 4

# Nombre de jours représentés par le graphique des nouvelles offres
CHART_DAYS = 14


def load_statistics(pDatabaseFile, pNow=None):
    """Calcule les indicateurs et la liste des dernières exécutions."""

    vNow = pNow if pNow is not None else datetime.now()

    rStatistics = {
        "offers": count_offers(pDatabaseFile, pHideIgnored=True),
        "new_offers": count_offers(
            pDatabaseFile,
            pSeenSince=vNow - timedelta(days=NEW_OFFER_DAYS),
            pHideIgnored=True,
        ),
        "applications": sum(
            count_offers(pDatabaseFile, pStatus=vStatus)
            for vStatus in FOLLOW_UP_STATUSES
        ),
        "follow_ups": count_offers(pDatabaseFile, pFollowUpBefore=vNow),
        "executions": get_history(pDatabaseFile, pLimit=RECENT_EXECUTIONS),
        "daily_new_offers": count_new_offers_by_day(pDatabaseFile, CHART_DAYS, vNow),
    }

    return rStatistics


def count_ready_sources():
    """Compte les sources sélectionnables, c'est-à-dire disponibles et configurées."""

    rCount = sum(
        1
        for vDefinition in SOURCES.values()
        if get_unavailability_reason(vDefinition) is None
    )

    return rCount


def describe_activity(pEntry):
    """Retourne l'icône, sa couleur, le titre, le détail et le bilan d'une exécution."""

    if pEntry.scraper_type == "job":
        vTitle = describe_search(pEntry.parameters) or "Recherche d'offres"
        vDetail = describe_sources(pEntry.parameters)
    else:
        vTitle = "Scraping de livres"
        vDetail = pEntry.url

    vIcon, vColor = {
        "success": ("circle-check", COLORS["success"]),
        "partial": ("circle-alert", COLORS["warning"]),
    }.get(pEntry.status, ("circle-alert", COLORS["danger"]))

    vDate = f"{pEntry.started_at:%d/%m/%Y à %H:%M}"

    rActivity = (
        vIcon,
        vColor,
        vTitle,
        f"{vDate} · {vDetail}" if vDetail else vDate,
        f"{pEntry.item_count} offre(s)",
    )

    return rActivity


class HomePage(QWidget):
    """Affiche la bannière, les indicateurs, l'activité et les actions rapides."""

    # Clé de la page ou du filtre à afficher, interprétée par la fenêtre principale
    navigation_requested = Signal(str)

    # Thème demandé par le bouton clair/sombre : light ou dark
    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        vGithubButton = create_button("GitHub", "github")
        vGithubButton.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL))
        )

        vIsDark = is_dark_theme()

        vThemeButton = create_button(
            "Mode clair" if vIsDark else "Mode sombre", "sun" if vIsDark else "moon"
        )
        vThemeButton.clicked.connect(
            lambda: self.theme_requested.emit("light" if vIsDark else "dark")
        )

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Tableau de bord",
            "Vue d'ensemble de vos offres et de vos candidatures",
            [vThemeButton, vGithubButton],
        )

        vLayout.addWidget(self.create_banner())
        vLayout.addLayout(self.create_statistics())

        vBottom = QHBoxLayout()
        vBottom.setSpacing(18)
        vBottom.addWidget(self.create_chart_card(), 3)
        vBottom.addWidget(self.create_activity_card(), 3)
        vBottom.addWidget(self.create_actions_card(), 2)

        vLayout.addLayout(vBottom)
        vLayout.addStretch()

    def create_banner(self):
        """Construit la bannière de bienvenue."""
        rBanner = QFrame()
        rBanner.setObjectName("banner")

        vTitle = QLabel("Votre recherche d'emploi, pilotée au même endroit")
        vTitle.setObjectName("bannerTitle")

        self.banner_text = QLabel()
        self.banner_text.setObjectName("bannerText")
        self.banner_text.setWordWrap(True)

        vButton = create_button(
            "Lancer une recherche", "arrow-right", "bannerButton", COLORS["primary"]
        )
        vButton.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        vButton.clicked.connect(lambda: self.navigation_requested.emit("search"))

        vButtonRow = QHBoxLayout()
        vButtonRow.addWidget(vButton)
        vButtonRow.addStretch()

        vTexts = QVBoxLayout()
        vTexts.setSpacing(8)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(self.banner_text)
        vTexts.addSpacing(8)
        vTexts.addLayout(vButtonRow)

        vIcons = QHBoxLayout()
        vIcons.setSpacing(22)

        for vIcon in ("search", "briefcase", "bell-ring"):
            vIcons.addWidget(create_icon_label(vIcon, COLORS["banner_text"], 46))

        vLayout = QHBoxLayout(rBanner)
        vLayout.setContentsMargins(32, 26, 40, 26)
        vLayout.addLayout(vTexts, 1)
        vLayout.addLayout(vIcons)

        return rBanner

    def create_statistics(self):
        """Construit les cartes statistiques colorées."""
        self.cards = {
            "offers": StatisticCard(
                "Offres actives en base", "briefcase", "blue", True
            ),
            "new_offers": StatisticCard(
                f"Nouvelles sur {NEW_OFFER_DAYS} jours", "sparkles", "green", True
            ),
            "applications": StatisticCard(
                "Candidatures en cours", "send", "amber", True
            ),
            "follow_ups": StatisticCard(
                "Relances à faire", "bell-ring", "purple", True
            ),
        }

        rGrid = QGridLayout()
        rGrid.setSpacing(18)

        # Chaque carte ouvre les offres correspondantes.
        for vIndex, (vName, vCard) in enumerate(self.cards.items()):
            vCard.clicked.connect(
                lambda pName=vName: self.navigation_requested.emit(pName)
            )
            rGrid.addWidget(vCard, 0, vIndex)

        return rGrid

    def create_chart_card(self):
        """Construit le graphique des nouvelles offres par jour."""
        vCard, vLayout = create_card(
            "Nouvelles offres", f"Offres découvertes sur {CHART_DAYS} jours"
        )

        self.chart = BarChart()

        vLayout.addWidget(self.chart, 1)

        return vCard

    def create_activity_card(self):
        """Construit la carte des dernières exécutions."""
        vCard, vLayout = create_card(
            "Activité récente", "Vos dernières recherches et leur résultat"
        )

        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(2)

        vLayout.addLayout(self.activity_layout)
        vLayout.addStretch()

        return vCard

    def create_actions_card(self):
        """Construit la carte des actions rapides."""
        vCard, vLayout = create_card(
            "Actions rapides", "Accédez directement aux fonctions principales"
        )

        for vText, vIcon, vTarget in (
            ("Nouvelle recherche", "search", "search"),
            ("Consulter les offres", "list-checks", "offers"),
            ("Candidatures à relancer", "bell-ring", "follow_ups"),
            ("Historique des exécutions", "history", "history"),
        ):
            vButton = create_button(vText, vIcon, "quickAction", COLORS["primary"])
            vButton.clicked.connect(
                lambda _=False, pTarget=vTarget: self.navigation_requested.emit(pTarget)
            )
            vLayout.addWidget(vButton)

        vLayout.addStretch()

        return vCard

    def create_activity_row(self, pEntry):
        """Construit la ligne d'une exécution dans l'activité récente."""
        vIcon, vColor, vTitle, vDetail, vResult = describe_activity(pEntry)

        vTitleLabel = QLabel(vTitle)
        vTitleLabel.setObjectName("activityTitle")

        vDetailLabel = QLabel(vDetail)
        vDetailLabel.setObjectName("cardSubtitle")

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitleLabel)
        vTexts.addWidget(vDetailLabel)

        vResultLabel = QLabel(vResult)
        vResultLabel.setObjectName("activityResult")

        rRow = QWidget()

        vLayout = QHBoxLayout(rRow)
        vLayout.setContentsMargins(0, 6, 0, 6)
        vLayout.setSpacing(12)
        vLayout.addWidget(create_icon_label(vIcon, vColor, 22))
        vLayout.addLayout(vTexts, 1)
        vLayout.addWidget(vResultLabel)

        return rRow

    def show_activity(self, pEntries):
        """Remplace la liste des dernières exécutions."""
        while self.activity_layout.count():
            self.activity_layout.takeAt(0).widget().deleteLater()

        if not pEntries:
            vEmpty = QLabel("Aucune recherche lancée pour le moment.")
            vEmpty.setObjectName("cardSubtitle")
            self.activity_layout.addWidget(vEmpty)

        for vEntry in pEntries:
            self.activity_layout.addWidget(self.create_activity_row(vEntry))

    def refresh(self):
        """Relit les indicateurs et l'activité en base."""
        self.banner_text.setText(
            f"Centralisez les offres de {count_ready_sources()} sources configurées, "
            "suivez vos candidatures et n'oubliez plus aucune relance."
        )

        try:
            vStatistics = load_statistics(self.database_file)

        except Exception:
            logger.exception("Impossible de charger les statistiques de l'accueil")

            self.show_activity([])

        else:
            for vName, vCard in self.cards.items():
                vCard.set_value(vStatistics[vName])

            self.show_activity(vStatistics["executions"])
            self.chart.set_values(
                [
                    (f"{vDay:%d/%m}", vCount)
                    for vDay, vCount in vStatistics["daily_new_offers"]
                ]
            )
