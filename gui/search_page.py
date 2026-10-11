"""Page de recherche : critères, sources, progression et arrêt"""

from datetime import datetime

from PySide6.QtCore import QSettings, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from job.presentation import describe_search, describe_sources
from job.sources.registry import SOURCES
from storage.saved_searches import (
    delete_saved_search,
    get_saved_searches,
    save_search,
)
from utils.logger import get_logger

logger = get_logger(__name__)

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


def create_spin_box(pMinimum, pMaximum, pValue, pSuffix="", pEmptyText=None):
    """Crée un champ numérique ; pEmptyText remplace l'affichage du minimum."""

    rSpinBox = QSpinBox()
    rSpinBox.setRange(pMinimum, pMaximum)
    rSpinBox.setValue(pValue)
    rSpinBox.setSuffix(pSuffix)

    if pEmptyText is not None:
        rSpinBox.setSpecialValueText(pEmptyText)

    return rSpinBox


def create_range(pMinimum, pMaximum):
    """Place deux champs côte à côte sous la forme « entre … et … »."""

    rRange = QWidget()

    vLayout = QHBoxLayout(rRange)
    vLayout.setContentsMargins(0, 0, 0, 0)
    vLayout.setSpacing(10)
    vLayout.addWidget(QLabel("entre"))
    vLayout.addWidget(pMinimum, 1)
    vLayout.addWidget(QLabel("et"))
    vLayout.addWidget(pMaximum, 1)

    return rRange


def split_words(pText):
    """Découpe une saisie séparée par des virgules ; None si elle est vide."""

    rWords = [vWord.strip() for vWord in pText.split(",") if vWord.strip()] or None

    return rWords


def create_field(pLabel, pWidget):
    """Place un libellé au-dessus de son champ."""

    vLabel = QLabel(pLabel)
    vLabel.setObjectName("fieldLabel")

    rLayout = QVBoxLayout()
    rLayout.setSpacing(6)
    rLayout.addWidget(vLabel)
    rLayout.addWidget(pWidget)

    return rLayout


def describe_saved_search(pSearch):
    """Résume une recherche enregistrée : critères, puis sources."""

    vParameters = {**pSearch["criteria"], "sources": pSearch["sources"]}

    rDescription = " · ".join(
        vPart
        for vPart in (
            describe_search(vParameters) or "Sans critère",
            describe_sources(vParameters),
        )
        if vPart
    )

    return rDescription


class SearchPage(QWidget):
    """Permet de lancer une recherche d'offres et d'en suivre l'avancement."""

    search_started = Signal()
    search_ended = Signal()
    # Offres trouvées, en couples (source, identifiant), et leur description
    show_offers_requested = Signal(object, str)
    schedule_requested = Signal(list, dict)

    def __init__(self, pSettings=None, pDatabaseFile=None):
        """Construit le formulaire et restaure les derniers critères saisis.

        Sans base de données, les recherches enregistrées ne sont pas proposées.
        """
        super().__init__()

        self.settings = pSettings if pSettings is not None else QSettings()
        self.database_file = pDatabaseFile

        # Recherches enregistrées : widgets créés seulement avec une base
        self.saved_combo = None
        self.delete_saved_button = None
        self.saved_searches = {}
        self.search_thread = None
        self.search_worker = None
        self.source_buttons = {}
        self.last_result_keys = []
        self.last_result_label = ""

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(16)

        create_page_header(
            vLayout,
            "Recherche",
            "Interrogez les sources et enregistrez les nouvelles offres en base",
            pIcon="search",
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

        self.min_salary_spin = create_spin_box(0, 20000, 0, " €", "Aucun minimum")
        self.max_salary_spin = create_spin_box(0, 20000, 0, " €", "Aucun maximum")

        for vSpin in (self.min_salary_spin, self.max_salary_spin):
            vSpin.setSingleStep(100)
            vSpin.valueChanged.connect(self.keep_salary_range)

        self.remote_check = QCheckBox("Télétravail uniquement")

        self.skills_edit = QLineEdit()
        self.skills_edit.setPlaceholderText("Ex. Java, Spring, SQL")

        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("Ex. stage, alternance")

        vCard, vLayout = create_card("Critères")

        if self.database_file is not None:
            vLayout.addLayout(self.create_saved_searches_row())

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(16)
        vGrid.setVerticalSpacing(12)
        vGrid.addLayout(create_field("Mot-clé", self.keyword_edit), 0, 0)
        vGrid.addLayout(create_field("Localisation", self.location_edit), 0, 1)
        vGrid.addLayout(create_field("Nombre maximum", self.max_items_spin), 0, 2)
        vGrid.addLayout(create_field("Contrat", self.contract_combo), 1, 0)
        vGrid.addLayout(
            create_field(
                "Salaire net mensuel",
                create_range(self.min_salary_spin, self.max_salary_spin),
            ),
            1,
            1,
        )
        vGrid.addWidget(self.remote_check, 1, 2, Qt.AlignmentFlag.AlignBottom)
        vGrid.addLayout(create_field("Compétences requises", self.skills_edit), 2, 0)
        vGrid.addLayout(
            create_field("Mots à exclure du titre", self.exclude_edit), 2, 1, 1, 2
        )
        vGrid.setColumnStretch(0, 2)
        vGrid.setColumnStretch(1, 2)
        vGrid.setColumnStretch(2, 1)

        self.remember_check = QCheckBox("Mémoriser ces critères")
        self.remember_check.setToolTip(
            "Coché, la recherche est retrouvée à la prochaine ouverture ; "
            "sinon les champs repartent vides"
        )
        self.remember_check.toggled.connect(self.save_settings)

        vLayout.addLayout(vGrid)
        vLayout.addWidget(self.remember_check)

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
                "circle-check", COLORS["border"], 16, pCheckedColor=COLORS["success"]
            )
        )
        rButton.toggled.connect(self.update_source_count)

        vReason = pDefinition.get_unavailability_reason()

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

        self.schedule_button = create_button(
            "Planifier cette recherche", "calendar", pIconColor=COLORS["primary"]
        )
        self.schedule_button.setToolTip(
            "Enregistre ces critères et ces sources pour le planificateur"
        )
        self.schedule_button.clicked.connect(self.request_schedule)

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
        self.show_offers_button.clicked.connect(self.request_results)
        self.show_offers_button.hide()

        vRow = QHBoxLayout()
        vRow.setSpacing(12)
        vRow.addWidget(self.start_button)
        vRow.addWidget(self.stop_button)
        vRow.addWidget(self.schedule_button)
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

    def keep_salary_range(self):
        """Aligne l'autre borne du salaire lorsque le minimum dépasse le maximum."""
        vMinimum = self.min_salary_spin.value()
        vMaximum = self.max_salary_spin.value()

        # Zéro signifie « sans borne » : il n'y a alors rien à aligner.
        if vMinimum and vMaximum and vMinimum > vMaximum:
            if self.sender() is self.min_salary_spin:
                self.max_salary_spin.setValue(vMinimum)
            else:
                self.min_salary_spin.setValue(vMaximum)

    def build_criteria(self):
        """Traduit le formulaire en critères pour le contrôleur ; 0 signifie aucun."""
        rCriteria = {
            "keyword": self.keyword_edit.text().strip() or None,
            "location": self.location_edit.text().strip() or None,
            "max_items": self.max_items_spin.value(),
            "contract": self.contract_combo.currentData(),
            "min_salary": self.min_salary_spin.value() or None,
            "max_salary": self.max_salary_spin.value() or None,
            "skills": split_words(self.skills_edit.text()),
            "exclude_keywords": split_words(self.exclude_edit.text()),
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

            # La recherche tourne dans un QThread : interroger les sources dans le
            # thread de l'interface figerait la fenêtre pendant toute la recherche.
            self.search_worker = self.create_worker(vSources, self.build_criteria())
            self.search_thread = QThread(self)

            # Le worker vit dans le thread : ses signaux reviennent dans l'interface par
            # la file d'événements de Qt, sans accès concurrent aux widgets.
            self.search_worker.moveToThread(self.search_thread)

            self.search_thread.started.connect(self.search_worker.run)

            self.search_worker.progress.connect(self.show_progress)
            self.search_worker.succeeded.connect(self.show_result)
            self.search_worker.cancelled.connect(self.show_cancelled)
            self.search_worker.failed.connect(self.show_error)

            # Quelle que soit l'issue, le thread s'arrête puis end_search libère
            # les ressources. Une erreur levée dans un slot est avalée par Qt : si
            # l'écran ne se met pas à jour, consulter les journaux.
            for vSignal in (
                self.search_worker.succeeded,
                self.search_worker.cancelled,
                self.search_worker.failed,
            ):
                vSignal.connect(self.search_thread.quit)

            self.search_thread.finished.connect(self.end_search)

            self.search_thread.start()
            self.search_started.emit()

    def request_schedule(self):
        """Demande l'enregistrement des critères et sources pour le planificateur."""
        vSources = self.get_selected_sources()

        if vSources:
            self.schedule_requested.emit(vSources, self.build_criteria())
        else:
            self.set_status("warning", "Sélectionnez au moins une source.")

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
    def request_results(self):
        """Affiche uniquement les offres trouvées par la dernière recherche."""
        self.show_offers_requested.emit(self.last_result_keys, self.last_result_label)

    def show_result(self, pResult):
        """Affiche le bilan d'une recherche terminée."""
        vItems = pResult.items
        vNewCount = int(vItems["is_new"].sum()) if "is_new" in vItems else 0

        # Les clés des offres trouvées permettent à « Voir les offres » de n'afficher
        # que les résultats de cette recherche.
        self.last_result_keys = list(
            zip(vItems["source"].astype(str), vItems["source_id"].astype(str))
        )
        self.last_result_label = (
            f"Résultats de la recherche de {datetime.now():%H:%M} : "
            f"{len(vItems)} offre(s), dont {vNewCount} nouvelle(s)"
        )

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
        # deleteLater laisse Qt détruire les objets une fois leurs signaux traités.
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
        """Mémorise les sources et, si la case est cochée, les critères saisis."""
        # Clés QSettings search/remember, search/sources et search/criteria/*,
        # stockées dans le registre Windows au nom de l'application.
        vRemember = self.remember_check.isChecked()

        self.settings.setValue("search/remember", vRemember)
        self.settings.setValue("search/sources", ",".join(self.get_selected_sources()))

        # Décochée, la case efface les critères gardés : les champs repartiront vides.
        self.settings.remove("search/criteria")

        if vRemember:
            for vName, vValue in (
                ("keyword", self.keyword_edit.text()),
                ("location", self.location_edit.text()),
                ("contract", self.contract_combo.currentData() or ""),
                ("min_salary", self.min_salary_spin.value()),
                ("max_salary", self.max_salary_spin.value()),
                ("remote", self.remote_check.isChecked()),
                ("skills", self.skills_edit.text()),
                ("exclude_keywords", self.exclude_edit.text()),
                ("max_items", self.max_items_spin.value()),
            ):
                self.settings.setValue(f"search/criteria/{vName}", vValue)

    def restore_settings(self):
        """Restaure les critères mémorisés ; toutes les sources par défaut."""
        vRemember = self.settings.value("search/remember", True, bool)

        # Bloque l'enregistrement déclenché par la case pendant sa restauration.
        self.remember_check.blockSignals(True)
        self.remember_check.setChecked(vRemember)
        self.remember_check.blockSignals(False)

        if vRemember:
            self.restore_criteria()

        vSources = self.settings.value("search/sources", None)

        if vSources is None:
            self.check_sources(True)
        else:
            for vName in vSources.split(","):
                if vName in self.source_buttons:
                    self.source_buttons[vName].setChecked(True)

        self.update_source_count()

    def create_saved_searches_row(self):
        """Construit la liste des recherches enregistrées et ses boutons."""
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(280)
        self.saved_combo.activated.connect(self.load_saved_search)

        vSaveButton = create_button(
            "Enregistrer…", "download", pIconColor=COLORS["primary"]
        )
        vSaveButton.setToolTip("Enregistre les critères et les sources actuels")
        vSaveButton.clicked.connect(self.save_current_search)

        self.delete_saved_button = create_button("Supprimer")
        self.delete_saved_button.clicked.connect(self.delete_current_search)

        vLabel = QLabel("Recherche enregistrée")
        vLabel.setObjectName("fieldLabel")

        rRow = QHBoxLayout()
        rRow.setSpacing(10)
        rRow.addWidget(vLabel)
        rRow.addWidget(self.saved_combo)
        rRow.addWidget(vSaveButton)
        rRow.addWidget(self.delete_saved_button)
        rRow.addStretch()

        self.refresh_saved_searches()

        return rRow

    def refresh_saved_searches(self, pSelectedName=None):
        """Recharge la liste des recherches enregistrées."""
        try:
            self.saved_searches = {
                vSearch["name"]: vSearch
                for vSearch in get_saved_searches(self.database_file)
            }

        except Exception:
            logger.exception("Impossible de lire les recherches enregistrées")

            self.saved_searches = {}

        self.saved_combo.clear()
        self.saved_combo.addItem(
            "Choisir une recherche…" if self.saved_searches else "Aucune recherche",
            None,
        )

        for vName, vSearch in self.saved_searches.items():
            self.saved_combo.addItem(vName, vName)

            # L'infobulle résume les critères et les sources de la recherche.
            self.saved_combo.setItemData(
                self.saved_combo.count() - 1,
                describe_saved_search(vSearch),
                Qt.ItemDataRole.ToolTipRole,
            )

        self.saved_combo.setCurrentIndex(
            max(self.saved_combo.findData(pSelectedName), 0)
        )
        self.delete_saved_button.setEnabled(bool(self.saved_searches))

    def load_saved_search(self):
        """Remplit le formulaire et les sources avec la recherche choisie."""
        vName = self.saved_combo.currentData()

        if vName in self.saved_searches:
            vSearch = self.saved_searches[vName]

            self.apply_criteria(vSearch["criteria"])
            self.select_sources(vSearch["sources"])
            self.set_status("idle", f"Recherche « {vName} » chargée")

    def save_current_search(self):
        """Demande un nom puis enregistre les critères et les sources actuels."""
        vSources = self.get_selected_sources()

        if not vSources:
            self.set_status("warning", "Sélectionnez au moins une source.")
            return

        vName, vAccepted = QInputDialog.getText(
            self,
            "Enregistrer la recherche",
            "Nom de la recherche (un nom existant est remplacé) :",
            text=self.saved_combo.currentData() or "",
        )

        if vAccepted:
            try:
                vSavedName = save_search(
                    self.database_file,
                    vName,
                    vSources,
                    self.build_criteria(),
                    datetime.now(),
                )

            except ValueError as vException:
                self.set_status("warning", str(vException))

            except Exception:
                logger.exception("Échec de l'enregistrement de la recherche")

                self.set_status("error", "La recherche n'a pas pu être enregistrée.")

            else:
                self.refresh_saved_searches(vSavedName)
                self.set_status("success", f"Recherche « {vSavedName} » enregistrée")

    def delete_current_search(self):
        """Supprime la recherche choisie, après confirmation."""
        vName = self.saved_combo.currentData()

        if vName is None:
            self.set_status("warning", "Choisissez d'abord une recherche enregistrée.")
            return

        vAnswer = QMessageBox.question(
            self,
            "Supprimer la recherche",
            f"Supprimer la recherche « {vName} » ?",
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            try:
                delete_saved_search(self.database_file, vName)

            except Exception:
                logger.exception("Échec de la suppression de la recherche")

                self.set_status("error", "La recherche n'a pas pu être supprimée.")

            else:
                self.refresh_saved_searches()
                self.set_status("idle", f"Recherche « {vName} » supprimée")

    def apply_criteria(self, pCriteria):
        """Remplit le formulaire avec des critères ; un critère absent est vidé."""
        self.keyword_edit.setText(pCriteria.get("keyword") or "")
        self.location_edit.setText(pCriteria.get("location") or "")
        self.contract_combo.setCurrentIndex(
            max(self.contract_combo.findData(pCriteria.get("contract")), 0)
        )
        self.min_salary_spin.setValue(pCriteria.get("min_salary") or 0)
        self.max_salary_spin.setValue(pCriteria.get("max_salary") or 0)
        self.remote_check.setChecked(bool(pCriteria.get("remote")))
        self.skills_edit.setText(", ".join(pCriteria.get("skills") or []))
        self.exclude_edit.setText(", ".join(pCriteria.get("exclude_keywords") or []))

        for vSpin, vName in (
            (self.max_items_spin, "max_items"),
            (self.max_pages_spin, "max_pages"),
            (self.delay_spin, "delay"),
            (self.timeout_spin, "timeout"),
            (self.distance_spin, "max_distance_km"),
        ):
            if vName in pCriteria:
                vSpin.setValue(pCriteria[vName] or 0)

    def select_sources(self, pSources):
        """Sélectionne exactement les sources indiquées, si elles sont disponibles."""
        for vName, vButton in self.source_buttons.items():
            vButton.setChecked(vButton.isEnabled() and vName in pSources)

        self.update_source_count()

    def restore_criteria(self):
        """Remplit le formulaire avec les critères mémorisés."""

        def read(pName, pDefault, pType):
            rValue = self.settings.value(f"search/criteria/{pName}", pDefault, pType)

            return rValue

        # Avant la mémorisation de tous les critères, seuls ces deux-là existaient.
        self.keyword_edit.setText(
            read("keyword", self.settings.value("search/keyword", "", str), str)
        )
        self.location_edit.setText(
            read("location", self.settings.value("search/location", "", str), str)
        )
        self.contract_combo.setCurrentIndex(
            max(self.contract_combo.findData(read("contract", "", str) or None), 0)
        )
        self.min_salary_spin.setValue(read("min_salary", 0, int))
        self.max_salary_spin.setValue(read("max_salary", 0, int))
        self.remote_check.setChecked(read("remote", False, bool))
        self.skills_edit.setText(read("skills", "", str))
        self.exclude_edit.setText(read("exclude_keywords", "", str))
        self.max_items_spin.setValue(
            read("max_items", self.max_items_spin.value(), int)
        )
