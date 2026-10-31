"""Page Planning : la semaine jour par jour, tâches à glisser d'un jour à l'autre"""

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.weekly_planning import add_revision, build_week, delete_revision, move_item
from utils.logger import get_logger

logger = get_logger(__name__)

KIND_COLORS = {"interview": "danger", "follow-up": "warning", "revision": "primary"}


def get_kind_color(pKind):
    """Retourne la couleur d'une tâche selon sa nature."""

    rColor = QColor(COLORS[KIND_COLORS.get(pKind, "text")])

    return rColor


class DayList(QListWidget):
    """Tâches d'un jour ; une tâche lâchée ici change de jour."""

    moved = Signal(str, object)

    def __init__(self, pDay):
        """Accepte les tâches glissées depuis les autres jours."""
        super().__init__()

        self.day = pDay
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setWordWrap(True)
        self.setMinimumHeight(220)

    def dropEvent(self, pEvent):  # pylint: disable=invalid-name
        """Signale la tâche déplacée ; la page relit ensuite la semaine."""
        vSource = pEvent.source()

        if (
            isinstance(vSource, DayList)
            and vSource is not self
            and vSource.currentItem()
        ):
            self.moved.emit(
                vSource.currentItem().data(Qt.ItemDataRole.UserRole), self.day
            )

        # La copie de Qt est refusée : la semaine relue affiche le résultat.
        pEvent.ignore()


class PlanningPage(QWidget):
    """Semaine en cours ou choisie : entretiens, relances, révisions et quêtes."""

    navigation_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit l'en-tête, la grille des jours et l'ajout d'une révision."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.day = date.today()
        self.lists = []

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)
        create_page_header(
            vLayout,
            "Planning",
            "La semaine en un coup d'œil : glissez une tâche d'un jour à l'autre, "
            "l'abonnement d'agenda suit",
            pIcon="calendar",
        )

        vCard, vCardLayout = create_card(pOpen=True)
        vNavigation = QHBoxLayout()
        vPrevious = create_button("Semaine précédente")
        vPrevious.clicked.connect(lambda: self.change_week(-7))
        vToday = create_button("Cette semaine")
        vToday.clicked.connect(lambda: self.change_week(None))
        vNext = create_button("Semaine suivante")
        vNext.clicked.connect(lambda: self.change_week(7))
        self.week_label = QLabel()
        self.week_label.setObjectName("cardTitle")
        vNavigation.addWidget(self.week_label, 1)
        vNavigation.addWidget(vPrevious)
        vNavigation.addWidget(vToday)
        vNavigation.addWidget(vNext)
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        vCardLayout.addLayout(vNavigation)
        vCardLayout.addLayout(self.grid)

        vAddCard, vAddLayout = create_card(
            "Prévoir une révision",
            "Elle apparaît dans le planning et dans l'agenda",
            "graduation-cap",
            "planning_add",
            pOpen=True,
        )
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText(
            "Thème à réviser, par exemple Schémas électriques"
        )
        self.label_edit.returnPressed.connect(self.add)
        vAddButton = create_button(
            "Ajouter", "circle-check", "primaryButton", COLORS["on_primary"]
        )
        vAddButton.clicked.connect(self.add)
        self.remove_button = create_button("Retirer la révision choisie", "trash-2")
        self.remove_button.clicked.connect(self.remove_selected)
        vAddRow = QHBoxLayout()
        vAddRow.addWidget(self.date_edit)
        vAddRow.addWidget(self.label_edit, 1)
        vAddRow.addWidget(vAddButton)
        vAddRow.addWidget(self.remove_button)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        vAddLayout.addLayout(vAddRow)
        vAddLayout.addWidget(self.message_label)

        vQuestCard, vQuestLayout = create_card(
            "Quêtes de la semaine", None, "award", "planning_quests", pOpen=True
        )
        self.quests_layout = QVBoxLayout()
        vQuestLayout.addLayout(self.quests_layout)

        vLayout.addWidget(vCard)
        vLayout.addWidget(vAddCard)
        vLayout.addWidget(vQuestCard)
        vLayout.addStretch(1)

    def change_week(self, pDays):
        """Passe à une autre semaine, ou revient à la semaine en cours."""
        self.day = date.today() if pDays is None else self.day + timedelta(days=pDays)
        self.refresh()

    def refresh(self):
        """Relit la semaine et reconstruit les colonnes des jours."""
        try:
            vWeek = build_week(self.database_file, self.day)

        except Exception:
            logger.exception("Impossible de construire le planning")
            return

        vSunday = vWeek["monday"] + timedelta(days=6)
        self.week_label.setText(
            f"Semaine du {vWeek['monday']:%d/%m} au {vSunday:%d/%m/%Y}"
        )
        clear_layout(self.grid)
        self.lists = []

        for vColumn, vDay in enumerate(vWeek["days"]):
            vTitle = QLabel(f"{vDay['name'].capitalize()} {vDay['date']:%d/%m}")
            vTitle.setObjectName("cardTitle" if vDay["today"] else "cardSubtitle")
            vList = DayList(vDay["date"])
            vList.moved.connect(self.move)
            vList.itemDoubleClicked.connect(
                lambda pItem: self.navigation_requested.emit(
                    pItem.data(Qt.ItemDataRole.UserRole + 1)
                )
            )

            for vTask in vDay["items"]:
                vItem = QListWidgetItem(f"{vTask['time']} {vTask['label']}".strip())
                vItem.setData(Qt.ItemDataRole.UserRole, vTask["id"])
                vItem.setData(Qt.ItemDataRole.UserRole + 1, vTask["page"])
                vItem.setForeground(get_kind_color(vTask["kind"]))
                vList.addItem(vItem)

            self.grid.addWidget(vTitle, 0, vColumn)
            self.grid.addWidget(vList, 1, vColumn)
            self.lists.append(vList)

        clear_layout(self.quests_layout)

        for vQuest in vWeek["quests"]:
            vLabel = QLabel(
                f"{'✓' if vQuest['done'] else '○'} {vQuest['label']} · "
                f"{vQuest['progress']} / {vQuest['target']}"
            )
            self.quests_layout.addWidget(vLabel)

    def move(self, pItemId, pDay):
        """Déplace une tâche au jour où elle a été lâchée."""
        try:
            move_item(self.database_file, pItemId, pDay)

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")

        self.refresh()

    def add(self):
        """Prévoit une séance de révision au jour choisi."""
        try:
            add_revision(
                self.database_file,
                self.date_edit.date().toPython(),
                self.label_edit.text(),
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.label_edit.clear()
        show_message(self.message_label, "Révision ajoutée au planning.", "success")
        self.day = self.date_edit.date().toPython()
        self.refresh()

    def remove_selected(self):
        """Retire la révision choisie dans le planning."""
        vItem = next(
            (
                vList.currentItem()
                for vList in self.lists
                if vList.currentItem() and vList.hasFocus()
            ),
            None,
        ) or next(
            (vList.currentItem() for vList in self.lists if vList.currentItem()), None
        )
        vId = vItem.data(Qt.ItemDataRole.UserRole) if vItem else ""

        if not vId.startswith("revision|"):
            show_message(
                self.message_label,
                "Choisissez d'abord une révision dans le planning.",
                "warning",
            )
            return

        delete_revision(self.database_file, vId.split("|", 1)[1])
        show_message(self.message_label, "Révision retirée.", "success")
        self.refresh()
