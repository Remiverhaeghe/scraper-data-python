"""Page Mon marché : demande et salaires par compétence et par ville"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.market import (
    CITY_COLUMNS,
    HISTORY_COLUMNS,
    MARKET_DAYS,
    REGION_COLUMNS,
    SKILL_COLUMNS,
    build_history_cells,
    build_market,
    build_market_cells,
    build_market_history,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def create_table(pColumns):
    """Crée un tableau en lecture seule, première colonne étirée."""

    rTable = QTableWidget(0, len(pColumns))
    rTable.setHorizontalHeaderLabels(pColumns)
    rTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    rTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    rTable.verticalHeader().hide()
    rTable.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    rTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    rTable.setMinimumHeight(320)

    return rTable


def fill_table(pTable, pRows, pWithMine=False):
    """Remplace les lignes d'un tableau par celles du marché."""

    pTable.setRowCount(len(pRows))

    for vRowIndex, vRow in enumerate(pRows):
        for vColumn, vText in enumerate(build_market_cells(vRow, pWithMine)):
            pTable.setItem(vRowIndex, vColumn, QTableWidgetItem(vText))


class MarketPage(QWidget):
    """Affiche le marché tiré des offres récentes : volumes et salaires."""

    # Compétences prioritaires dont l'examen blanc est demandé
    exam_requested = Signal(list)

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        vContent = create_scroll_content(self)
        vLayout = QVBoxLayout(vContent)
        vLayout.setContentsMargins(32, 18, 32, 18)
        vLayout.setSpacing(12)

        create_page_header(
            vLayout,
            "Mon marché",
            f"Offres en France des {MARKET_DAYS} derniers jours, hors stage, "
            "alternance et mission libre",
            pIcon="banknote",
        )

        self.cards = {
            "offer_count": StatisticCard("Offres analysées", "briefcase", "blue"),
            "salaried_count": StatisticCard("Avec un salaire", "banknote", "green"),
            "median": StatisticCard("Net mensuel médian", "scale", "amber"),
            "target": StatisticCard("Votre salaire visé", "target", "purple"),
        }

        vCards = QGridLayout()
        vCards.setSpacing(18)

        for vIndex, vCard in enumerate(self.cards.values()):
            vCards.addWidget(vCard, 0, vIndex)

        vLayout.addLayout(vCards)

        vPriorityCard, vPriorityLayout = create_card(
            "À travailler en priorité",
            "Compétences les plus demandées que vous n'avez pas évaluées, ou notées "
            "sous 5 : à réviser, ou à évaluer dans Profil",
            pIcon="target",
            pOpen=True,
        )
        self.priority_label = QLabel()
        self.priority_label.setWordWrap(True)
        vPriorityLayout.addWidget(self.priority_label)

        self.priority_skills = []
        self.exam_button = create_button(
            "Examen blanc sur ces compétences", "timer", pObjectName="primaryButton"
        )
        self.exam_button.clicked.connect(
            lambda: self.exam_requested.emit(self.priority_skills)
        )
        vPriorityLayout.addWidget(self.exam_button, 0, Qt.AlignmentFlag.AlignLeft)
        vLayout.addWidget(vPriorityCard)

        vHistoryCard, vHistoryLayout = create_card(
            "Évolution du marché",
            "Offres vues chaque mois, et celles qui citent une compétence de votre "
            "profil",
            pOpen=True,
        )
        self.history_chart = BarChart()
        self.history_chart.setMinimumHeight(200)
        self.history_table = create_table(HISTORY_COLUMNS)
        self.history_table.setMinimumHeight(140)
        vHistoryLayout.addWidget(self.history_chart)
        vHistoryLayout.addWidget(self.history_table)
        vLayout.addWidget(vHistoryCard)

        vSkillsCard, vSkillsLayout = create_card(
            "Compétences les plus demandées",
            "Médiane affichée à partir de trois salaires",
            pOpen=True,
        )
        self.skills_table = create_table(SKILL_COLUMNS)
        vSkillsLayout.addWidget(self.skills_table)
        vLayout.addWidget(vSkillsCard)

        vRegionsCard, vRegionsLayout = create_card("Régions qui recrutent le plus")
        self.regions_table = create_table(REGION_COLUMNS)
        vRegionsLayout.addWidget(self.regions_table)
        vLayout.addWidget(vRegionsCard)

        vCitiesCard, vCitiesLayout = create_card("Villes qui recrutent le plus")
        self.cities_table = create_table(CITY_COLUMNS)
        vCitiesLayout.addWidget(self.cities_table)
        vLayout.addWidget(vCitiesCard)
        vLayout.addStretch()

    def show_history(self, pHistory):
        """Affiche l'évolution du marché : graphique et tableau mois par mois."""
        self.history_chart.set_series(
            [vMonth["label"] for vMonth in pHistory],
            [
                (
                    "Offres",
                    COLORS["primary"],
                    [vMonth["offers"] for vMonth in pHistory],
                ),
                (
                    "Avec vos compétences",
                    COLORS["success"],
                    [vMonth["mine"] for vMonth in pHistory],
                ),
            ],
            pAxes=("Mois", "Offres vues"),
            pEmptyText="Aucune offre pour le moment",
        )
        self.history_table.setRowCount(len(pHistory))

        for vRowIndex, vMonth in enumerate(pHistory):
            for vColumn, vText in enumerate(build_history_cells(vMonth)):
                self.history_table.setItem(vRowIndex, vColumn, QTableWidgetItem(vText))

    def refresh(self):
        """Recalcule le marché à partir des offres en base."""
        try:
            vMarket = build_market(self.database_file, datetime.now())
            vHistory = build_market_history(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de calculer le marché")

            return

        for vName, vCard in self.cards.items():
            vCard.set_value(vMarket[vName])

        # Sans salaire visé, la carte renvoie vers les Paramètres.
        if vMarket["target"] is None:
            self.cards["target"].set_value("À régler")

        self.priority_skills = [vSkill["name"] for vSkill in vMarket["priorities"]]
        self.exam_button.setEnabled(bool(self.priority_skills))
        self.priority_label.setText(
            "\n".join(
                f"{vSkill['name']} · {vSkill['label']}"
                for vSkill in vMarket["priorities"]
            )
            or "Toutes les compétences les plus demandées sont maîtrisées."
        )
        self.show_history(vHistory)
        fill_table(self.skills_table, vMarket["skills"], pWithMine=True)
        fill_table(self.regions_table, vMarket["regions"])
        self.regions_table.setToolTip(
            f"{vMarket['unknown_region_count']} offre(s) pas encore placée(s) sur la "
            "carte ne sont pas classées"
        )
        fill_table(self.cities_table, vMarket["cities"])
        self.cities_table.setToolTip(
            f"{vMarket['unknown_city_count']} offre(s) sans ville ne sont pas classées"
        )
