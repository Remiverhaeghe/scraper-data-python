"""Page des offres enregistrées : filtres, tableau triable et suivi"""

from datetime import datetime, timedelta

from PySide6.QtCore import QSortFilterProxyModel, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from config import NEW_OFFER_DAYS
from gui.offer_detail import OfferDetailPanel
from gui.offers_model import COLUMNS, SORT_ROLE, OffersTableModel
from gui.widgets import create_page_header
from job.contract import CONTRACT_TYPES
from job.presentation import (
    FOLLOW_UP_FILTER,
    STATUS_LABELS,
    build_offer_filters,
    prepare_offer,
)
from job.sources.registry import SOURCES
from storage.job_offers import get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, l'utilisateur affine ses filtres plutôt que de parcourir la liste
MAX_DISPLAYED_OFFERS = 1000

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
        self.table.sortByColumn(6, Qt.SortOrder.DescendingOrder)

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
            f"Offres enregistrées, les nouvelles des {NEW_OFFER_DAYS} derniers "
            "jours en gras ; double-cliquez pour ouvrir l'offre",
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

        rLayout = QHBoxLayout()
        rLayout.addWidget(self.search_edit, 1)

        for vWidget in (
            self.source_combo,
            self.contract_combo,
            self.status_combo,
            self.min_salary_spin,
            self.remote_check,
            self.new_check,
        ):
            rLayout.addWidget(vWidget)

        return rLayout

    def show_follow_ups(self):
        """Sélectionne le filtre des candidatures à relancer."""
        self.status_combo.setCurrentIndex(self.status_combo.findData(FOLLOW_UP_FILTER))

    def build_filters(self, pNow):
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
        )

        return rFilters

    def refresh(self):
        """Relit les offres en base en conservant l'offre sélectionnée."""
        vNow = datetime.now()
        vSelectedKey = self.get_offer_key(self.detail_panel.offer)

        try:
            vOffers = get_offers(
                self.database_file,
                pLimit=MAX_DISPLAYED_OFFERS + 1,
                **self.build_filters(vNow),
            )

        except Exception:
            logger.exception("Impossible de charger les offres")

            self.count_label.setText("Les offres n'ont pas pu être chargées.")

        else:
            vNewSince = vNow - timedelta(days=NEW_OFFER_DAYS)

            vPrepared = [
                prepare_offer(vOffer, vNewSince)
                for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
            ]

            self.model.set_offers(vPrepared)
            self.count_label.setText(self.describe_count(len(vOffers)))
            self.select_offer(vSelectedKey)

    def describe_count(self, pCount):
        """Indique le nombre d'offres affichées."""
        if pCount > MAX_DISPLAYED_OFFERS:
            rText = (
                f"{MAX_DISPLAYED_OFFERS} premières offres affichées, "
                "affinez les filtres pour voir les autres."
            )
        else:
            rText = f"{pCount} offre(s)"

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

        if vSourceRow is None:
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
