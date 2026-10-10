"""Page des offres enregistrées : filtres, tableau triable et suivi"""

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gui.offer_detail import OfferDetailPanel
from gui.offers_model import COLUMNS, SORT_ROLE, OffersTableModel
from gui.theme import COLORS
from gui.widgets import create_button, create_page_header
from job.contract import CONTRACT_TYPES
from job.export import EXPORT_FORMATS, export_offers
from job.presentation import (
    FOLLOW_UP_FILTER,
    STATUS_LABELS,
    build_offer_filters,
    prepare_offer,
)
from job.settings import load_settings
from job.sources.registry import SOURCES
from storage.job_offers import get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, l'utilisateur affine ses filtres plutôt que de parcourir la liste
MAX_DISPLAYED_OFFERS = 1000

# Statut filtré par les préréglages ouverts depuis l'accueil
PRESET_STATUSES = {"applications": "APPLIED", "follow_ups": FOLLOW_UP_FILTER}

# Attente après la dernière frappe avant de relancer la recherche
SEARCH_DELAY_MS = 300


class OffersPage(QWidget):
    """Liste les offres en base et affiche le détail de l'offre choisie."""

    def __init__(self, pDatabaseFile):
        """Construit les filtres, le tableau et le panneau de détail."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.model = OffersTableModel()

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(SORT_ROLE)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        vHeader = self.table.horizontalHeader()

        for vColumn, (_, _, vWidth) in enumerate(COLUMNS):
            if vWidth is None:
                vHeader.setSectionResizeMode(vColumn, QHeaderView.ResizeMode.Stretch)
            else:
                self.table.setColumnWidth(vColumn, vWidth)
        # Sans colonne triée, l'ordre de la requête est conservé : nouvelles en tête.
        self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        self.table.selectionModel().currentRowChanged.connect(self.show_selected_offer)
        self.table.doubleClicked.connect(lambda: self.detail_panel.open_offer())

        self.detail_panel = OfferDetailPanel(pDatabaseFile)
        self.detail_panel.application_changed.connect(self.refresh)

        vSplitter = QSplitter(Qt.Orientation.Vertical)
        vSplitter.addWidget(self.table)
        vSplitter.addWidget(self.detail_panel)
        vSplitter.setSizes([500, 300])

        self.count_label = QLabel()
        self.count_label.setObjectName("pageSubtitle")

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout,
            "Offres",
            "Toutes les offres récupérées : filtrez, triez et suivez vos candidatures",
            [self.create_export_button()],
            pIcon="briefcase",
        )

        vLayout.addLayout(self.create_filters())
        vLayout.addWidget(self.count_label)
        vLayout.addWidget(vSplitter, 1)

    def create_filters(self):
        """Construit la barre de filtres, appliqués dès leur modification."""
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(SEARCH_DELAY_MS)
        self.search_timer.timeout.connect(self.refresh)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Titre, entreprise, lieu, description")
        self.search_edit.setMinimumWidth(260)
        self.search_edit.textChanged.connect(self.search_timer.start)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Toutes les sources", None)

        for vName, vDefinition in SOURCES.items():
            self.source_combo.addItem(vDefinition.label, vName)

        self.contract_combo = QComboBox()
        self.contract_combo.addItem("Tous les contrats", None)

        for vContract in CONTRACT_TYPES:
            self.contract_combo.addItem(vContract, vContract)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Offres actives", None)
        self.status_combo.addItem("À relancer", FOLLOW_UP_FILTER)

        for vStatus, vLabel in STATUS_LABELS.items():
            self.status_combo.addItem(vLabel, vStatus)

        self.min_salary_spin = QSpinBox()
        self.min_salary_spin.setRange(0, 20000)
        self.min_salary_spin.setSingleStep(100)
        self.min_salary_spin.setSuffix(" € net/mois")
        self.min_salary_spin.setSpecialValueText("Tous salaires")

        self.remote_check = QCheckBox("Télétravail")
        self.new_check = QCheckBox("Nouvelles uniquement")

        for vCombo in (self.source_combo, self.contract_combo, self.status_combo):
            vCombo.currentIndexChanged.connect(self.refresh)

        self.min_salary_spin.valueChanged.connect(self.search_timer.start)
        self.remote_check.toggled.connect(self.refresh)
        self.new_check.toggled.connect(self.refresh)

        vSearchRow = QHBoxLayout()
        vSearchRow.addWidget(self.search_edit, 1)
        vSearchRow.addWidget(self.source_combo)
        vSearchRow.addWidget(self.status_combo)

        vOptionsRow = QHBoxLayout()
        vOptionsRow.setSpacing(16)
        vOptionsRow.addWidget(self.contract_combo)
        vOptionsRow.addWidget(self.min_salary_spin)
        vOptionsRow.addWidget(self.remote_check)
        vOptionsRow.addWidget(self.new_check)
        vOptionsRow.addStretch()

        rLayout = QVBoxLayout()
        rLayout.setSpacing(10)
        rLayout.addLayout(vSearchRow)
        rLayout.addLayout(vOptionsRow)

        return rLayout

    def create_export_button(self):
        """Crée le bouton d'export et son menu de formats."""
        rButton = create_button("Exporter", "download", pIconColor=COLORS["primary"])

        vMenu = QMenu(rButton)

        for vSuffix, vLabel in EXPORT_FORMATS.items():
            vMenu.addAction(
                f"{vLabel} ({vSuffix})",
                lambda pSuffix=vSuffix: self.choose_export_file(pSuffix),
            )

        rButton.setMenu(vMenu)

        return rButton

    def choose_export_file(self, pSuffix):
        """Demande où enregistrer l'export puis l'écrit."""
        vLabel = EXPORT_FORMATS[pSuffix]

        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les offres",
            str(Path.home() / f"offres_{datetime.now():%Y-%m-%d}{pSuffix}"),
            f"{vLabel} (*{pSuffix})",
        )

        if vPath:
            try:
                vCount = self.export_to(vPath)

            except Exception:
                logger.exception("Échec de l'export des offres en %s", vLabel)

                QMessageBox.warning(
                    self, "Export impossible", "Le fichier n'a pas pu être écrit."
                )

            else:
                QMessageBox.information(
                    self, "Export terminé", f"{vCount} offre(s) exportée(s)."
                )

    def export_to(self, pPath):
        """Exporte toutes les offres correspondant aux filtres, sans limite d'affichage."""
        vOffers = get_offers(
            self.database_file,
            **self.build_filters(
                datetime.now(),
                load_settings(self.database_file)["new_offer_days"],
            ),
        )

        rCount = export_offers(vOffers, pPath)

        return rCount

    def apply_preset(self, pPreset):
        """Réinitialise les filtres puis applique un préréglage de l'accueil.

        Préréglages : offers, new_offers, applications ou follow_ups.
        """
        vWidgets = (
            self.search_edit,
            self.source_combo,
            self.contract_combo,
            self.status_combo,
            self.min_salary_spin,
            self.remote_check,
            self.new_check,
        )

        # Une seule relecture en base plutôt qu'une par filtre modifié
        for vWidget in vWidgets:
            vWidget.blockSignals(True)

        self.search_edit.clear()
        self.source_combo.setCurrentIndex(0)
        self.contract_combo.setCurrentIndex(0)
        self.min_salary_spin.setValue(0)
        self.remote_check.setChecked(False)
        self.new_check.setChecked(pPreset == "new_offers")
        self.status_combo.setCurrentIndex(
            max(self.status_combo.findData(PRESET_STATUSES.get(pPreset)), 0)
        )

        for vWidget in vWidgets:
            vWidget.blockSignals(False)

        self.refresh()

    def build_filters(self, pNow, pNewOfferDays):
        """Traduit les filtres de la page en paramètres de get_offers."""
        rFilters = build_offer_filters(
            pSearch=self.search_edit.text(),
            pSource=self.source_combo.currentData(),
            pContract=self.contract_combo.currentData(),
            pRemote=self.remote_check.isChecked(),
            pMinNetSalary=self.min_salary_spin.value() or None,
            pNewOnly=self.new_check.isChecked(),
            pStatus=self.status_combo.currentData(),
            pNow=pNow,
            pNewOfferDays=pNewOfferDays,
        )

        return rFilters

    def refresh(self):
        """Relit les offres en base en conservant l'offre sélectionnée."""
        vNow = datetime.now()
        vSelectedKey = self.get_offer_key(self.detail_panel.offer)

        try:
            vNewOfferDays = load_settings(self.database_file)["new_offer_days"]

            vOffers = get_offers(
                self.database_file,
                pLimit=MAX_DISPLAYED_OFFERS + 1,
                **self.build_filters(vNow, vNewOfferDays),
            )

        except Exception:
            logger.exception("Impossible de charger les offres")

            self.count_label.setText("Les offres n'ont pas pu être chargées.")

        else:
            vNewSince = vNow - timedelta(days=vNewOfferDays)

            vPrepared = [
                prepare_offer(vOffer, vNewSince)
                for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
            ]

            self.model.set_offers(vPrepared)
            self.count_label.setText(self.describe_count(len(vOffers), vNewOfferDays))
            self.select_offer(vSelectedKey)

    def describe_count(self, pCount, pNewOfferDays):
        """Indique le nombre d'offres affichées."""
        if pCount > MAX_DISPLAYED_OFFERS:
            rText = (
                f"{MAX_DISPLAYED_OFFERS} premières offres affichées, "
                "affinez les filtres pour voir les autres."
            )
        else:
            rText = (
                f"{pCount} offre(s) · en gras, les nouvelles des {pNewOfferDays} "
                "derniers jours · double-clic pour ouvrir l'offre"
            )

        return rText

    @staticmethod
    def get_offer_key(pOffer):
        """Identifie une offre par sa source et son identifiant."""
        rKey = (pOffer["source"], pOffer["source_id"]) if pOffer else None

        return rKey

    def select_offer(self, pKey):
        """Resélectionne une offre après rechargement, ou vide le détail."""
        vSourceRow = next(
            (
                vRow
                for vRow, vOffer in enumerate(self.model.offers)
                if self.get_offer_key(vOffer) == pKey
            ),
            None,
        )

        # Sans offre à resélectionner, la première est affichée plutôt qu'un détail vide.
        if vSourceRow is None and self.model.offers:
            self.table.selectRow(0)
        elif vSourceRow is None:
            self.table.clearSelection()
            self.detail_panel.show_offer(None)
        else:
            self.table.selectRow(
                self.proxy.mapFromSource(self.model.index(vSourceRow, 0)).row()
            )

    def show_selected_offer(self, pCurrent):
        """Affiche le détail de l'offre de la ligne sélectionnée."""
        vOffer = None

        if pCurrent.isValid():
            vOffer = self.model.offer_at(self.proxy.mapToSource(pCurrent).row())

        self.detail_panel.show_offer(vOffer)
