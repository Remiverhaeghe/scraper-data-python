"""Page de consultation des logs de l'application"""

from datetime import date
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_page_header
from utils.log_reader import (
    LEVEL_FILTERS,
    clear_logs,
    export_logs,
    LEVEL_TONES,
    MAX_LOG_ENTRIES,
    read_log_entries,
)
from utils.logger import get_logger, get_retention_days

logger = get_logger(__name__)

COLUMNS = ["Date", "Niveau", "Module", "Message"]

# Largeurs fixes : un calcul d'après le contenu, refait à chaque changement de
# mise en page, figeait l'application sur plusieurs centaines de lignes.
COLUMN_WIDTHS = (150, 120, 230)


class LogsPage(QWidget):
    """Affiche les derniers logs, filtrables par niveau et par texte."""

    def __init__(self):
        """Construit les filtres et le tableau ; les logs sont lus par refresh."""
        super().__init__()

        self.level_combo = QComboBox()

        for vLevel, vLabel in LEVEL_FILTERS.items():
            self.level_combo.addItem(vLabel, vLevel)

        self.level_combo.currentIndexChanged.connect(self.refresh)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher dans les messages et modules")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.returnPressed.connect(self.refresh)

        vRefreshButton = create_button(
            "Actualiser", "history", pIconColor=COLORS["primary"]
        )
        vRefreshButton.clicked.connect(self.refresh)

        vDownloadButton = create_button(
            "Télécharger", "download", pIconColor=COLORS["primary"]
        )
        vDownloadButton.setToolTip("Enregistre tous les journaux conservés")
        vDownloadButton.clicked.connect(self.download_logs)

        vClearButton = create_button(
            "Vider", "circle-alert", "dangerButton", COLORS["danger"]
        )
        vClearButton.setToolTip("Efface tous les journaux, après confirmation")
        vClearButton.clicked.connect(self.confirm_clear)

        vFilters = QHBoxLayout()
        vFilters.setSpacing(12)
        vFilters.addWidget(self.level_combo)
        vFilters.addWidget(self.search_edit, 1)
        vFilters.addWidget(vRefreshButton)
        vFilters.addWidget(vDownloadButton)
        vFilters.addWidget(vClearButton)

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()

        vHeader = self.table.horizontalHeader()
        vHeader.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        vHeader.setStretchLastSection(True)

        for vColumn, vWidth in enumerate(COLUMN_WIDTHS):
            self.table.setColumnWidth(vColumn, vWidth)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Journaux",
            "Ce que fait l'application, pour comprendre une erreur ou un résultat",
            pIcon="terminal",
        )

        vLayout.addLayout(vFilters)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.table, 1)

    def refresh(self):
        """Relit les logs avec les filtres choisis, les plus récents en premier."""
        try:
            vEntries = read_log_entries(
                pLevel=self.level_combo.currentData(),
                pSearch=self.search_edit.text().strip() or None,
            )

        except OSError:
            logger.exception("Impossible de lire les fichiers de logs")

            vEntries = []
            self.message_label.setText("Les fichiers de logs n'ont pas pu être lus.")

        else:
            self.message_label.setText(
                f"{len(vEntries)} entrée(s) affichée(s), {MAX_LOG_ENTRIES} au plus · "
                f"logs conservés {get_retention_days()} jours · le détail d'une "
                "erreur s'affiche au survol du message"
            )

        self.show_entries(vEntries)

    def download_logs(self):
        """Enregistre tous les journaux conservés dans un fichier choisi."""
        vFileName, _ = QFileDialog.getSaveFileName(
            self,
            "Télécharger les journaux",
            f"journaux-{date.today():%Y%m%d}.log",
            "Journaux (*.log)",
        )

        if vFileName:
            try:
                Path(vFileName).write_text(export_logs(), encoding="utf-8")

            except OSError:
                logger.exception("Échec de l'export des journaux")

                self.message_label.setText(
                    "Les journaux n'ont pas pu être enregistrés."
                )

            else:
                self.message_label.setText(f"Journaux enregistrés : {vFileName}")

    def confirm_clear(self):
        """Demande confirmation, puis efface tous les journaux."""
        vAnswer = QMessageBox.question(
            self,
            "Vider les journaux",
            "Effacer tous les journaux ? Téléchargez-les avant si vous voulez les "
            "garder.",
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            clear_logs()
            self.refresh()

    def show_entries(self, pEntries):
        """Remplit le tableau ; une trace d'erreur complète est en infobulle."""
        self.table.setRowCount(len(pEntries))

        for vRow, vEntry in enumerate(pEntries):
            vFirstLine = vEntry["message"].split("\n", 1)[0]

            for vColumn, vText in enumerate(
                (vEntry["time"], vEntry["level_label"], vEntry["module"], vFirstLine)
            ):
                vItem = QTableWidgetItem(vText)
                vItem.setToolTip(vEntry["message"])

                if vColumn == 1 and vEntry["level"] in LEVEL_TONES:
                    vItem.setForeground(QColor(COLORS[LEVEL_TONES[vEntry["level"]]]))

                self.table.setItem(vRow, vColumn, vItem)
