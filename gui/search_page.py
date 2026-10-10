"""Page de recherche : critères, sources, progression et arrêt"""

from PySide6.QtCore import QSettings, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.search_worker import SearchWorker
from gui.theme import COLORS
from gui.widgets import create_button, create_page_header
from job.contract import CONTRACT_TYPES
from job.sources.registry import SOURCES

# Nombre de sources affichées par ligne
SOURCE_COLUMNS = 4

DEFAULT_MAX_ITEMS = 100


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
        self.source_checkboxes = {}

        vContent = QWidget()

        vLayout = QVBoxLayout(vContent)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Recherche",
            "Interrogez les sources et enregistrez les offres en base",
        )

        vLayout.addWidget(self.create_criteria_group())
        vLayout.addWidget(self.create_sources_group())

        self.advanced_button = QPushButton("Afficher les options avancées")
        self.advanced_button.setObjectName("linkButton")
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(self.toggle_advanced_options)

        self.advanced_group = self.create_advanced_group()
        self.advanced_group.hide()

        vLayout.addWidget(self.advanced_button)
        vLayout.addWidget(self.advanced_group)
        vLayout.addLayout(self.create_actions())
        vLayout.addLayout(self.create_progress())
        vLayout.addStretch()

        vScrollArea = QScrollArea()
        vScrollArea.setWidgetResizable(True)
        vScrollArea.setWidget(vContent)

        vPageLayout = QVBoxLayout(self)
        vPageLayout.setContentsMargins(0, 0, 0, 0)
        vPageLayout.addWidget(vScrollArea)

        self.restore_settings()

    def create_criteria_group(self):
        """Construit les critères de recherche et les filtres."""
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("Ex. Développeur Java")

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Ex. Lille")

        self.max_items_spin = create_spin_box(1, 2000, DEFAULT_MAX_ITEMS)

        self.contract_combo = QComboBox()
        self.contract_combo.addItem("Tous les contrats", None)

        for vContract in CONTRACT_TYPES:
            self.contract_combo.addItem(vContract, vContract)

        self.min_salary_spin = create_spin_box(
            0, 20000, 0, " € net/mois", "Aucun minimum"
        )
        self.min_salary_spin.setSingleStep(100)

        self.remote_check = QCheckBox("Télétravail uniquement")

        rGroup = QGroupBox("Critères")

        vForm = QFormLayout(rGroup)
        vForm.addRow("Mot-clé", self.keyword_edit)
        vForm.addRow("Localisation", self.location_edit)
        vForm.addRow("Nombre maximum d'offres", self.max_items_spin)
        vForm.addRow("Contrat", self.contract_combo)
        vForm.addRow("Salaire minimum", self.min_salary_spin)
        vForm.addRow("", self.remote_check)

        return rGroup

    def create_sources_group(self):
        """Construit la sélection des sources."""
        rGroup = QGroupBox("Sources")

        vGrid = QGridLayout()

        for vIndex, (vName, vDefinition) in enumerate(SOURCES.items()):
            vCheckBox = QCheckBox(vDefinition.label)
            vReason = get_unavailability_reason(vDefinition)

            if vReason is not None:
                vCheckBox.setEnabled(False)
                vCheckBox.setText(f"{vDefinition.label} ({vReason})")

                # Seuls les noms des variables sont affichés, jamais leurs valeurs.
                vMissing = vDefinition.get_missing_settings()

                if vDefinition.available and vMissing:
                    vCheckBox.setToolTip(
                        "À renseigner dans .env : " + ", ".join(vMissing)
                    )

            self.source_checkboxes[vName] = vCheckBox

            vGrid.addWidget(vCheckBox, *divmod(vIndex, SOURCE_COLUMNS))

        vAllButton = QPushButton("Tout cocher")
        vAllButton.clicked.connect(lambda: self.check_sources(True))

        vNoneButton = QPushButton("Tout décocher")
        vNoneButton.clicked.connect(lambda: self.check_sources(False))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vAllButton)
        vButtons.addWidget(vNoneButton)
        vButtons.addStretch()

        vLayout = QVBoxLayout(rGroup)
        vLayout.addLayout(vGrid)
        vLayout.addLayout(vButtons)

        return rGroup

    def create_advanced_group(self):
        """Construit les options techniques du scraping."""
        self.max_pages_spin = create_spin_box(0, 50, 0, "", "Valeur de chaque source")

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setSuffix(" s")

        self.timeout_spin = create_spin_box(5, 120, 30, " s")

        self.distance_spin = create_spin_box(0, 500, 0, " km", "Aucune limite")

        rGroup = QGroupBox("Options avancées")

        vForm = QFormLayout(rGroup)
        vForm.addRow("Pages maximum par source", self.max_pages_spin)
        vForm.addRow("Délai entre deux requêtes", self.delay_spin)
        vForm.addRow("Délai d'attente d'une réponse", self.timeout_spin)
        vForm.addRow("Distance maximum", self.distance_spin)

        return rGroup

    def create_actions(self):
        """Construit les boutons de lancement et d'arrêt."""
        self.start_button = create_button(
            "Lancer la recherche", "search", "primaryButton", COLORS["surface"]
        )
        self.start_button.clicked.connect(self.start_search)

        self.stop_button = QPushButton("Arrêter")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_search)

        rLayout = QHBoxLayout()
        rLayout.addWidget(self.start_button)
        rLayout.addWidget(self.stop_button)
        rLayout.addStretch()

        return rLayout

    def create_progress(self):
        """Construit la barre de progression et les messages d'état."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Prêt")

        self.result_label = QLabel()
        self.result_label.setObjectName("pageSubtitle")

        self.show_offers_button = QPushButton("Voir les offres")
        self.show_offers_button.clicked.connect(self.show_offers_requested.emit)
        self.show_offers_button.hide()

        vResult = QHBoxLayout()
        vResult.addWidget(self.result_label)
        vResult.addWidget(self.show_offers_button)
        vResult.addStretch()

        self.warning_label = QLabel()
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()

        rLayout = QVBoxLayout()
        rLayout.addWidget(self.progress_bar)
        rLayout.addWidget(self.status_label)
        rLayout.addLayout(vResult)
        rLayout.addWidget(self.warning_label)

        return rLayout

    def toggle_advanced_options(self, pVisible):
        """Affiche ou masque les options avancées."""
        self.advanced_group.setVisible(pVisible)

        self.advanced_button.setText(
            "Masquer les options avancées"
            if pVisible
            else "Afficher les options avancées"
        )

    def check_sources(self, pChecked):
        """Coche ou décoche toutes les sources sélectionnables."""
        for vCheckBox in self.source_checkboxes.values():
            if vCheckBox.isEnabled():
                vCheckBox.setChecked(pChecked)

    def get_selected_sources(self):
        """Retourne les sources cochées et sélectionnables."""
        rSources = [
            vName
            for vName, vCheckBox in self.source_checkboxes.items()
            if vCheckBox.isEnabled() and vCheckBox.isChecked()
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
            self.status_label.setText("Sélectionnez au moins une source.")

        elif not self.is_running():
            self.save_settings()

            self.result_label.clear()
            self.show_offers_button.hide()
            self.warning_label.hide()
            self.progress_bar.setValue(0)
            self.status_label.setText("Démarrage de la recherche...")
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
            self.status_label.setText("Arrêt demandé, fin de la source en cours...")

    @Slot(int, int, str)
    def show_progress(self, pIndex, pTotal, pLabel):
        """Affiche la source en cours d'interrogation."""
        self.progress_bar.setValue(round((pIndex - 1) / pTotal * 100))
        self.status_label.setText(f"Interrogation de {pLabel} ({pIndex}/{pTotal})")

    @Slot(object)
    def show_result(self, pResult):
        """Affiche le bilan d'une recherche terminée."""
        vItems = pResult.items
        vNewCount = int(vItems["is_new"].sum()) if "is_new" in vItems else 0

        self.progress_bar.setValue(100)
        self.status_label.setText("Recherche terminée")
        self.result_label.setText(
            f"{len(vItems)} offre(s) correspondent aux critères, "
            f"dont {vNewCount} nouvelle(s)."
        )
        self.show_offers_button.show()

        if pResult.error_message:
            self.show_warning(f"Sources en erreur : {pResult.error_message}")

    @Slot()
    def show_cancelled(self):
        """Indique que la recherche a été arrêtée sans enregistrement."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Recherche arrêtée, aucune offre enregistrée")

    @Slot(str)
    def show_error(self, pMessage):
        """Affiche l'échec de la recherche."""
        self.progress_bar.setValue(0)
        self.status_label.setText("La recherche a échoué")
        self.show_warning(pMessage)

    def show_warning(self, pMessage):
        """Affiche un message d'avertissement sous la progression."""
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
                if vName in self.source_checkboxes:
                    self.source_checkboxes[vName].setChecked(True)
