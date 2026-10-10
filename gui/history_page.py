"""Page de l'historique des exécutions"""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import create_page_header
from job.presentation import EXECUTION_STATUS_LABELS, describe_search, describe_sources
from storage.history_repository import get_history
from utils.logger import get_logger

logger = get_logger(__name__)

# Les exécutions plus anciennes restent en base mais ne sont pas affichées
MAX_DISPLAYED_EXECUTIONS = 200

COLUMNS = ["Date", "Recherche", "Sources", "Offres", "Durée", "Statut"]


def build_row(pEntry):
    """Retourne les textes d'une ligne de l'historique."""

    if pEntry.scraper_type == "job":
        vSearch = describe_search(pEntry.parameters)
    else:
        vSearch = f"Livres · {pEntry.url}"

    rRow = [
        f"{pEntry.started_at:%d/%m/%Y %H:%M}",
        vSearch,
        describe_sources(pEntry.parameters),
        str(pEntry.item_count),
        f"{pEntry.duration_seconds:.1f} s",
        EXECUTION_STATUS_LABELS.get(pEntry.status, pEntry.status),
    ]

    return rRow


class HistoryPage(QWidget):
    """Liste les dernières exécutions, les plus récentes en premier."""

    def __init__(self, pDatabaseFile):
        """Construit le tableau de l'historique."""
        super().__init__()

        self.database_file = pDatabaseFile

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

        create_page_header(
            vLayout,
            "Historique",
            "Dernières exécutions ; survolez un statut pour voir le détail d'une erreur",
        )

        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.table, 1)

    def refresh(self):
        """Relit l'historique en base."""
        try:
            vEntries = get_history(self.database_file, pLimit=MAX_DISPLAYED_EXECUTIONS)

        except Exception:
            logger.exception("Impossible de charger l'historique")

            self.message_label.setText("L'historique n'a pas pu être chargé.")

        else:
            self.table.setRowCount(len(vEntries))

            for vRow, vEntry in enumerate(vEntries):
                for vColumn, vText in enumerate(build_row(vEntry)):
                    self.table.setItem(vRow, vColumn, QTableWidgetItem(vText))

                if vEntry.error_message:
                    self.table.item(vRow, len(COLUMNS) - 1).setToolTip(
                        vEntry.error_message
                    )

            self.message_label.setText(
                f"{len(vEntries)} exécution(s)"
                if vEntries
                else "Aucune exécution enregistrée pour le moment."
            )
