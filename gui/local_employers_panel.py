"""Employeurs industriels de la région et candidatures spontanées, sur Mon marché"""

import threading
from datetime import datetime
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.employers_map import EmployersMap
from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.geocoding import load_home
from job.local_employers import (
    build_employers_view,
    fetch_local_employers,
    follow_employer,
    record_spontaneous,
)
from job.presentation import format_date
from job.spontaneous_applications import STATUSES
from utils.logger import get_logger

logger = get_logger(__name__)

COLUMNS = (
    "Employeur",
    "Secteur",
    "Effectif",
    "Site le plus proche",
    "Distance",
    "Offres en base",
    "Candidature",
)
RIGHT_ALIGNED = (4, 5)
SEARCH_URL = "https://duckduckgo.com/?q={query}"
MAX_ROWS = 300


def describe_contact(pEmployer):
    """Retourne la colonne Candidature : étape, date et relance due, ou le suivi."""

    vApplication = pEmployer.get("spontaneous")

    if vApplication is None:
        return "Suivi" if pEmployer["followed"] else ""

    rText = f"{vApplication['status_label']} · envoi du {format_date(vApplication['sent_on'])}"

    if vApplication["follow_up_due"]:
        rText += " · à relancer"

    return rText


class LocalEmployersPanel(QWidget):
    """Liste filtrable des employeurs ; suivre l'un d'eux alerte de ses nouvelles offres."""

    fetched = Signal(str, str)

    def __init__(self, pDatabaseFile):
        """Construit les filtres, le tableau et les actions."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.employers = []
        self.fetched.connect(self.end_fetch)

        vCard, vLayout = create_card(
            "Employeurs industriels de la région",
            "Entreprises de 250 salariés et plus, d'après l'annuaire public : suivez "
            "vos candidatures spontanées et soyez alerté de leurs nouvelles offres",
            "briefcase",
            "local-employers",
        )
        self.sector_combo = QComboBox()
        self.sector_combo.currentIndexChanged.connect(self.refresh)
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(0, 300)
        self.distance_spin.setSingleStep(10)
        self.distance_spin.setSuffix(" km")
        self.distance_spin.setSpecialValueText("Toute la région")
        self.distance_spin.valueChanged.connect(self.refresh)
        self.contact_combo = QComboBox()
        self.contact_combo.currentIndexChanged.connect(self.refresh)
        self.update_button = create_button("Mettre à jour la liste", "history")
        self.update_button.clicked.connect(self.start_fetch)
        vFilters = QHBoxLayout()
        vFilters.addWidget(self.sector_combo, 1)
        vFilters.addWidget(self.contact_combo, 1)
        vFilters.addWidget(self.distance_spin)
        vFilters.addWidget(self.update_button)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(320)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(lambda _pRow, _pColumn: self.open_page())

        vFollow = create_button(
            "Suivre l'employeur choisi",
            "bell-ring",
            "primaryButton",
            COLORS["on_primary"],
        )
        vFollow.clicked.connect(self.follow)
        vPage = create_button("Fiche publique", "file-text")
        vPage.clicked.connect(self.open_page)
        vCareer = create_button("Chercher sa page carrière", "search")
        vCareer.clicked.connect(self.search_career_page)
        vActions = QHBoxLayout()
        vActions.addWidget(vFollow)
        vActions.addWidget(vPage)
        vActions.addWidget(vCareer)
        vActions.addStretch(1)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Pas de candidature", "")

        for vStatus, vLabel in STATUSES.items():
            self.status_combo.addItem(vLabel, vStatus)

        vRecord = create_button("Enregistrer l'étape", "send")
        vRecord.clicked.connect(self.record_status)
        vTracking = QHBoxLayout()
        vTracking.addWidget(QLabel("Candidature spontanée :"))
        vTracking.addWidget(self.status_combo)
        vTracking.addWidget(vRecord)
        vTracking.addStretch(1)

        self.map = EmployersMap()
        self.map.employer_clicked.connect(self.select_employer)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.table, "Liste")
        self.tabs.addTab(self.map, "Carte")

        self.status_label = QLabel()
        self.status_label.setObjectName("cardSubtitle")
        self.status_label.setWordWrap(True)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        vLayout.addLayout(vFilters)
        vLayout.addWidget(self.status_label)
        vLayout.addWidget(self.tabs)
        vLayout.addLayout(vActions)
        vLayout.addLayout(vTracking)
        vLayout.addWidget(self.message_label)

        vOuter = QVBoxLayout(self)
        vOuter.setContentsMargins(0, 0, 0, 0)
        vOuter.addWidget(vCard)

    def refresh(self):
        """Relit la liste enregistrée et la filtre."""
        try:
            vView = build_employers_view(
                self.database_file,
                self.sector_combo.currentData() or "",
                self.distance_spin.value() or None,
                self.contact_combo.currentData() or "",
            )

        except Exception:
            logger.exception("Impossible de lire les employeurs de la région")
            return

        if not self.sector_combo.count():
            self.sector_combo.blockSignals(True)
            self.sector_combo.addItem("Tous les secteurs", "")

            for vSector in vView["sectors"]:
                self.sector_combo.addItem(vSector, vSector)

            self.sector_combo.blockSignals(False)

        if not self.contact_combo.count():
            self.contact_combo.blockSignals(True)

            for vContact, vLabel in vView["contacts"].items():
                self.contact_combo.addItem(vLabel, vContact)

            self.contact_combo.blockSignals(False)

        self.employers = vView["employers"][:MAX_ROWS]
        self.status_label.setText(
            f"{vView['region']} · {len(vView['employers'])} employeur(s) affiché(s) sur "
            f"{vView['count']} · liste du {format_date(vView['updated_at'])} · "
            f"{vView['sent_count']} candidature(s) spontanée(s), "
            f"{vView['due_count']} à relancer"
            if vView["updated_at"]
            else "Liste encore vide : mettez-la à jour depuis l'annuaire public "
            "(une vingtaine de secondes)."
        )
        self.table.setRowCount(len(self.employers))

        for vRow, vEmployer in enumerate(self.employers):
            for vColumn, vValue in enumerate(
                (
                    vEmployer["name"],
                    vEmployer["sector"],
                    vEmployer.get("headcount") or "",
                    vEmployer["city"],
                    (
                        ""
                        if vEmployer["distance_km"] is None
                        else f"{vEmployer['distance_km']} km"
                    ),
                    str(vEmployer["offers"]),
                    describe_contact(vEmployer),
                )
            ):
                vItem = QTableWidgetItem(vValue)

                if vColumn in RIGHT_ALIGNED:
                    vItem.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(vRow, vColumn, vItem)

        self.table.resizeColumnsToContents()
        self.map.set_employers(load_home(self.database_file), self.employers)

    def selected(self):
        """Retourne l'employeur choisi, ou None en l'indiquant."""
        vRow = self.table.currentRow()

        if not 0 <= vRow < len(self.employers):
            show_message(
                self.message_label, "Choisissez d'abord un employeur.", "warning"
            )
            return None

        return self.employers[vRow]

    def follow(self):
        """Ajoute l'employeur choisi aux entreprises privilégiées."""
        vEmployer = self.selected()

        if vEmployer is None:
            return

        follow_employer(self.database_file, vEmployer["siren"])
        show_message(
            self.message_label,
            f"{vEmployer['name']} est suivi : ses nouvelles offres seront signalées.",
            "success",
        )
        self.refresh()

    def select_employer(self, pSiren):
        """Choisit dans la liste l'employeur cliqué sur la carte."""
        for vRow, vEmployer in enumerate(self.employers):
            if vEmployer["siren"] == pSiren:
                self.table.selectRow(vRow)
                show_message(self.message_label, f"{vEmployer['name']} choisi.", None)

    def record_status(self):
        """Enregistre l'étape choisie de la candidature spontanée."""
        vEmployer = self.selected()

        if vEmployer is None:
            return

        try:
            record_spontaneous(
                self.database_file, vEmployer["siren"], self.status_combo.currentData()
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        show_message(
            self.message_label,
            f"{vEmployer['name']} : {self.status_combo.currentText().lower()}.",
            "success",
        )
        self.refresh()

    def open_page(self):
        """Ouvre la fiche publique de l'employeur choisi."""
        vEmployer = self.selected()

        if vEmployer is not None:
            QDesktopServices.openUrl(QUrl(vEmployer["page"]))

    def search_career_page(self):
        """Cherche la page carrière de l'employeur choisi sur le web."""
        vEmployer = self.selected()

        if vEmployer is not None:
            QDesktopServices.openUrl(
                QUrl(
                    SEARCH_URL.format(
                        query=quote_plus(f"{vEmployer['name']} recrutement carrière")
                    )
                )
            )

    def start_fetch(self):
        """Met la liste à jour en arrière-plan, sans figer la fenêtre."""
        self.update_button.setEnabled(False)
        show_message(self.message_label, "Interrogation de l'annuaire public…", None)

        def run():
            try:
                vCount = fetch_local_employers(self.database_file, datetime.now())
                self.fetched.emit(f"{vCount} employeur(s) trouvé(s).", "success")

            except ValueError as vError:
                self.fetched.emit(str(vError), "warning")

        threading.Thread(target=run, daemon=True).start()

    def end_fetch(self, pMessage, pTone):
        """Affiche le résultat de la mise à jour et la nouvelle liste."""
        self.update_button.setEnabled(True)
        show_message(self.message_label, pMessage, pTone)
        self.refresh()
