"""Page de qualité des données : remplissage, offres à vérifier et hors sujet"""

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.offer_purge_panel import OfferPurgePanel
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.quality import (
    PROBLEMS_HELP,
    build_quality_export,
    describe_problems,
    get_quality_report,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Hauteur du graphique : barres et noms des champs lisibles sans se chevaucher
CHART_HEIGHT = 300


def set_bold(pItem, pBold):
    """Met en gras une cellule du tableau, pour la ligne du total par exemple."""

    vFont = pItem.font()
    vFont.setBold(pBold)
    pItem.setFont(vFont)


class QualityPage(QWidget):
    """Montre quels champs les sources remplissent, pour repérer les manques."""

    def __init__(self, pDatabaseFile):
        """Construit les chiffres clés, le graphique et le tableau ; données par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.statistic_cards = {
            "count": StatisticCard("Offres analysées", "inbox", "blue"),
            "average": StatisticCard("Remplissage moyen", "list-checks", "green"),
            "weakest": StatisticCard("Champ le moins rempli", "circle-alert", "amber"),
            "best": StatisticCard("Source la plus complète", "trophy", "purple"),
        }

        vStatistics = QHBoxLayout()
        vStatistics.setSpacing(12)

        for vCard in self.statistic_cards.values():
            vStatistics.addWidget(vCard)

        self.chart = BarChart()
        self.chart.setMinimumHeight(CHART_HEIGHT)

        vChartCard, vChartLayout = create_card(
            "Remplissage global",
            "Part des offres en base dont le champ est renseigné, toutes sources",
        )
        vChartLayout.addWidget(self.chart)

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

        vProblemsCard, vProblemsLayout = create_card(
            "Offres à vérifier", pActions=[self.export_button]
        )
        vProblemsLayout.addWidget(self.problems_label)
        vProblemsLayout.addWidget(vProblemsHelp)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        vTableCard, vTableLayout = create_card(
            "Par source",
            "Vert : 80 % et plus · orange : 40 % et plus · rouge : en dessous. "
            "Les sources les mieux remplies d'abord.",
        )
        vTableLayout.addWidget(self.table)

        self.purge_panel = OfferPurgePanel(pDatabaseFile)
        self.purge_panel.purged.connect(lambda _: self.refresh())

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.setWordWrap(True)

        # Zone défilante : les cartes gardent leur hauteur dans une petite fenêtre.
        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Qualité des données",
            "Les informations fournies par chaque source, pour voir ce qui manque",
            pIcon="list-checks",
        )

        vLayout.addLayout(vStatistics)
        vLayout.addWidget(vChartCard)
        vLayout.addWidget(vProblemsCard)
        vLayout.addWidget(vTableCard)
        vLayout.addWidget(self.purge_panel)
        vLayout.addWidget(self.message_label)
        vLayout.addStretch(1)

    def refresh(self):
        """Relit le remplissage des champs en base."""
        try:
            vReport = get_quality_report(self.database_file)

        except Exception:
            logger.exception("Impossible de calculer la qualité des données")

            show_message(
                self.message_label,
                "La qualité des données n'a pas pu être lue.",
                "danger",
            )

        else:
            self.show_report(vReport)

    def show_statistics(self, pReport):
        """Affiche les chiffres clés : volume, moyenne, champ faible, meilleure source."""
        vSummary = pReport["summary"]

        self.statistic_cards["count"].set_value(str(pReport["total"]["count"]))
        self.statistic_cards["average"].set_value(
            f"{pReport['total']['average']['rate']} %"
        )

        for vKey, vLabel in (
            ("weakest", "Champ le moins rempli"),
            ("best", "Source la plus complète"),
        ):
            vValue = vSummary[vKey]
            self.statistic_cards[vKey].set_value(f"{vValue[1]} %" if vValue else "-")
            self.statistic_cards[vKey].set_label(
                f"{vLabel} : {vValue[0]}" if vValue else vLabel
            )

    def set_rate_item(self, pRow, pColumn, pRate, pBold=False):
        """Place un taux dans le tableau, sur un fond teinté selon sa tonalité."""
        vItem = QTableWidgetItem(f"{pRate['rate']} %")
        vItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        vItem.setForeground(QColor(COLORS[pRate["tone"]]))
        vItem.setBackground(QColor(COLORS[f"{pRate['tone']}_light"]))
        set_bold(vItem, pBold)
        self.table.setItem(pRow, pColumn, vItem)

    def show_table(self, pReport):
        """Remplit le tableau par source, moyenne en tête et total en dernière ligne."""
        vRows = sorted(pReport["rows"], key=lambda pRow: -pRow["average"]["rate"])
        vRows.append({**pReport["total"], "source": "Toutes sources"})

        self.table.setColumnCount(len(pReport["columns"]) + 3)
        self.table.setHorizontalHeaderLabels(
            ["Source", "Offres", "Moyenne"] + pReport["columns"]
        )
        self.table.setRowCount(len(vRows))

        for vRow, vSource in enumerate(vRows):
            vTotal = vRow == len(vRows) - 1

            for vColumn, vText in enumerate((vSource["source"], str(vSource["count"]))):
                vItem = QTableWidgetItem(vText)
                set_bold(vItem, vTotal)
                self.table.setItem(vRow, vColumn, vItem)

            self.set_rate_item(vRow, 2, vSource["average"], pBold=True)

            for vColumn, vRate in enumerate(vSource["rates"], start=3):
                self.set_rate_item(vRow, vColumn, vRate, pBold=vTotal)

        # Toutes les lignes visibles : c'est la page qui défile, pas le tableau.
        self.table.resizeRowsToContents()
        self.table.setFixedHeight(
            self.table.horizontalHeader().sizeHint().height()
            + sum(self.table.rowHeight(vRow) for vRow in range(len(vRows)))
            + 2 * self.table.frameWidth()
        )

    def show_report(self, pReport):
        """Affiche les chiffres clés, le graphique global et le tableau par source."""
        self.show_statistics(pReport)

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

        self.show_table(pReport)

        vProblems = pReport["problems"]

        self.export_button.setText(
            f"Exporter les offres à vérifier ({vProblems['total']})"
            if vProblems["total"]
            else "Aucune offre à vérifier"
        )
        self.export_button.setEnabled(bool(vProblems["total"]))
        self.problems_label.setText(describe_problems(vProblems))

        show_message(
            self.message_label,
            f"{pReport['total']['count']} offre(s) analysée(s), "
            f"{pReport['rejected']} écartée(s) faute de titre et de description. ",
            None,
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

                show_message(
                    self.message_label,
                    "L'export n'a pas pu être enregistré.",
                    "danger",
                )

            else:
                show_message(
                    self.message_label,
                    f"Offres à vérifier exportées : {vFileName}",
                    "success",
                )
