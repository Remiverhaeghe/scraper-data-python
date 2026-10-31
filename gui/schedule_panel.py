"""Carte de la recherche planifiée : recherche lancée, fréquence et état"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    FlowLayout,
    clear_layout,
    create_button,
    create_card,
    create_icon_label,
    show_message,
)
from job.schedule import (
    SCHEDULE_INTERVALS,
    clear_scheduled_search,
    describe_extra_searches,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    load_schedule,
    save_extra_searches,
    save_schedule_options,
    save_scheduled_search,
)
from storage.saved_searches import get_saved_searches
from utils.logger import get_logger

logger = get_logger(__name__)


class SchedulePanel(QWidget):
    """Activation, fréquence et recherches de la recherche planifiée."""

    def __init__(self, pDatabaseFile):
        """Construit la recherche planifiée, son remplacement et ses options."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.saved_searches = {}

        vCard, vCardLayout = create_card(
            "Recherche planifiée",
            "Lancée par le planificateur (python -m scheduler), parmi les "
            "recherches enregistrées de la page Recherche.",
        )

        self.search_label = QLabel()
        self.search_label.setObjectName("activityTitle")
        self.search_label.setWordWrap(True)

        self.sources_label = QLabel()
        self.sources_label.setObjectName("cardSubtitle")
        self.sources_label.setWordWrap(True)

        self.extra_label = QLabel()
        self.extra_label.setObjectName("cardSubtitle")
        self.extra_label.setWordWrap(True)

        vSearchTexts = QVBoxLayout()
        vSearchTexts.setSpacing(2)
        vSearchTexts.addWidget(self.search_label)
        vSearchTexts.addWidget(self.sources_label)
        vSearchTexts.addWidget(self.extra_label)

        vSearch = QHBoxLayout()
        vSearch.setSpacing(10)
        vSearch.addWidget(
            create_icon_label("search", COLORS["primary"], 18),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        vSearch.addLayout(vSearchTexts, 1)

        self.remove_button = create_button(
            "", "trash-2", "iconButton", COLORS["danger"]
        )
        self.remove_button.setToolTip(
            "Retirer la recherche planifiée et désactiver la planification"
        )
        self.remove_button.clicked.connect(self.remove_scheduled_search)
        vSearch.addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignTop)

        # Recopie les critères et les sources : modifier ensuite la recherche
        # enregistrée ne change pas la recherche planifiée.
        self.search_combo = QComboBox()
        self.search_combo.setToolTip(
            "Remplace la recherche planifiée à l'enregistrement"
        )

        self.extra_searches_title = QLabel("Lancer aussi ces recherches enregistrées")
        self.extra_searches_title.setObjectName("cardSubtitle")

        self.extra_searches_layout = FlowLayout(12)
        self.extra_search_checks = {}

        self.enabled_check = QCheckBox("Activer la recherche planifiée")

        self.interval_combo = QComboBox()

        for vHours in SCHEDULE_INTERVALS:
            self.interval_combo.addItem(format_interval(vHours), vHours)

        vOptions = QHBoxLayout()
        vOptions.setSpacing(12)
        vOptions.addWidget(self.enabled_check)
        vOptions.addStretch()
        vOptions.addWidget(self.interval_combo)

        self.runs_label = QLabel()
        self.runs_label.setObjectName("cardSubtitle")
        self.runs_label.setWordWrap(True)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.message_label, 1)

        vCardLayout.addLayout(vSearch)
        vCardLayout.addWidget(self.search_combo)
        vCardLayout.addWidget(self.extra_searches_title)
        vCardLayout.addLayout(self.extra_searches_layout)
        vCardLayout.addLayout(vOptions)
        vCardLayout.addWidget(self.runs_label)
        vCardLayout.addLayout(vActions)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh_saved_searches(self):
        """Propose les recherches enregistrées pour remplacer la recherche planifiée."""
        try:
            self.saved_searches = {
                vSearch["name"]: vSearch
                for vSearch in get_saved_searches(self.database_file)
            }

        except Exception:
            logger.exception("Impossible de lire les recherches enregistrées")

            self.saved_searches = {}

        self.search_combo.clear()
        self.search_combo.addItem(
            (
                "Garder la recherche actuelle"
                if self.saved_searches
                else "Aucune recherche enregistrée dans la page Recherche"
            ),
            None,
        )

        for vName in self.saved_searches:
            self.search_combo.addItem(f"Planifier « {vName} »", vName)

        clear_layout(self.extra_searches_layout)

        self.extra_search_checks = {
            vName: QCheckBox(vName) for vName in self.saved_searches
        }

        for vCheck in self.extra_search_checks.values():
            self.extra_searches_layout.addWidget(vCheck)

        self.extra_searches_title.setVisible(bool(self.saved_searches))

    def refresh(self):
        """Relit la planification en base."""
        self.refresh_saved_searches()

        try:
            vSchedule = load_schedule(self.database_file)

        except Exception:
            logger.exception("Impossible de charger la planification")

            self.runs_label.setText("La planification n'a pas pu être lue.")

        else:
            vSearch, vSources = describe_scheduled_search(vSchedule)

            self.search_label.setText(vSearch)
            self.sources_label.setText(vSources)
            self.sources_label.setVisible(bool(vSources))

            vExtra = describe_extra_searches(vSchedule)

            self.extra_label.setText(vExtra)
            self.extra_label.setVisible(bool(vExtra))

            for vName, vCheck in self.extra_search_checks.items():
                vCheck.setChecked(vName in vSchedule["extra_searches"])
            self.enabled_check.setChecked(vSchedule["enabled"])
            self.remove_button.setVisible(vSchedule["search"] is not None)
            self.interval_combo.setCurrentIndex(
                self.interval_combo.findData(vSchedule["interval_hours"])
            )
            self.runs_label.setText(describe_schedule_runs(vSchedule, datetime.now()))

    def save(self):
        """Enregistre l'activation et la fréquence de la recherche planifiée."""
        vName = self.search_combo.currentData()

        try:
            if vName is not None:
                vSearch = self.saved_searches[vName]

                save_scheduled_search(
                    self.database_file, vSearch["sources"], vSearch["criteria"]
                )

            vErrors = save_schedule_options(
                self.database_file,
                self.enabled_check.isChecked(),
                self.interval_combo.currentData(),
            )

            if not vErrors:
                save_extra_searches(
                    self.database_file,
                    [
                        vName
                        for vName, vCheck in self.extra_search_checks.items()
                        if vCheck.isChecked()
                    ],
                )

        except Exception:
            logger.exception("Échec de l'enregistrement de la planification")

            show_message(
                self.message_label,
                "La planification n'a pas pu être enregistrée.",
                "danger",
            )
            return

        if not vErrors:
            self.refresh()

        show_message(
            self.message_label,
            " ".join(vErrors) or "Planification enregistrée.",
            "warning" if vErrors else "success",
        )

    def remove_scheduled_search(self):
        """Retire la recherche planifiée, après confirmation."""
        if (
            QMessageBox.question(
                self,
                "Retirer la recherche planifiée",
                "La recherche planifiée sera retirée et la planification "
                "désactivée. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            clear_scheduled_search(self.database_file)

        except Exception:
            logger.exception("Échec du retrait de la recherche planifiée")

            show_message(
                self.message_label, "La recherche n'a pas pu être retirée.", "danger"
            )

        else:
            self.refresh()
            show_message(self.message_label, "Recherche planifiée retirée.")
