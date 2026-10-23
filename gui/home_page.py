"""Page d'accueil : synthèse des offres, du suivi et des dernières exécutions"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_fold_button,
    create_icon_label,
    create_page_header,
    create_scroll_content,
)
from job.presentation import (
    CHART_PALETTE,
    describe_execution,
    format_date,
    format_net_salary,
)
from job.setup_checklist import build_setup_checklist
from job.statistics import (
    ACTIVITY_AXES,
    ACTIVITY_SERIES,
    EMPTY_CHART_TEXT,
    count_ready_sources,
    load_statistics,
)
from utils.logger import get_logger

logger = get_logger(__name__)

HOME_CHART_MIN_HEIGHT = 170


# Icône de chaque tonalité d'exécution
TONE_ICONS = {
    "success": "circle-check",
    "warning": "circle-alert",
    "danger": "circle-alert",
}

# Raccourcis de la bannière, après le bouton de recherche
# Préréglage de la page Offres ouvert par une carte, quand il porte un autre nom
CARD_PRESETS = {"applications": "applied_offers"}

BANNER_ACTIONS = (
    ("Consulter les offres", "list-checks", "offers"),
    ("Relances à faire", "bell-ring", "follow_ups"),
    ("Historique", "history", "history"),
)


def describe_activity(pEntry):
    """Retourne l'icône, sa couleur, le titre, le détail, les sources et le bilan."""

    vDescription = describe_execution(pEntry)

    rActivity = (
        TONE_ICONS[vDescription["tone"]],
        COLORS[vDescription["tone"]],
        vDescription["title"],
        vDescription["detail"],
        vDescription["sources"],
        vDescription["result"],
    )

    return rActivity


def describe_last_search(pExecutions):
    """Résume la dernière recherche pour l'en-tête du tableau de bord."""

    rDescription = "Aucune recherche pour le moment"

    if pExecutions:
        vEntry = pExecutions[0]
        rDescription = (
            f"Dernière recherche le {vEntry.started_at:%d/%m à %H:%M} · "
            f"{vEntry.item_count} offre(s)"
        )

    return rDescription


class HomePage(QWidget):
    """Affiche la bannière, les indicateurs, l'activité et les actions rapides."""

    # Clé de la page ou du filtre à afficher, interprétée par la fenêtre principale
    navigation_requested = Signal(str)

    # Offre à afficher, en couple (source, identifiant), et sa description
    offer_requested = Signal(object, str)

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.last_search_label = QLabel()
        self.last_search_label.setObjectName("pageSubtitle")

        vContent = create_scroll_content(self)

        # Les cartes du bas partagent la hauteur restante : l'accueil peut se
        # réduire jusqu'à sa taille minimale avant de défiler.
        vContent.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        vLayout = QVBoxLayout(vContent)
        vLayout.setContentsMargins(32, 18, 32, 18)
        vLayout.setSpacing(12)

        create_page_header(
            vLayout,
            "Tableau de bord",
            "Vue d'ensemble de vos offres et de vos candidatures",
            [self.last_search_label, create_fold_button(self)],
            pIcon="house",
        )

        vLayout.addWidget(self.create_banner())
        vLayout.addLayout(self.create_statistics())
        vLayout.addWidget(self.create_goal_bar())
        vLayout.addWidget(self.create_checklist_card())

        # Une grille aligne les colonnes des deux rangées, qui se partagent la
        # hauteur de la fenêtre : la page ne défile que sur un petit écran.
        vGrid = QGridLayout()
        vGrid.setSpacing(16)
        vGrid.addWidget(self.create_chart_card(), 0, 0)
        vGrid.addWidget(self.create_activity_card(), 0, 1)
        vGrid.addWidget(self.create_follow_ups_card(), 1, 0)
        vGrid.addWidget(self.create_latest_offers_card(), 1, 1)
        vGrid.addWidget(self.create_similar_offers_card(), 2, 0, 1, 2)

        for vIndex in range(2):
            vGrid.setColumnStretch(vIndex, 1)
            vGrid.setRowStretch(vIndex, 1)

        vLayout.addLayout(vGrid, 1)

    def create_banner(self):
        """Construit la bannière de bienvenue."""
        rBanner = QFrame()
        rBanner.setObjectName("banner")

        vTitle = QLabel("Votre recherche d'emploi, pilotée au même endroit")
        vTitle.setObjectName("bannerTitle")

        self.banner_text = QLabel()
        self.banner_text.setObjectName("bannerText")
        self.banner_text.setWordWrap(True)

        vSearchButton = create_button(
            "Nouvelle recherche", "arrow-right", "bannerButton", COLORS["primary"]
        )
        vSearchButton.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        vSearchButton.clicked.connect(lambda: self.navigation_requested.emit("search"))

        vButtonRow = QHBoxLayout()
        vButtonRow.setSpacing(10)
        vButtonRow.addWidget(vSearchButton)

        for vText, vIcon, vTarget in BANNER_ACTIONS:
            vButton = create_button(
                vText, vIcon, "bannerSecondaryButton", COLORS["on_primary"]
            )
            vButton.clicked.connect(
                lambda _=False, pTarget=vTarget: self.navigation_requested.emit(pTarget)
            )
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
        vLayout.setContentsMargins(32, 22, 40, 22)
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
        rGrid.setSpacing(16)

        # Chaque carte ouvre les offres correspondantes.
        for vIndex, (vName, vCard) in enumerate(self.cards.items()):
            vCard.clicked.connect(
                lambda pName=vName: self.navigation_requested.emit(
                    CARD_PRESETS.get(pName, pName)
                )
            )
            rGrid.addWidget(vCard, 0, vIndex)

        return rGrid

    def create_goal_bar(self):
        """Construit la progression de l'objectif de candidatures de la semaine."""
        self.goal_bar = QProgressBar()
        self.goal_bar.setToolTip(
            "Objectif réglable dans Paramètres, règles de calcul ; 0 le masque"
        )
        self.goal_bar.hide()

        return self.goal_bar

    def show_week_goal(self, pGoal):
        """Affiche la progression de l'objectif, masquée sans objectif."""
        self.goal_bar.setVisible(pGoal["share"] is not None)

        if pGoal["share"] is not None:
            self.goal_bar.setValue(pGoal["share"])
            self.goal_bar.setFormat(
                f"Objectif de la semaine : {pGoal['sent']} / {pGoal['goal']} "
                "candidature(s)" + (" · atteint" if pGoal["share"] == 100 else "")
            )

    def create_checklist_card(self):
        """Construit la liste des réglages restant à faire."""
        self.checklist_card, vLayout = create_card(
            "À faire pour bien démarrer", "Cette carte disparaît une fois tout réglé"
        )

        self.checklist_layout = QVBoxLayout()
        self.checklist_layout.setSpacing(2)

        vLayout.addLayout(self.checklist_layout)
        self.checklist_card.hide()

        return self.checklist_card

    def create_checklist_row(self, pItem):
        """Construit une ligne cliquable qui ouvre la page où faire le réglage."""
        vButton = QPushButton()
        vButton.setObjectName("listRow")
        vButton.setCursor(Qt.CursorShape.PointingHandCursor)
        vButton.clicked.connect(lambda: self.navigation_requested.emit(pItem["page"]))

        vTitleLabel = QLabel(pItem["text"])
        vTitleLabel.setObjectName("activityTitle")

        vHintLabel = QLabel(pItem["hint"])
        vHintLabel.setObjectName("cardSubtitle")

        vLayout = QHBoxLayout(vButton)
        vLayout.setContentsMargins(8, 6, 8, 6)
        vLayout.setSpacing(12)
        vLayout.addWidget(create_icon_label("circle-alert", COLORS["warning"], 20))
        vLayout.addWidget(vTitleLabel)
        vLayout.addWidget(vHintLabel, 1)

        vButton.setMinimumHeight(vLayout.sizeHint().height())

        return vButton

    def show_checklist(self, pChecklist):
        """Affiche les réglages manquants ; la carte est masquée quand tout est fait."""
        self.checklist_card.setVisible(bool(pChecklist))
        self.show_rows(
            self.checklist_layout,
            [self.create_checklist_row(vItem) for vItem in pChecklist],
            "",
        )

    def create_chart_card(self):
        """Construit le graphique des nouvelles offres par jour."""
        vCard, vLayout = create_card(
            "Activité",
            "Nouvelles offres, candidatures et relances par jour",
        )

        self.chart = BarChart()
        # Plus bas qu'ailleurs : l'accueil tient sans défiler dans une fenêtre réduite,
        # le graphique s'agrandit quand la place le permet.
        self.chart.setMinimumHeight(HOME_CHART_MIN_HEIGHT)

        vLayout.addWidget(self.chart, 1)

        return vCard

    def create_follow_ups_card(self):
        """Construit la liste des prochaines relances prévues."""
        vCard, vLayout = create_card(
            "Relances à venir",
            "Les candidatures à relancer, les plus proches en premier",
        )

        self.follow_ups_layout = QVBoxLayout()
        self.follow_ups_layout.setSpacing(2)

        vLayout.addLayout(self.follow_ups_layout)
        vLayout.addStretch()

        return vCard

    def create_latest_offers_card(self):
        """Construit la liste des dernières offres découvertes."""
        vCard, vLayout = create_card(
            "Dernières offres", "Les offres découvertes le plus récemment"
        )

        self.latest_offers_layout = QVBoxLayout()
        self.latest_offers_layout.setSpacing(2)

        vLayout.addLayout(self.latest_offers_layout)
        vLayout.addStretch()

        return vCard

    def create_offer_row(self, pIcon, pColor, pTitle, pDetail, pResult, pKey):
        """Construit une ligne cliquable qui ouvre l'offre dans la page des offres."""
        vButton = QPushButton()
        vButton.setObjectName("listRow")
        vButton.setCursor(Qt.CursorShape.PointingHandCursor)
        vButton.clicked.connect(
            lambda: self.offer_requested.emit(
                [pKey], f"Offre ouverte depuis l'accueil : {pTitle}"
            )
        )

        vTitleLabel = QLabel(pTitle)
        vTitleLabel.setObjectName("activityTitle")

        vDetailLabel = QLabel(pDetail)
        vDetailLabel.setObjectName("cardSubtitle")

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitleLabel)
        vTexts.addWidget(vDetailLabel)

        vResultLabel = QLabel(pResult)
        vResultLabel.setObjectName("activityResult")

        vLayout = QHBoxLayout(vButton)
        vLayout.setContentsMargins(8, 6, 8, 6)
        vLayout.setSpacing(12)
        vLayout.addWidget(create_icon_label(pIcon, pColor, 20))
        vLayout.addLayout(vTexts, 1)
        vLayout.addWidget(vResultLabel)

        vButton.setMinimumHeight(vLayout.sizeHint().height())

        return vButton

    def show_rows(self, pLayout, pRows, pEmptyText):
        """Remplace les lignes d'une liste, ou affiche un message si elle est vide."""
        while pLayout.count():
            pLayout.takeAt(0).widget().deleteLater()

        if not pRows:
            vEmpty = QLabel(pEmptyText)
            vEmpty.setObjectName("cardSubtitle")
            pLayout.addWidget(vEmpty)

        for vRow in pRows:
            pLayout.addWidget(vRow)

    def show_follow_ups(self, pFollowUps):
        """Affiche les prochaines relances, en orange lorsqu'elles sont dues."""
        vToday = datetime.now().isoformat()

        self.show_rows(
            self.follow_ups_layout,
            [
                self.create_offer_row(
                    "bell-ring",
                    COLORS[
                        (
                            "warning"
                            if vFollowUp["follow_up_date"] <= vToday
                            else "primary"
                        )
                    ],
                    vFollowUp["title"] or "Titre non communiqué",
                    vFollowUp["company"] or "",
                    format_date(vFollowUp["follow_up_date"]),
                    (vFollowUp["source"], vFollowUp["source_id"]),
                )
                for vFollowUp in pFollowUps
            ],
            "Aucune relance prévue.",
        )

    def create_similar_offers_card(self):
        """Construit la liste des nouvelles offres proches de celles retenues."""
        self.similar_offers_card, vLayout = create_card(
            "Offres proches de vos candidatures",
            "Nouvelles offres qui partagent compétences et intitulé avec celles "
            "que vous avez retenues",
        )

        self.similar_offers_layout = QVBoxLayout()
        self.similar_offers_layout.setSpacing(2)

        vLayout.addLayout(self.similar_offers_layout)

        return self.similar_offers_card

    def show_similar_offers(self, pOffers):
        """Affiche les offres proches ; la carte est masquée sans offre retenue."""
        self.similar_offers_card.setVisible(bool(pOffers))
        self.show_rows(
            self.similar_offers_layout,
            [
                self.create_offer_row(
                    "target",
                    COLORS["primary"],
                    vOffer["title"] or "Titre non communiqué",
                    " · ".join(
                        vPart
                        for vPart in (
                            vOffer.get("company"),
                            f"proche de « {vOffer['reference_title']} »",
                        )
                        if vPart
                    ),
                    f"{vOffer['similarity']} %",
                    (vOffer["source"], vOffer["source_id"]),
                )
                for vOffer in pOffers
            ],
            "",
        )

    def show_latest_offers(self, pOffers):
        """Affiche les dernières offres avec leur source, leur salaire et leur date."""
        self.show_rows(
            self.latest_offers_layout,
            [
                self.create_offer_row(
                    "sparkles" if vOffer["is_new"] else "briefcase",
                    COLORS["success" if vOffer["is_new"] else "muted"],
                    vOffer["title"] or "Titre non communiqué",
                    " · ".join(
                        vPart
                        for vPart in (
                            vOffer["company"],
                            vOffer["source_label"],
                            format_net_salary(vOffer),
                        )
                        if vPart
                    ),
                    format_date(vOffer["published_at"] or vOffer["first_seen_at"]),
                    (vOffer["source"], vOffer["source_id"]),
                )
                for vOffer in pOffers
            ],
            "Aucune offre en base pour le moment.",
        )

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

    def create_activity_row(self, pEntry):
        """Construit la ligne d'une exécution dans l'activité récente."""
        vIcon, vColor, vTitle, vDetail, vSources, vResult = describe_activity(pEntry)

        vTitleLabel = QLabel(vTitle)
        vTitleLabel.setObjectName("activityTitle")

        vDetailLabel = QLabel(vDetail)
        vDetailLabel.setObjectName("cardSubtitle")
        vDetailLabel.setToolTip(vSources)

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
            # La page est relue à chaque affichage (MainWindow.show_page) : les chiffres
            # suivent les recherches et candidatures faites ailleurs, web compris.
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

            self.show_week_goal(vStatistics["week_goal"])
            self.show_activity(vStatistics["executions"])
            self.show_chart(vStatistics["daily_activity"])
            self.show_follow_ups(vStatistics["upcoming_follow_ups"])
            self.show_latest_offers(vStatistics["latest_offers"])
            self.show_similar_offers(vStatistics["similar_offers"])
            self.show_checklist(build_setup_checklist(self.database_file))
            self.last_search_label.setText(
                describe_last_search(vStatistics["executions"])
            )

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
            pAxes=ACTIVITY_AXES,
            pEmptyText=EMPTY_CHART_TEXT,
        )
