"""Page de l'historique des exécutions"""

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
from gui.widgets import StatisticCard, create_card, create_page_header
from job.presentation import (
    CHART_PALETTE,
    EXECUTION_STATUS_LABELS,
    UNKNOWN_SEARCH,
    describe_search,
    describe_sources,
    summarize_history,
)
from job.statistics import (
    EXECUTION_CHART_SIZE,
    get_execution_counts,
    get_source_shares,
)
from storage.history_repository import get_history, get_history_summary
from utils.logger import get_logger

logger = get_logger(__name__)

# Les exécutions plus anciennes restent en base mais ne sont pas affichées
MAX_DISPLAYED_EXECUTIONS = 200

COLUMNS = ["Date", "Recherche", "Sources", "Offres", "Durée", "Statut"]

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

    rRow = [
        f"{pEntry.started_at:%d/%m/%Y %H:%M}",
        vSearch,
        describe_sources(pEntry.parameters) or "—",
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
        vHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

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
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.table, 1)

    def create_charts(self):
        """Construit la répartition par source et le rendement des exécutions."""
        vSourceCard, vSourceLayout = create_card(
            "Offres par source", "Répartition des offres actuellement en base"
        )

        self.source_chart = PieChart()
        vSourceLayout.addWidget(self.source_chart, 1)

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
        """Remplit une ligne du tableau, avec l'icône du statut et l'erreur en infobulle."""
        for vColumn, vText in enumerate(build_row(pEntry)):
            vItem = QTableWidgetItem(vText)

            if vText in (UNKNOWN_SEARCH, "—"):
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

            self.message_label.setText("L'historique n'a pas pu être chargé.")

        else:
            for vName, vValue in summarize_history(vSummary).items():
                self.cards[vName].set_value(vValue)

            self.source_chart.set_shares(
                [
                    (vShare["label"], vShare["count"], CHART_PALETTE[vIndex])
                    for vIndex, vShare in enumerate(
                        get_source_shares(self.database_file)
                    )
                ]
            )

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
            )

            self.table.setRowCount(len(vEntries))

            for vRow, vEntry in enumerate(vEntries):
                self.fill_row(vRow, vEntry)

            self.message_label.setText(
                f"{len(vEntries)} dernière(s) exécution(s) · survolez un statut "
                "pour lire le détail d'une erreur"
                if vEntries
                else "Aucune exécution enregistrée pour le moment."
            )
