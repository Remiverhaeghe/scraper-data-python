"""Statistiques de la révision : chiffres clés, progression par catégorie et activité"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.icons import get_icon
from gui.theme import COLORS
from gui.widgets import StatisticCard, create_card
from job.presentation import CHART_PALETTE
from job.quiz_domains import build_category_progress

# Colonnes du tableau de progression par catégorie
PROGRESS_COLUMNS = ["Catégorie", "Thèmes", "Acquises", "Progression", "À revoir"]
PROGRESS_BAR_WIDTH = 140
PROGRESS_BAR_HEIGHT = 14


def describe_unbalanced(pUnbalanced):
    """Résume les questions à revoir : trop dures puis trop faciles, avec leur taux."""

    vLines = []

    for vKind, vLabel in (("hard", "Trop dures"), ("easy", "Trop faciles")):
        if pUnbalanced.get(vKind):
            vLines.append(
                f"{vLabel}, à reformuler ou signaler : "
                + " ; ".join(
                    f"{vRow['question'][:60]} ({vRow['theme']}, {vRow['rate']} % "
                    f"sur {vRow['answers']})"
                    for vRow in pUnbalanced[vKind]
                )
            )

    rText = "\n".join(vLines)

    return rText


class QuizStatisticsCard(QWidget):
    """Carte « Mes statistiques », remplie par show_progress."""

    def __init__(self):
        """Construit les chiffres, le tableau par catégorie et le graphique."""
        super().__init__()

        self.statistic_cards = {
            "acquired": StatisticCard("Questions acquises", "circle-check", "green"),
            "answers": StatisticCard("Réponses données", "graduation-cap", "blue"),
            "rate": StatisticCard("Bonnes réponses", "sparkles", "purple"),
            "streak": StatisticCard("Jours de révision d'affilée", "calendar", "amber"),
        }

        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.statistic_cards.values():
            vCards.addWidget(vCard, 1)

        self.statistics_chart = BarChart()

        # Progression par catégorie : domaines puis sous-domaines, sans le détail
        # des thèmes pour rester lisible.
        self.progress_tree = QTreeWidget()
        self.progress_tree.setObjectName("progressTree")
        self.progress_tree.setColumnCount(len(PROGRESS_COLUMNS))
        self.progress_tree.setHeaderLabels(PROGRESS_COLUMNS)
        self.progress_tree.setIconSize(QSize(16, 16))
        self.progress_tree.setUniformRowHeights(True)
        self.progress_tree.setRootIsDecorated(True)
        self.progress_tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.progress_tree.header().setStretchLastSection(False)
        self.progress_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

        for vColumn in range(1, len(PROGRESS_COLUMNS)):
            self.progress_tree.header().setSectionResizeMode(
                vColumn, QHeaderView.ResizeMode.ResizeToContents
            )

        vProgressTitle = QLabel("Progression par catégorie")
        vProgressTitle.setObjectName("fieldLabel")

        # Questions réussies presque toujours ou presque jamais : à revoir.
        self.unbalanced_label = QLabel()
        self.unbalanced_label.setObjectName("cardSubtitle")
        self.unbalanced_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Mes statistiques", "Progression globale et réponses des 14 derniers jours"
        )
        vCardLayout.addLayout(vCards)
        vCardLayout.addWidget(vProgressTitle)
        vCardLayout.addWidget(self.progress_tree)
        vCardLayout.addWidget(self.unbalanced_label)
        vCardLayout.addWidget(self.statistics_chart)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def show_progress(self, pThemes, pStatistics, pUnbalanced=None):
        """Affiche les chiffres, la progression par catégorie et l'activité récente.

        pUnbalanced liste les questions trop dures et trop faciles à revoir.
        """
        self.show_statistics(pStatistics)
        self.show_category_progress(pThemes)
        self.unbalanced_label.setText(describe_unbalanced(pUnbalanced or {}))
        self.unbalanced_label.setVisible(bool(self.unbalanced_label.text()))

    def show_category_progress(self, pThemes):
        """Remplit le tableau de progression par domaine et sous-domaine."""
        self.progress_tree.clear()

        vDomainItem = None

        for vRow in build_category_progress(pThemes):
            vItem = QTreeWidgetItem(
                [
                    vRow["label"],
                    str(vRow["themes"]),
                    f"{vRow['correct']} / {vRow['total']}",
                    "",
                    str(vRow["due"]) if vRow["due"] else "",
                ]
            )
            vItem.setIcon(
                0,
                get_icon(
                    vRow["icon"],
                    COLORS["primary"] if vRow["level"] == 0 else COLORS["muted"],
                    16,
                ),
            )
            vItem.setForeground(4, QColor(COLORS["warning"]))

            if vRow["level"] == 0:
                vFont = vItem.font(0)
                vFont.setBold(True)
                vItem.setFont(0, vFont)
                self.progress_tree.addTopLevelItem(vItem)
                vDomainItem = vItem
            else:
                vDomainItem.addChild(vItem)

            vBar = QProgressBar()
            vBar.setValue(vRow["score"])
            vBar.setFormat(f"{vRow['score']} %")
            vBar.setFixedSize(PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT)
            self.progress_tree.setItemWidget(vItem, 3, vBar)

        self.progress_tree.expandAll()

        # Toutes les lignes visibles : la page défile, pas le tableau.
        vRows = sum(
            1 + self.progress_tree.topLevelItem(vIndex).childCount()
            for vIndex in range(self.progress_tree.topLevelItemCount())
        )
        self.progress_tree.setFixedHeight(
            self.progress_tree.header().sizeHint().height()
            + vRows * self.progress_tree.sizeHintForRow(0)
            + 8
        )

    def show_statistics(self, pStatistics):
        """Affiche les chiffres de la révision et le graphique des derniers jours."""
        vCards = self.statistic_cards

        vCards["acquired"].set_value(
            f"{pStatistics['acquired']} / {pStatistics['total']}"
        )
        vCards["answers"].set_value(str(pStatistics["answers"]))
        vCards["rate"].set_value(
            "-" if pStatistics["rate"] is None else f"{pStatistics['rate']} %"
        )
        vCards["streak"].set_value(str(pStatistics["streak"]))

        self.statistics_chart.set_series(
            [f"{vDay:%d/%m}" for vDay, _, _ in pStatistics["days"]],
            [
                (
                    "Réponses",
                    CHART_PALETTE[0],
                    [vCount for _, vCount, _ in pStatistics["days"]],
                ),
                (
                    "Bonnes réponses",
                    CHART_PALETTE[1],
                    [vCorrect for _, _, vCorrect in pStatistics["days"]],
                ),
            ],
            pAxes=("Jour", "Réponses par jour"),
            pEmptyText="Aucune réponse ces 14 derniers jours",
        )
