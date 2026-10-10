"""Page d'accueil : synthèse des offres, du suivi et des dernières exécutions"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.presentation import CHART_PALETTE, describe_execution
from job.statistics import (
    ACTIVITY_SERIES,
    CHART_DAYS,
    count_ready_sources,
    load_statistics,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# Icône de chaque tonalité d'exécution
TONE_ICONS = {
    "success": "circle-check",
    "warning": "circle-alert",
    "danger": "circle-alert",
}


def describe_activity(pEntry):
    """Retourne l'icône, sa couleur, le titre, le détail et le bilan d'une exécution."""

    vDescription = describe_execution(pEntry)

    rActivity = (
        TONE_ICONS[vDescription["tone"]],
        COLORS[vDescription["tone"]],
        vDescription["title"],
        vDescription["detail"],
        vDescription["result"],
    )

    return rActivity


class HomePage(QWidget):
    """Affiche la bannière, les indicateurs, l'activité et les actions rapides."""

    # Clé de la page ou du filtre à afficher, interprétée par la fenêtre principale
    navigation_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Tableau de bord",
            "Vue d'ensemble de vos offres et de vos candidatures",
            pIcon="house",
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
            "new_offers": StatisticCard("Nouvelles offres", "sparkles", "green", True),
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
            "Activité",
            f"Sur {CHART_DAYS} jours, chaque série à sa propre échelle",
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

            self.cards["new_offers"].set_label(
                f"Nouvelles sur {vStatistics['new_offer_days']} jours"
            )

            self.show_activity(vStatistics["executions"])
            self.show_chart(vStatistics["daily_activity"])

    def show_chart(self, pDailyActivity):
        """Affiche une série de barres par type d'activité, jour par jour."""
        vFirstSeries = next(iter(pDailyActivity.values()))

        self.chart.set_series(
            [f"{vDay:%d/%m}" for vDay, _ in vFirstSeries],
            [
                (
                    ACTIVITY_SERIES[vName][0],
                    CHART_PALETTE[vIndex],
                    [vCount for _, vCount in vCounts],
                )
                for vIndex, (vName, vCounts) in enumerate(pDailyActivity.items())
            ],
            pIndependentScales=True,
        )
