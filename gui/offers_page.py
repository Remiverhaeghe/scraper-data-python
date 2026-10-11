"""Page des offres enregistrées : filtres, tableau triable et suivi"""

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from config import EXPIRY_DAYS
from gui.offer_detail import OfferDetailPanel
from gui.offers_model import COLUMNS, SORT_ROLE, OffersTableModel
from gui.theme import COLORS
from gui.widgets import create_button, create_icon_label, create_page_header
from job.contract import CONTRACT_TYPES
from job.deduplication import group_offers
from job.export import EXPORT_FORMATS, export_offers
from job.presentation import (
    AVAILABILITY_FILTERS,
    DEFAULT_AVAILABILITY,
    FOLLOW_UP_FILTER,
    PUBLISHED_PERIODS,
    STATUS_LABELS,
    build_offer_filters,
    prepare_offer,
)
from job.settings import load_settings
from job.sources.registry import SOURCES
from storage.duplicates import get_decisions
from storage.job_offers import get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, l'utilisateur affine ses filtres plutôt que de parcourir la liste
MAX_DISPLAYED_OFFERS = 1000

# Statut filtré par les préréglages ouverts depuis l'accueil
PRESET_STATUSES = {"applications": "APPLIED", "follow_ups": FOLLOW_UP_FILTER}

# Attente après la dernière frappe avant de relancer la recherche
SEARCH_DELAY_MS = 300


def create_salary_spin(pEmptyText, pSuffix):
    """Crée un champ de salaire net mensuel ; 0 signifie aucune borne."""

    rSpin = QSpinBox()
    rSpin.setRange(0, 20000)
    rSpin.setSingleStep(100)
    rSpin.setSuffix(pSuffix)
    rSpin.setSpecialValueText(pEmptyText)

    return rSpin


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
        # Le lambda est nécessaire : detail_panel n'est créé qu'après cette ligne,
        # il n'est donc cherché qu'au moment du double-clic.
        self.table.doubleClicked.connect(
            lambda: self.detail_panel.open_offer()  # pylint: disable=unnecessary-lambda
        )

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

        self.result_keys = None
        self.results_banner = self.create_results_banner()

        vLayout.addLayout(self.create_filters())
        vLayout.addWidget(self.results_banner)
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

        self.min_salary_spin = create_salary_spin("Sans minimum", " € net min")
        self.max_salary_spin = create_salary_spin("Sans maximum", " € net max")

        self.availability_combo = QComboBox()

        for vValue, vLabel in AVAILABILITY_FILTERS.items():
            self.availability_combo.addItem(vLabel, vValue)

        self.published_combo = QComboBox()

        for vDays, vLabel in PUBLISHED_PERIODS.items():
            self.published_combo.addItem(vLabel, vDays)

        self.salary_check = QCheckBox("Avec salaire")
        self.remote_check = QCheckBox("Télétravail")
        self.new_check = QCheckBox("Nouvelles uniquement")
        self.multiple_check = QCheckBox("Multi-annonces")
        self.multiple_check.setToolTip("Offres publiées plusieurs fois, regroupées")

        for vCombo in (
            self.source_combo,
            self.contract_combo,
            self.status_combo,
            self.availability_combo,
            self.published_combo,
        ):
            vCombo.currentIndexChanged.connect(self.refresh)

        for vSpin in (self.min_salary_spin, self.max_salary_spin):
            vSpin.valueChanged.connect(self.search_timer.start)

        for vCheck in (
            self.salary_check,
            self.remote_check,
            self.new_check,
            self.multiple_check,
        ):
            vCheck.toggled.connect(self.refresh)

        vSearchRow = QHBoxLayout()
        vSearchRow.addWidget(self.search_edit, 1)
        vSearchRow.addWidget(self.source_combo)
        vSearchRow.addWidget(self.status_combo)

        vOptionsRow = QHBoxLayout()
        vOptionsRow.setSpacing(16)
        for vWidget in (
            self.contract_combo,
            self.availability_combo,
            self.published_combo,
            self.min_salary_spin,
            self.max_salary_spin,
            self.salary_check,
            self.remote_check,
            self.new_check,
            self.multiple_check,
        ):
            vOptionsRow.addWidget(vWidget)

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
        vSettings = load_settings(self.database_file)

        vOffers = get_offers(
            self.database_file,
            **self.build_filters(
                datetime.now(),
                vSettings["new_offer_days"],
                vSettings["expiry_days"],
            ),
        )

        rCount = export_offers(vOffers, pPath)

        return rCount

    def create_results_banner(self):
        """Construit le bandeau qui signale l'affichage des résultats d'une recherche."""
        self.results_label = QLabel()
        self.results_label.setObjectName("activityTitle")

        vShowAllButton = QPushButton("Afficher toutes les offres")
        vShowAllButton.setObjectName("linkButton")
        vShowAllButton.clicked.connect(lambda: self.apply_preset("offers"))

        rBanner = QFrame()
        rBanner.setObjectName("resultsBanner")

        vLayout = QHBoxLayout(rBanner)
        vLayout.setContentsMargins(14, 8, 14, 8)
        vLayout.addWidget(create_icon_label("search", COLORS["primary"], 18))
        vLayout.addWidget(self.results_label, 1)
        vLayout.addWidget(vShowAllButton)

        rBanner.hide()

        return rBanner

    def apply_preset(self, pPreset, pKeys=None, pDescription=""):
        """Réinitialise les filtres puis applique un préréglage.

        Préréglages : offers, new_offers, applications ou follow_ups. pKeys
        restreint la liste aux offres d'une recherche, décrite par pDescription.
        """
        self.result_keys = pKeys
        self.results_label.setText(pDescription)
        self.results_banner.setVisible(pKeys is not None)

        vWidgets = (
            self.search_edit,
            self.source_combo,
            self.contract_combo,
            self.status_combo,
            self.availability_combo,
            self.published_combo,
            self.min_salary_spin,
            self.max_salary_spin,
            self.salary_check,
            self.remote_check,
            self.new_check,
            self.multiple_check,
        )

        # Une seule relecture en base plutôt qu'une par filtre modifié
        for vWidget in vWidgets:
            vWidget.blockSignals(True)

        self.search_edit.clear()
        self.source_combo.setCurrentIndex(0)
        self.contract_combo.setCurrentIndex(0)
        self.published_combo.setCurrentIndex(0)
        self.availability_combo.setCurrentIndex(
            self.availability_combo.findData(DEFAULT_AVAILABILITY)
        )
        self.min_salary_spin.setValue(0)
        self.max_salary_spin.setValue(0)
        self.salary_check.setChecked(False)
        self.remote_check.setChecked(False)
        self.new_check.setChecked(pPreset == "new_offers")
        self.multiple_check.setChecked(False)
        self.status_combo.setCurrentIndex(
            max(self.status_combo.findData(PRESET_STATUSES.get(pPreset)), 0)
        )

        for vWidget in vWidgets:
            vWidget.blockSignals(False)

        self.refresh()

    def build_filters(self, pNow, pNewOfferDays, pExpiryDays=EXPIRY_DAYS):
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
            pMaxNetSalary=self.max_salary_spin.value() or None,
            pPublishedDays=self.published_combo.currentData(),
            pHasSalary=self.salary_check.isChecked(),
            pKeys=self.result_keys,
            pAvailability=self.availability_combo.currentData(),
            pExpiryDays=pExpiryDays,
        )

        return rFilters

    def refresh(self):
        """Relit les offres en base en conservant l'offre sélectionnée."""
        vNow = datetime.now()
        vSelectedKey = self.get_offer_key(self.detail_panel.offer)

        try:
            vSettings = load_settings(self.database_file)
            vNewOfferDays = vSettings["new_offer_days"]

            vOffers = get_offers(
                self.database_file,
                # Une offre de plus que la limite est lue pour savoir s'il en reste : le
                # message invite alors à affiner les filtres.
                pLimit=MAX_DISPLAYED_OFFERS + 1,
                **self.build_filters(vNow, vNewOfferDays, vSettings["expiry_days"]),
            )

        except Exception:
            logger.exception("Impossible de charger les offres")

            self.count_label.setText("Les offres n'ont pas pu être chargées.")

        else:
            vNewSince = vNow - timedelta(days=vNewOfferDays)

            vPrepared = [
                prepare_offer(vOffer, vNewSince, vNow, vSettings["expiry_days"])
                for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
            ]

            # Les annonces d'une même offre sont regroupées en une seule ligne.
            vPrepared = group_offers(vPrepared, get_decisions(self.database_file))

            if self.multiple_check.isChecked():
                vPrepared = [vOffer for vOffer in vPrepared if vOffer["duplicates"]]

            self.model.set_offers(vPrepared)
            # Au-delà de la limite, le message invite à affiner ; sinon, il compte
            # les lignes affichées, annonces regroupées comprises.
            vCount = (
                len(vOffers) if len(vOffers) > MAX_DISPLAYED_OFFERS else len(vPrepared)
            )
            self.count_label.setText(self.describe_count(vCount, vNewOfferDays))
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
            # Le tableau est trié par un proxy : une ligne affichée ne correspond pas à la
            # même ligne du modèle, d'où la conversion par mapToSource.
            vOffer = self.model.offer_at(self.proxy.mapToSource(pCurrent).row())

        self.detail_panel.show_offer(vOffer)
