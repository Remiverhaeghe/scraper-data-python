"""Page des compétences : demande des offres croisée avec la préparation"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.icons import get_icon
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.profile import add_profile_skill
from job.quiz import load_active_quiz
from job.skills_dashboard import SKILL_STATUSES, build_skills_dashboard
from utils.logger import get_logger

logger = get_logger(__name__)

# Compétences reprises dans le graphique : au-delà, les libellés se chevauchent
CHART_SKILLS = 10
CHART_HEIGHT = 260
HISTORY_CHART_HEIGHT = 220

# Marge verticale d'une cellule (QTableView::item dans theme.qss : 6 px en haut
# et en bas, plus la bordure) : elle s'applique aussi au bouton placé dedans.
CELL_PADDING = 16

COLUMNS = (
    "Compétence",
    "Offres",
    "Profil",
    "Thèmes de révision",
    "Maîtrise",
    "État",
    "",
)


class SkillsPage(QWidget):
    """Montre les compétences les plus demandées et la préparation de chacune."""

    revise_requested = Signal(str)
    generation_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les chiffres clés, le graphique et le tableau ; données par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.statistic_cards = {
            "covered": StatisticCard(
                "Compétences avec des questions", "list-checks", "blue"
            ),
            "readiness": StatisticCard(
                "Préparation pondérée", "graduation-cap", "green"
            ),
            "in_profile": StatisticCard("Dans votre profil", "user", "purple"),
            "priority": StatisticCard("À travailler en premier", "target", "amber"),
        }
        self.statistic_cards["readiness"].setToolTip(
            "Score de révision moyen, chaque compétence pesant selon le nombre "
            "d'offres qui la demandent"
        )

        vStatistics = QHBoxLayout()
        vStatistics.setSpacing(12)

        for vCard in self.statistic_cards.values():
            vStatistics.addWidget(vCard)

        self.chart = BarChart()
        self.chart.setMinimumHeight(CHART_HEIGHT)

        self.history_chart = BarChart()
        self.history_chart.setMinimumHeight(HISTORY_CHART_HEIGHT)

        vHistoryCard, vHistoryLayout = create_card(
            "Évolution de la préparation",
            "Préparation pondérée par la demande à la fin de chaque semaine, "
            "d'après vos réponses de révision",
        )
        vHistoryLayout.addWidget(self.history_chart)

        vChartCard, vChartLayout = create_card(
            "Demande des offres",
            "Les compétences les plus citées, colorées selon votre préparation",
        )
        vChartLayout.addWidget(self.chart)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.setWordWrap(True)

        vHeader = self.table.horizontalHeader()
        vHeader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        vTableCard, vTableLayout = create_card(
            "Compétences les plus demandées",
            "Réviser un thème existant, ou préparer avec ChatGPT les questions "
            "d'une compétence qui n'en a pas encore",
        )
        vTableLayout.addWidget(self.table)

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.setWordWrap(True)

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Compétences",
            "Ce que demandent vos offres, et où en est votre préparation",
            pIcon="target",
        )

        vLayout.addLayout(vStatistics)
        vLayout.addWidget(vHistoryCard)
        vLayout.addWidget(vChartCard)
        vLayout.addWidget(vTableCard)
        vLayout.addWidget(self.message_label)
        vLayout.addStretch(1)

    def refresh(self):
        """Relit les offres, le profil et la révision."""
        try:
            vDashboard = build_skills_dashboard(
                self.database_file, load_active_quiz(self.database_file)
            )

        except Exception:
            logger.exception("Impossible de calculer le tableau des compétences")

            show_message(
                self.message_label,
                "Le tableau des compétences n'a pas pu être calculé.",
                "danger",
            )

        else:
            self.show_dashboard(vDashboard)

    def show_dashboard(self, pDashboard):
        """Affiche les chiffres clés, le graphique et le tableau."""
        vSummary = pDashboard["summary"]
        vRows = pDashboard["rows"]

        self.statistic_cards["covered"].set_value(
            f"{vSummary['covered']} / {vSummary['skills']}"
        )
        self.statistic_cards["readiness"].set_value(f"{vSummary['readiness']} %")
        self.statistic_cards["in_profile"].set_value(
            f"{vSummary['in_profile']} / {vSummary['skills']}"
        )
        self.statistic_cards["priority"].set_value(vSummary["priority"] or "-")

        self.history_chart.set_series(
            [vPoint["label"] for vPoint in pDashboard["history"]],
            [
                (
                    "Préparation",
                    COLORS["primary"],
                    [vPoint["readiness"] for vPoint in pDashboard["history"]],
                )
            ],
            pAxes=("Semaine", "% de préparation"),
            pEmptyText="Aucune réponse de révision pour le moment",
            pFillWidth=True,
        )

        vChartRows = vRows[:CHART_SKILLS]
        self.chart.set_series(
            [vRow["skill"] for vRow in vChartRows],
            [
                (
                    "Offres",
                    [COLORS[SKILL_STATUSES[vRow["status"]][2]] for vRow in vChartRows],
                    [vRow["offers"] for vRow in vChartRows],
                )
            ],
            pAxes=("Compétence", "Offres qui la demandent"),
            pEmptyText="Aucune compétence repérée dans vos offres pour le moment",
            pFillWidth=True,
        )

        self.show_table(vRows)

        show_message(
            self.message_label,
            f"{pDashboard['offer_count']} offre(s) analysée(s). Couleurs : vert "
            "maîtrisé, bleu en cours, orange à réviser, rouge sans question.",
            None,
        )

    def show_table(self, pRows):
        """Remplit le tableau, avec l'action utile sur chaque compétence."""
        self.table.setRowCount(len(pRows))

        for vRow, vSkill in enumerate(pRows):
            vLabel, vIcon, vTone = SKILL_STATUSES[vSkill["status"]]
            vTexts = (
                vSkill["skill"],
                f"{vSkill['offers']} ({vSkill['share']} %)",
                "Oui" if vSkill["in_profile"] else "Non",
                ", ".join(vLabel for _, vLabel in vSkill["themes"]) or "Aucun thème",
                f"{vSkill['score']} %" if vSkill["themes"] else "-",
            )

            for vColumn, vText in enumerate(vTexts):
                self.table.setItem(vRow, vColumn, QTableWidgetItem(vText))

            self.table.item(vRow, 0).setIcon(
                get_icon(vSkill["icon"], COLORS["primary"], 16)
            )

            vStatus = QTableWidgetItem(get_icon(vIcon, COLORS[vTone], 16), vLabel)
            vStatus.setForeground(QColor(COLORS[vTone]))
            self.table.setItem(vRow, 5, vStatus)
            self.table.setCellWidget(vRow, 6, self.create_action(vSkill))

        # Toutes les lignes visibles : c'est la page qui défile, pas le tableau.
        self.table.resizeRowsToContents()

        # La hauteur calculée ne tient compte que du texte : le bouton serait rogné.
        # Il est mesuré une fois sa feuille de style appliquée, marges comprises.
        for vRow in range(len(pRows)):
            vCell = self.table.cellWidget(vRow, 6)
            vCell.ensurePolished()

            for vChild in vCell.findChildren(QWidget):
                vChild.ensurePolished()

            self.table.setRowHeight(
                vRow,
                max(
                    self.table.rowHeight(vRow),
                    vCell.sizeHint().height() + CELL_PADDING,
                ),
            )

        self.table.setFixedHeight(
            self.table.horizontalHeader().sizeHint().height()
            + sum(self.table.rowHeight(vRow) for vRow in range(len(pRows)))
            + 2 * self.table.frameWidth()
        )

    def add_to_profile(self, pSkill):
        """Ajoute une compétence au profil puis rafraîchit le tableau."""
        try:
            add_profile_skill(self.database_file, pSkill)

        except Exception:
            logger.exception("Impossible d'ajouter la compétence au profil")

            show_message(
                self.message_label,
                "La compétence n'a pas pu être ajoutée au profil.",
                "danger",
            )

        else:
            self.refresh()

    def create_action(self, pSkill):
        """Crée le bouton d'une compétence : réviser son thème ou préparer des questions."""
        if pSkill["themes"]:
            vButton = create_button(
                "Réviser", "graduation-cap", pIconColor=COLORS["primary"]
            )
            vButton.setToolTip(f"Ouvre le thème {pSkill['themes'][0][1]}")
            vButton.clicked.connect(
                lambda: self.revise_requested.emit(pSkill["themes"][0][0])
            )
        else:
            vButton = create_button("Préparer", "bot", pIconColor=COLORS["primary"])
            vButton.setToolTip(
                "Aucune question pour cette compétence : copie la demande ChatGPT "
                f"pour le thème {pSkill['catalog_label']}"
            )
            vButton.clicked.connect(
                lambda: self.generation_requested.emit(pSkill["catalog_label"])
            )

        # Boutons centrés dans leur cellule : ils gardent leur hauteur.
        rCell = QWidget()
        vLayout = QHBoxLayout(rCell)
        vLayout.setContentsMargins(4, 2, 4, 2)
        vLayout.setSpacing(6)
        vLayout.addWidget(vButton, 0, Qt.AlignmentFlag.AlignVCenter)

        if not pSkill["in_profile"]:
            vProfileButton = create_button("", "user", pIconColor=COLORS["primary"])
            vProfileButton.setObjectName("profileSkillButton")
            vProfileButton.setToolTip(f"Ajouter {pSkill['skill']} à mon profil")
            vProfileButton.clicked.connect(lambda: self.add_to_profile(pSkill["skill"]))
            vLayout.addWidget(vProfileButton, 0, Qt.AlignmentFlag.AlignVCenter)

        return rCell
