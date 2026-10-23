"""Carte des questions signalées comme douteuses, à relire puis remettre en jeu"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.quiz import describe_flagged_questions, unflag_questions
from utils.logger import get_logger

logger = get_logger(__name__)

FLAGGED_COLUMNS = ["Thème", "Question"]

# Texte affiché pour une question supprimée depuis son signalement
MISSING_QUESTION = "Question introuvable, retirée depuis"


class QuizFlaggedCard(QWidget):
    """Liste des questions signalées, depuis ce PC ou le téléphone."""

    questions_changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit le tableau et le bouton de remise en jeu."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.tree = QTreeWidget()
        self.tree.setColumnCount(len(FLAGGED_COLUMNS))
        self.tree.setHeaderLabels(FLAGGED_COLUMNS)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemSelectionChanged.connect(self.update_button)

        self.restore_button = create_button(
            "Remettre dans les tirages", "circle-check", pIconColor=COLORS["primary"]
        )
        self.restore_button.setToolTip(
            "Question finalement correcte : elle revient dans les révisions"
        )
        self.restore_button.clicked.connect(self.restore_selected)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.restore_button)
        vActions.addStretch()

        self.card, vCardLayout = create_card(
            "Questions signalées",
            "Retirées des tirages depuis ce PC ou le téléphone, à relire",
        )
        vCardLayout.addWidget(self.tree)
        vCardLayout.addLayout(vActions)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(self.card)

    def refresh(self):
        """Relit les questions signalées ; la carte est masquée s'il n'y en a pas."""
        try:
            vQuestions = describe_flagged_questions(self.database_file)

        except Exception:
            logger.exception("Impossible de lire les questions signalées")
            vQuestions = []

        self.tree.clear()

        for vQuestion in vQuestions:
            vItem = QTreeWidgetItem(
                [vQuestion["theme"], vQuestion["question"] or MISSING_QUESTION]
            )
            vItem.setData(0, Qt.ItemDataRole.UserRole, vQuestion["id"])
            vItem.setToolTip(1, vQuestion["question"])
            self.tree.addTopLevelItem(vItem)

        self.setVisible(bool(vQuestions))
        self.update_button()

    def update_button(self):
        """Active le bouton seulement avec une sélection."""
        self.restore_button.setEnabled(bool(self.tree.selectedItems()))

    def restore_selected(self):
        """Remet les questions sélectionnées dans les tirages."""
        vIds = {
            vItem.data(0, Qt.ItemDataRole.UserRole)
            for vItem in self.tree.selectedItems()
        }

        try:
            unflag_questions(self.database_file, vIds)

        except Exception:
            logger.exception("Impossible de remettre les questions dans les tirages")
            show_message(
                self.message_label, "Les questions n'ont pas pu être remises.", "danger"
            )
            return

        show_message(
            self.message_label, f"{len(vIds)} question(s) remise(s) dans les tirages."
        )
        self.questions_changed.emit()
