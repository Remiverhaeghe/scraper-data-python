"""Page de l'historique des exécutions"""

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.icons import get_icon
from gui.chart import BarChart, PieChart
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_card,
    create_page_header,
    show_message,
)
from job.presentation import (
    CHART_PALETTE,
    EXECUTION_STATUS_LABELS,
    UNKNOWN_SEARCH,
    describe_search,
    describe_sources,
    summarize_history,
)
from job.statistics import (
    EXECUTION_AXES,
    EXECUTION_CHART_SIZE,
    SOURCE_COMPARISON_COLUMNS,
    SOURCE_COMPARISON_DAYS,
    build_source_cells,
    compare_saved_searches,
    compare_sources,
    build_month_summary,
    describe_interview_sources,
    describe_useless_sources,
    get_contract_shares,
    get_execution_counts,
    get_source_shares,
)
from storage.history_repository import get_history, get_history_summary
from utils.logger import get_logger

logger = get_logger(__name__)

# Les exécutions plus anciennes restent en base mais ne sont pas affichées
MAX_DISPLAYED_EXECUTIONS = 200

COLUMNS = ["Date", "Recherche et sources", "Offres", "Durée", "Statut"]

# Icône et couleur de chaque statut d'exécution
STATUS_ICONS = {
    "success": ("circle-check", "success"),
    "partial": ("circle-alert", "warning"),
    "error": ("circle-alert", "danger"),
}


def build_row(pEntry):
    """Retourne les textes d'une ligne de l'historique."""

    if pEntry.scraper_type == "job":
        vSearch = describe_search(pEntry.parameters) or UNKNOWN_SEARCH
    else:
        vSearch = f"Livres · {pEntry.url}"

    # Les sources sont affichées sous les critères, dans la même cellule.
    vSources = describe_sources(pEntry.parameters)

    rRow = [
        f"{pEntry.started_at:%d/%m/%Y %H:%M}",
        f"{vSearch}\n{vSources}" if vSources else vSearch,
        str(pEntry.item_count),
        f"{pEntry.duration_seconds:.1f} s",
        EXECUTION_STATUS_LABELS.get(pEntry.status, pEntry.status),
    ]

    return rRow


class HistoryPage(QWidget):
    """Affiche la synthèse et la liste des dernières exécutions."""

    def __init__(self, pDatabaseFile):
        """Construit les cartes de synthèse et le tableau."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.cards = {
            "executions": StatisticCard("Exécutions", "history", "blue"),
            "item_count": StatisticCard("Offres récupérées", "briefcase", "green"),
            "average_duration": StatisticCard("Durée moyenne", "timer", "amber"),
            "success_rate": StatisticCard("Taux de réussite", "circle-check", "purple"),
        }

        vCards = QGridLayout()
        vCards.setSpacing(18)

        for vIndex, vCard in enumerate(self.cards.values()):
            vCards.addWidget(vCard, 0, vIndex)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()

        vHeader = self.table.horizontalHeader()
        vHeader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Historique",
            "Chaque recherche lancée, ses critères et son résultat",
            pIcon="history",
        )

        vLayout.addLayout(vCards)
        vLayout.addLayout(self.create_charts())
        vLayout.addWidget(self.create_month_card())
        vLayout.addWidget(self.create_comparison_card())
        vLayout.addWidget(self.create_search_comparison_card())
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.table, 1)

    @staticmethod
    def create_comparison_table(pFirstColumn):
        """Crée un tableau de comparaison en lecture seule, sans défilement interne."""
        rTable = QTableWidget(0, len(SOURCE_COMPARISON_COLUMNS))
        rTable.setHorizontalHeaderLabels([pFirstColumn, *SOURCE_COMPARISON_COLUMNS[1:]])
        rTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rTable.setAlternatingRowColors(True)
        rTable.verticalHeader().hide()
        rTable.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        vHeader = rTable.horizontalHeader()
        vHeader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        return rTable

    def create_comparison_card(self):
        """Construit le tableau qui compare l'utilité des sources."""
        self.comparison_table = self.create_comparison_table("Source")

        rCard, vLayout = create_card(
            "Comparaison des sources",
            f"Offres découvertes ces {SOURCE_COMPARISON_DAYS} derniers jours : "
            "correspondance au profil et suites données",
        )
        self.useless_label = QLabel()
        self.useless_label.setObjectName("cardSubtitle")
        self.useless_label.setWordWrap(True)

        vLayout.addWidget(self.comparison_table)
        vLayout.addWidget(self.useless_label)

        return rCard

    def create_month_card(self):
        """Construit le bilan des 30 derniers jours, comparés aux 30 précédents."""
        vCard, vLayout = create_card(
            "Votre mois",
            "Les 30 derniers jours, comparés aux 30 précédents",
            pIcon="calendar",
        )

        self.month_label = QLabel()
        self.month_label.setWordWrap(True)
        vLayout.addWidget(self.month_label)

        return vCard

    def show_month(self, pMonth):
        """Affiche chaque série du mois, son évolution et les entretiens par source."""
        self.month_label.setText(
            " · ".join(
                f"<b>{vRow['current']}</b> {escape(vRow['label'])} ({vRow['trend']})"
                for vRow in pMonth["rows"]
            )
            + f"<br>{escape(describe_interview_sources(pMonth['interview_sources']))}"
        )

    def create_search_comparison_card(self):
        """Construit le tableau qui compare les recherches enregistrées."""
        self.search_table = self.create_comparison_table("Recherche")

        self.search_card, vLayout = create_card(
            "Comparaison des recherches enregistrées",
            f"Offres de ces {SOURCE_COMPARISON_DAYS} derniers jours qui répondent aux "
            "critères de chaque recherche : celles qui mènent à des candidatures en tête",
        )
        vLayout.addWidget(self.search_table)

        return self.search_card

    @staticmethod
    def fill_comparison_table(pTable, pRows):
        """Remplit un tableau de comparaison, ajusté à son nombre de lignes."""
        pTable.setRowCount(len(pRows))

        for vRow, vData in enumerate(pRows):
            for vColumn, vText in enumerate(build_source_cells(vData)):
                vItem = QTableWidgetItem(vText)

                if vColumn:
                    vItem.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                pTable.setItem(vRow, vColumn, vItem)

        # Toutes les lignes visibles, sans barre de défilement interne
        pTable.setFixedHeight(
            pTable.horizontalHeader().height()
            + sum(pTable.rowHeight(vRow) for vRow in range(len(pRows)))
            + 2 * pTable.frameWidth()
        )

    def fill_comparison(self):
        """Remplit les comparaisons des sources et des recherches enregistrées."""
        vRows = compare_sources(self.database_file, datetime.now())
        vAdvice = describe_useless_sources(vRows)

        show_message(self.useless_label, vAdvice, "warning")
        self.useless_label.setVisible(bool(vAdvice))
        self.fill_comparison_table(self.comparison_table, vRows)

        vSearches = compare_saved_searches(self.database_file, datetime.now())
        self.search_card.setVisible(bool(vSearches))
        self.fill_comparison_table(self.search_table, vSearches)

    def create_charts(self):
        """Construit la répartition par source et le rendement des exécutions."""
        vSourceCard, vSourceLayout = create_card(
            "Répartition des offres",
            "Offres actuellement en base",
        )

        self.source_chart = PieChart("Par source")
        self.contract_chart = PieChart("Par contrat")

        vCharts = QHBoxLayout()
        vCharts.setSpacing(18)
        vCharts.addWidget(self.source_chart, 1)
        vCharts.addWidget(self.contract_chart, 1)

        vSourceLayout.addLayout(vCharts, 1)

        vExecutionCard, vExecutionLayout = create_card(
            "Rendement des recherches",
            f"Offres récupérées lors des {EXECUTION_CHART_SIZE} dernières exécutions",
        )

        self.execution_chart = BarChart()
        vExecutionLayout.addWidget(self.execution_chart, 1)

        rLayout = QHBoxLayout()
        rLayout.setSpacing(18)
        rLayout.addWidget(vSourceCard, 1)
        rLayout.addWidget(vExecutionCard, 1)

        return rLayout

    def fill_row(self, pRow, pEntry):
        """Remplit une ligne du tableau ; l'erreur éventuelle est en infobulle."""
        for vColumn, vText in enumerate(build_row(pEntry)):
            vItem = QTableWidgetItem(vText)

            if vText == UNKNOWN_SEARCH:
                vItem.setForeground(QColor(COLORS["muted"]))

            self.table.setItem(pRow, vColumn, vItem)

        vIcon, vColorName = STATUS_ICONS.get(pEntry.status, STATUS_ICONS["error"])

        vStatusItem = self.table.item(pRow, len(COLUMNS) - 1)
        vStatusItem.setIcon(get_icon(vIcon, COLORS[vColorName], 16))

        if pEntry.error_message:
            vStatusItem.setToolTip(pEntry.error_message)

    def refresh(self):
        """Relit la synthèse et l'historique en base."""
        try:
            vEntries = get_history(self.database_file, pLimit=MAX_DISPLAYED_EXECUTIONS)
            vSummary = get_history_summary(self.database_file)

        except Exception:
            logger.exception("Impossible de charger l'historique")

            show_message(
                self.message_label,
                "L'historique n'a pas pu être chargé.",
                "danger",
            )

        else:
            for vName, vValue in summarize_history(vSummary).items():
                self.cards[vName].set_value(vValue)

            self.show_month(build_month_summary(self.database_file, datetime.now()))

            self.source_chart.set_shares(
                [
                    (vShare["label"], vShare["count"], CHART_PALETTE[vIndex])
                    for vIndex, vShare in enumerate(
                        get_source_shares(self.database_file)
                    )
                ]
            )

            self.contract_chart.set_shares(
                [
                    (vShare["label"], vShare["count"], CHART_PALETTE[vIndex])
                    for vIndex, vShare in enumerate(
                        get_contract_shares(self.database_file)
                    )
                ]
            )

            self.fill_comparison()

            vExecutions = get_execution_counts(self.database_file)

            self.execution_chart.set_series(
                [vLabel for vLabel, _ in vExecutions],
                [
                    (
                        "Offres",
                        CHART_PALETTE[0],
                        [vCount for _, vCount in vExecutions],
                    )
                ],
                pAxes=EXECUTION_AXES,
                pEmptyText="Aucune exécution pour le moment",
            )

            self.table.setRowCount(len(vEntries))

            for vRow, vEntry in enumerate(vEntries):
                self.fill_row(vRow, vEntry)

            # Les critères et les sources tiennent sur deux lignes.
            self.table.resizeRowsToContents()

            show_message(
                self.message_label,
                (
                    f"{len(vEntries)} dernière(s) exécution(s) · survolez un statut "
                    "pour lire le détail d'une erreur"
                    if vEntries
                    else "Aucune exécution enregistrée pour le moment."
                ),
                None,
            )
