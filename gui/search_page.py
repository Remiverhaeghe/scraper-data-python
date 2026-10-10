"""Page de recherche : critères, sources, progression et arrêt"""

from PySide6.QtCore import QSettings, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.icons import get_icon
from gui.search_worker import SearchWorker
from gui.theme import COLORS
from gui.widgets import create_button, create_card, create_page_header
from job.contract import CONTRACT_TYPES
from job.sources.registry import SOURCES

# Nombre de pastilles de sources par ligne
SOURCE_COLUMNS = 6

DEFAULT_MAX_ITEMS = 100

# Icône et couleur du message d'état selon sa nature
STATUS_STYLES = {
    "idle": ("search", "muted"),
    "running": ("timer", "primary"),
    "success": ("circle-check", "success"),
    "warning": ("circle-alert", "warning"),
    "error": ("circle-alert", "danger"),
}


def get_unavailability_reason(pDefinition):
    """Retourne la raison pour laquelle une source ne peut pas être cochée."""

    rReason = None

    if not pDefinition.available:
        rReason = "indisponible"

    elif pDefinition.get_missing_settings():
        rReason = "non configurée"

    return rReason


def create_spin_box(pMinimum, pMaximum, pValue, pSuffix="", pEmptyText=None):
    """Crée un champ numérique ; pEmptyText remplace l'affichage du minimum."""

    rSpinBox = QSpinBox()
    rSpinBox.setRange(pMinimum, pMaximum)
    rSpinBox.setValue(pValue)
    rSpinBox.setSuffix(pSuffix)

    if pEmptyText is not None:
        rSpinBox.setSpecialValueText(pEmptyText)

    return rSpinBox


def create_field(pLabel, pWidget):
    """Place un libellé au-dessus de son champ."""

    vLabel = QLabel(pLabel)
    vLabel.setObjectName("fieldLabel")

    rLayout = QVBoxLayout()
    rLayout.setSpacing(6)
    rLayout.addWidget(vLabel)
    rLayout.addWidget(pWidget)

    return rLayout


class SearchPage(QWidget):
    """Permet de lancer une recherche d'offres et d'en suivre l'avancement."""

    search_started = Signal()
    search_ended = Signal()
    show_offers_requested = Signal()

    def __init__(self, pSettings=None):
        """Construit le formulaire et restaure les derniers critères saisis."""
        super().__init__()

        self.settings = pSettings if pSettings is not None else QSettings()
        self.search_thread = None
        self.search_worker = None
        self.source_buttons = {}

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(16)

        create_page_header(
            vLayout,
            "Recherche",
            "Interrogez les sources et enregistrez les nouvelles offres en base",
        )

        self.advanced_button = QPushButton("Afficher les options avancées")
        self.advanced_button.setObjectName("linkButton")
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(self.toggle_advanced_options)

        self.advanced_card = self.create_advanced_card()
        self.advanced_card.hide()

        vLayout.addWidget(self.create_criteria_card())
        vLayout.addWidget(self.create_sources_card())
        vLayout.addWidget(self.advanced_button, 0, Qt.AlignmentFlag.AlignLeft)
        vLayout.addWidget(self.advanced_card)
        vLayout.addWidget(self.create_actions_card())
        vLayout.addStretch()

        self.restore_settings()
        self.set_status("idle", "Prêt à lancer une recherche")

    def create_criteria_card(self):
        """Construit les critères de recherche et les filtres sur deux lignes."""
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("Ex. Développeur Java")

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Ex. Lille")

        self.max_items_spin = create_spin_box(1, 2000, DEFAULT_MAX_ITEMS, " offres")

        self.contract_combo = QComboBox()
        self.contract_combo.addItem("Tous les contrats", None)

        for vContract in CONTRACT_TYPES:
            self.contract_combo.addItem(vContract, vContract)

        self.min_salary_spin = create_spin_box(
            0, 20000, 0, " € net/mois", "Aucun minimum"
        )
        self.min_salary_spin.setSingleStep(100)

        self.remote_check = QCheckBox("Télétravail uniquement")

        vCard, vLayout = create_card("Critères")

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(16)
        vGrid.setVerticalSpacing(12)
        vGrid.addLayout(create_field("Mot-clé", self.keyword_edit), 0, 0)
        vGrid.addLayout(create_field("Localisation", self.location_edit), 0, 1)
        vGrid.addLayout(create_field("Nombre maximum", self.max_items_spin), 0, 2)
        vGrid.addLayout(create_field("Contrat", self.contract_combo), 1, 0)
        vGrid.addLayout(create_field("Salaire minimum", self.min_salary_spin), 1, 1)
        vGrid.addWidget(self.remote_check, 1, 2, Qt.AlignmentFlag.AlignBottom)
        vGrid.setColumnStretch(0, 2)
        vGrid.setColumnStretch(1, 2)
        vGrid.setColumnStretch(2, 1)

        vLayout.addLayout(vGrid)

        return vCard

    def create_sources_card(self):
        """Construit la sélection des sources sous forme de pastilles."""
        vCard, vLayout = create_card()

        vTitle = QLabel("Sources")
        vTitle.setObjectName("cardTitle")

        self.source_count_label = QLabel()
        self.source_count_label.setObjectName("cardSubtitle")

        vAllButton = QPushButton("Tout sélectionner")
        vAllButton.setObjectName("linkButton")
        vAllButton.clicked.connect(lambda: self.check_sources(True))

        vNoneButton = QPushButton("Tout désélectionner")
        vNoneButton.setObjectName("linkButton")
        vNoneButton.clicked.connect(lambda: self.check_sources(False))

        vHeader = QHBoxLayout()
        vHeader.setSpacing(12)
        vHeader.addWidget(vTitle)
        vHeader.addWidget(self.source_count_label)
        vHeader.addStretch()
        vHeader.addWidget(vAllButton)
        vHeader.addWidget(vNoneButton)

        vGrid = QGridLayout()
        vGrid.setSpacing(10)

        for vIndex, (vName, vDefinition) in enumerate(SOURCES.items()):
            vButton = self.create_source_button(vDefinition)

            self.source_buttons[vName] = vButton

            vGrid.addWidget(vButton, *divmod(vIndex, SOURCE_COLUMNS))

        vLayout.addLayout(vHeader)
        vLayout.addLayout(vGrid)

        return vCard

    def create_source_button(self, pDefinition):
        """Crée la pastille sélectionnable d'une source."""
        rButton = QPushButton(pDefinition.label)
        rButton.setObjectName("sourceChip")
        rButton.setCheckable(True)
        rButton.setCursor(Qt.CursorShape.PointingHandCursor)
        rButton.setIcon(
            get_icon(
                "circle-check", COLORS["border"], 16, pCheckedColor=COLORS["primary"]
            )
        )
        rButton.toggled.connect(self.update_source_count)

        vReason = get_unavailability_reason(pDefinition)

        if vReason is not None:
            rButton.setEnabled(False)
            rButton.setText(f"{pDefinition.label} · {vReason}")

            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            vMissing = pDefinition.get_missing_settings()

            rButton.setToolTip(
                "À renseigner dans .env : " + ", ".join(vMissing)
                if pDefinition.available and vMissing
                else "Source momentanément indisponible"
            )

        return rButton

    def create_advanced_card(self):
        """Construit les options techniques du scraping sur une ligne."""
        self.max_pages_spin = create_spin_box(0, 50, 0, " pages", "Par défaut")

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setSuffix(" s")

        self.timeout_spin = create_spin_box(5, 120, 30, " s")

        self.distance_spin = create_spin_box(0, 500, 0, " km", "Aucune limite")

        rCard, vLayout = create_card()

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(16)
        vGrid.addLayout(create_field("Pages par source", self.max_pages_spin), 0, 0)
        vGrid.addLayout(create_field("Délai entre requêtes", self.delay_spin), 0, 1)
        vGrid.addLayout(create_field("Délai d'attente", self.timeout_spin), 0, 2)
        vGrid.addLayout(create_field("Distance maximum", self.distance_spin), 0, 3)

        vLayout.addLayout(vGrid)

        return rCard

    def create_actions_card(self):
        """Construit les boutons, le message d'état et la progression."""
        self.start_button = create_button(
            "Lancer la recherche", "search", "primaryButton", COLORS["on_primary"]
        )
        self.start_button.clicked.connect(self.start_search)

        self.stop_button = create_button("Arrêter")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_search)

        self.status_icon = QLabel()

        self.status_label = QLabel()
        self.status_label.setObjectName("activityTitle")

        self.result_label = QLabel()
        self.result_label.setObjectName("cardSubtitle")

        vMessages = QVBoxLayout()
        vMessages.setSpacing(2)
        vMessages.addWidget(self.status_label)
        vMessages.addWidget(self.result_label)

        self.show_offers_button = create_button(
            "Voir les offres", "arrow-right", pIconColor=COLORS["primary"]
        )
        self.show_offers_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.show_offers_button.clicked.connect(self.show_offers_requested.emit)
        self.show_offers_button.hide()

        vRow = QHBoxLayout()
        vRow.setSpacing(12)
        vRow.addWidget(self.start_button)
        vRow.addWidget(self.stop_button)
        vRow.addSpacing(16)
        vRow.addWidget(self.status_icon)
        vRow.addLayout(vMessages, 1)
        vRow.addWidget(self.show_offers_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)

        self.warning_label = QLabel()
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()

        rCard, vLayout = create_card()
        vLayout.addLayout(vRow)
        vLayout.addWidget(self.progress_bar)
        vLayout.addWidget(self.warning_label)

        return rCard

    def set_status(self, pKind, pText, pDetail=""):
        """Affiche le message d'état avec l'icône et la couleur de sa nature."""
        vIcon, vColorName = STATUS_STYLES[pKind]

        self.status_icon.setPixmap(
            get_icon(vIcon, COLORS[vColorName], 24).pixmap(24, 24)
        )
        self.status_label.setText(pText)
        self.result_label.setText(pDetail)

    def toggle_advanced_options(self, pVisible):
        """Affiche ou masque les options avancées."""
        self.advanced_card.setVisible(pVisible)

        self.advanced_button.setText(
            "Masquer les options avancées"
            if pVisible
            else "Afficher les options avancées"
        )

    def check_sources(self, pChecked):
        """Sélectionne ou désélectionne toutes les sources disponibles."""
        for vButton in self.source_buttons.values():
            if vButton.isEnabled():
                vButton.setChecked(pChecked)

    def update_source_count(self):
        """Affiche le nombre de sources sélectionnées."""
        vSelectable = sum(
            1 for vButton in self.source_buttons.values() if vButton.isEnabled()
        )

        self.source_count_label.setText(
            f"{len(self.get_selected_sources())} sur {vSelectable} sélectionnée(s)"
        )

    def get_selected_sources(self):
        """Retourne les sources sélectionnées et disponibles."""
        rSources = [
            vName
            for vName, vButton in self.source_buttons.items()
            if vButton.isEnabled() and vButton.isChecked()
        ]

        return rSources

    def build_criteria(self):
        """Traduit le formulaire en critères pour le contrôleur ; 0 signifie aucun."""
        rCriteria = {
            "keyword": self.keyword_edit.text().strip() or None,
            "location": self.location_edit.text().strip() or None,
            "max_items": self.max_items_spin.value(),
            "contract": self.contract_combo.currentData(),
            "min_salary": self.min_salary_spin.value() or None,
            "remote": True if self.remote_check.isChecked() else None,
            "max_pages": self.max_pages_spin.value() or None,
            "delay": self.delay_spin.value(),
            "timeout": self.timeout_spin.value(),
            "max_distance_km": self.distance_spin.value() or None,
        }

        return rCriteria

    def is_running(self):
        """Indique si une recherche est en cours."""
        rRunning = self.search_thread is not None

        return rRunning

    def create_worker(self, pSources, pCriteria):
        """Crée le worker chargé d'exécuter la recherche."""
        rWorker = SearchWorker(pSources, pCriteria)

        return rWorker

    def start_search(self):
        """Lance la recherche dans un thread dédié."""
        vSources = self.get_selected_sources()

        if not vSources:
            self.set_status("warning", "Sélectionnez au moins une source.")

        elif not self.is_running():
            self.save_settings()

            self.show_offers_button.hide()
            self.warning_label.hide()
            self.progress_bar.setValue(0)
            self.set_status("running", "Démarrage de la recherche...")
            self.set_running(True)

            self.search_worker = self.create_worker(vSources, self.build_criteria())
            self.search_thread = QThread(self)

            self.search_worker.moveToThread(self.search_thread)

            self.search_thread.started.connect(self.search_worker.run)

            self.search_worker.progress.connect(self.show_progress)
            self.search_worker.succeeded.connect(self.show_result)
            self.search_worker.cancelled.connect(self.show_cancelled)
            self.search_worker.failed.connect(self.show_error)

            for vSignal in (
                self.search_worker.succeeded,
                self.search_worker.cancelled,
                self.search_worker.failed,
            ):
                vSignal.connect(self.search_thread.quit)

            self.search_thread.finished.connect(self.end_search)

            self.search_thread.start()
            self.search_started.emit()

    def stop_search(self):
        """Demande l'arrêt de la recherche avant la source suivante."""
        if self.is_running():
            self.search_worker.stop()

            self.stop_button.setEnabled(False)
            self.set_status("running", "Arrêt demandé, fin de la source en cours...")

    @Slot(int, int, str)
    def show_progress(self, pIndex, pTotal, pLabel):
        """Affiche la source en cours d'interrogation."""
        self.progress_bar.setValue(round((pIndex - 1) / pTotal * 100))
        self.set_status(
            "running", f"Interrogation de {pLabel}", f"Source {pIndex} sur {pTotal}"
        )

    @Slot(object)
    def show_result(self, pResult):
        """Affiche le bilan d'une recherche terminée."""
        vItems = pResult.items
        vNewCount = int(vItems["is_new"].sum()) if "is_new" in vItems else 0

        self.progress_bar.setValue(100)
        self.set_status(
            "warning" if pResult.error_message else "success",
            "Recherche terminée",
            f"{len(vItems)} offre(s) correspondent aux critères, "
            f"dont {vNewCount} nouvelle(s).",
        )
        self.show_offers_button.show()

        if pResult.error_message:
            self.show_warning(f"Sources en erreur : {pResult.error_message}")

    @Slot()
    def show_cancelled(self):
        """Indique que la recherche a été arrêtée sans enregistrement."""
        self.progress_bar.setValue(0)
        self.set_status("warning", "Recherche arrêtée, aucune offre enregistrée")

    @Slot(str)
    def show_error(self, pMessage):
        """Affiche l'échec de la recherche."""
        self.progress_bar.setValue(0)
        self.set_status("error", "La recherche a échoué")
        self.show_warning(pMessage)

    def show_warning(self, pMessage):
        """Affiche le détail d'une erreur sous la progression."""
        self.warning_label.setText(pMessage)
        self.warning_label.show()

    @Slot()
    def end_search(self):
        """Libère le thread et réactive le formulaire."""
        self.search_worker.deleteLater()
        self.search_thread.deleteLater()

        self.search_worker = None
        self.search_thread = None

        self.set_running(False)
        self.search_ended.emit()

    def set_running(self, pRunning):
        """Active ou désactive les commandes selon l'état de la recherche."""
        self.start_button.setEnabled(not pRunning)
        self.stop_button.setEnabled(pRunning)

    def save_settings(self):
        """Mémorise les derniers critères saisis pour la prochaine ouverture."""
        self.settings.setValue("search/keyword", self.keyword_edit.text())
        self.settings.setValue("search/location", self.location_edit.text())
        self.settings.setValue("search/sources", ",".join(self.get_selected_sources()))

    def restore_settings(self):
        """Restaure les derniers critères ; toutes les sources par défaut."""
        self.keyword_edit.setText(self.settings.value("search/keyword", "", str))
        self.location_edit.setText(self.settings.value("search/location", "", str))

        vSources = self.settings.value("search/sources", None)

        if vSources is None:
            self.check_sources(True)
        else:
            for vName in vSources.split(","):
                if vName in self.source_buttons:
                    self.source_buttons[vName].setChecked(True)

        self.update_source_count()
