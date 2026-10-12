"""Page de qualité des données : remplissage des champs et offres à vérifier"""

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import COLORS
from gui.widgets import create_button, create_card, create_page_header
from job.quality import (
    PROBLEMS_HELP,
    build_quality_export,
    describe_problems,
    get_quality_report,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class QualityPage(QWidget):
    """Montre quels champs les sources remplissent, pour repérer les manques."""

    def __init__(self, pDatabaseFile):
        """Construit le graphique, le tableau et l'export ; les données par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.export_button = create_button(
            "Exporter les offres à vérifier", "download", pIconColor=COLORS["primary"]
        )
        self.export_button.setToolTip(
            "CSV des offres incomplètes ou mal découpées, avec le défaut repéré"
        )
        self.export_button.clicked.connect(self.export_problems)

        self.problems_label = QLabel()
        self.problems_label.setObjectName("activityTitle")
        self.problems_label.setWordWrap(True)

        vProblemsHelp = QLabel(PROBLEMS_HELP)
        vProblemsHelp.setObjectName("cardSubtitle")
        vProblemsHelp.setWordWrap(True)

        vProblemsCard, vProblemsLayout = create_card("Offres à vérifier")
        vProblemsLayout.addWidget(self.problems_label)
        vProblemsLayout.addWidget(vProblemsHelp)

        self.chart = BarChart()
        self.chart.setMinimumHeight(220)

        vChartCard, vChartLayout = create_card(
            "Remplissage global",
            "Part des offres en base dont le champ est renseigné, toutes sources",
        )
        vChartLayout.addWidget(self.chart, 1)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        vTableCard, vTableLayout = create_card(
            "Par source",
            "Vert : 80 % et plus · orange : 40 % et plus · rouge : en dessous",
        )
        vTableLayout.addWidget(self.table, 1)

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.setWordWrap(True)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Qualité des données",
            "Les informations fournies par chaque source, pour voir ce qui manque",
            [self.export_button],
            pIcon="list-checks",
        )

        vLayout.addWidget(vChartCard)
        vLayout.addWidget(vProblemsCard)
        vLayout.addWidget(vTableCard, 1)
        vLayout.addWidget(self.message_label)

    def refresh(self):
        """Relit le remplissage des champs en base."""
        try:
            vReport = get_quality_report(self.database_file)

        except Exception:
            logger.exception("Impossible de calculer la qualité des données")

            self.message_label.setText("La qualité des données n'a pas pu être lue.")

        else:
            self.show_report(vReport)

    def show_report(self, pReport):
        """Affiche le graphique global et le tableau par source."""
        self.chart.set_series(
            pReport["columns"],
            [
                (
                    "Remplissage",
                    # Mêmes couleurs que le tableau : vert, orange ou rouge selon le taux
                    [COLORS[vRate["tone"]] for vRate in pReport["total"]["rates"]],
                    [vRate["rate"] for vRate in pReport["total"]["rates"]],
                )
            ],
            pAxes=("Champ", "% des offres renseignées"),
            pEmptyText="Aucune offre en base pour le moment",
            pFillWidth=True,
        )

        self.table.setColumnCount(len(pReport["columns"]) + 2)
        self.table.setHorizontalHeaderLabels(["Source", "Offres"] + pReport["columns"])
        self.table.setRowCount(len(pReport["rows"]))

        for vRow, vSource in enumerate(pReport["rows"]):
            self.table.setItem(vRow, 0, QTableWidgetItem(vSource["source"]))
            self.table.setItem(vRow, 1, QTableWidgetItem(str(vSource["count"])))

            for vColumn, vRate in enumerate(vSource["rates"], start=2):
                vItem = QTableWidgetItem(f"{vRate['rate']} %")
                vItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                vItem.setForeground(QColor(COLORS[vRate["tone"]]))
                self.table.setItem(vRow, vColumn, vItem)

        vProblems = pReport["problems"]

        self.export_button.setText(
            f"Exporter les offres à vérifier ({vProblems['total']})"
            if vProblems["total"]
            else "Aucune offre à vérifier"
        )
        self.export_button.setEnabled(bool(vProblems["total"]))
        self.problems_label.setText(describe_problems(vProblems))

        self.message_label.setText(
            f"{pReport['total']['count']} offre(s) analysée(s), "
            f"{pReport['rejected']} écartée(s) faute de titre et de description. "
        )

    def export_problems(self):
        """Enregistre le CSV des offres à vérifier dans un fichier choisi."""
        vFileName, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les offres à vérifier",
            f"offres-a-verifier-{date.today():%Y%m%d}.csv",
            "CSV (*.csv)",
        )

        if vFileName:
            try:
                Path(vFileName).write_text(
                    build_quality_export(self.database_file), encoding="utf-8"
                )

            except Exception:
                logger.exception("Échec de l'export des offres à vérifier")

                self.message_label.setText("L'export n'a pas pu être enregistré.")

            else:
                self.message_label.setText(f"Offres à vérifier exportées : {vFileName}")
