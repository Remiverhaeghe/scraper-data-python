"""Page des offres enregistrées : filtres, tableau triable et suivi"""

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QSettings, QSortFilterProxyModel, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from config import EXPIRY_DAYS
from gui.icons import get_icon
from gui.offer_detail import OfferDetailPanel
from gui.offer_filters_bar import OfferFiltersBar
from gui.offer_form import ManualOfferDialog
from gui.offers_model import COLUMNS, SORT_ROLE, OffersTableModel
from gui.theme import COLORS
from gui.widgets import (
    create_button,
    create_icon_label,
    create_page_header,
)
from job.agencies import load_interim_agencies, mark_agency_offers
from job.companies import (
    build_company_filter_keys,
    load_company_rules,
    mark_preferred_companies,
)
from job.deduplication import group_offers
from job.experience_fit import mark_experience_fit
from job.freshness import add_freshness
from job.salary_market import add_estimated_salaries
from job.geocoding import add_distances, load_home
from job.export import EXPORT_FORMATS, export_offers
from job.manual_offers import (
    IMPORT_FORMATS,
    describe_import,
    import_offers_file,
    list_import_problems,
)
from job.offer_filters import build_offer_filters
from job.presentation import (
    FOLLOW_UP_FILTER,
    MANUAL_SOURCE,
    prepare_offer,
)
from job.preparation import filter_by_match, score_offers
from job.profile import load_profile
from job.settings import load_settings
from storage.duplicates import get_decisions
from storage.job_applications import save_application
from storage.job_offers import get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, l'utilisateur affine ses filtres plutôt que de parcourir la liste
MAX_DISPLAYED_OFFERS = 1000

# Statut filtré par les préréglages ouverts depuis l'accueil
PRESET_STATUSES = {"applied_offers": "APPLIED", "follow_ups": FOLLOW_UP_FILTER}


# Réglage qui garde la fiche masquée d'une ouverture à l'autre
DETAIL_HIDDEN_KEY = "offers/detail_hidden"

# Largeur des colonnes du tableau et partage tableau / fiche, gardés d'une
# ouverture à l'autre ; la clé change avec la liste des colonnes.
COLUMNS_STATE_KEY = "offers/columns-v2"
SPLITTER_STATE_KEY = "offers/splitter"


class OffersPage(QWidget):
    """Liste les offres en base et affiche le détail de l'offre choisie."""

    def __init__(self, pDatabaseFile):
        """Construit les filtres, le tableau et le panneau de détail."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.home = None
        self.agencies = None

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

        # Actifs seulement quand le tableau a le focus : la saisie d'une
        # recherche n'est pas gênée.
        for vKeys, vAction in (
            ("I", lambda: self.set_current_status("INTERESTED")),
            ("P", lambda: self.set_current_status("APPLIED")),
            ("X", lambda: self.set_current_status("IGNORED")),
            ("O", self.detail_panel.open_offer),
            ("Return", self.detail_panel.open_offer),
        ):
            vShortcut = QShortcut(QKeySequence(vKeys), self.table)
            vShortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            vShortcut.activated.connect(vAction)

        self.table.setToolTip(
            "Raccourcis : I Intéressé, P Postulé, X Ignorée, O ou Entrée pour "
            "ouvrir l'annonce"
        )

        vSplitter = QSplitter(Qt.Orientation.Vertical)
        vSplitter.addWidget(self.table)
        vSplitter.addWidget(self.detail_panel)
        vSplitter.setSizes([500, 300])
        # Le tableau garde quelques lignes visibles, même quand la fiche est haute.
        self.table.setMinimumHeight(220)
        vSplitter.setCollapsible(0, False)
        vSplitter.setStretchFactor(0, 3)
        vSplitter.setStretchFactor(1, 2)
        self.splitter = vSplitter
        self.restore_layout()
        self.table.horizontalHeader().sectionResized.connect(self.save_layout)
        vSplitter.splitterMoved.connect(self.save_layout)

        self.count_label = QLabel()
        self.count_label.setObjectName("pageSubtitle")

        self.detail_button = create_button("", pIconColor=COLORS["primary"])
        self.detail_button.clicked.connect(self.toggle_detail)
        self.set_detail_visible(
            not QSettings().value(DETAIL_HIDDEN_KEY, False, type=bool)
        )

        vCountRow = QHBoxLayout()
        vCountRow.addWidget(self.count_label, 1)
        vCountRow.addWidget(self.detail_button)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout,
            "Offres",
            "Toutes les offres récupérées : filtrez, triez et suivez vos candidatures",
            [
                self.create_add_button(),
                self.create_import_button(),
                self.create_export_button(),
            ],
            pIcon="briefcase",
        )

        self.result_keys = None
        self.results_banner = self.create_results_banner()

        self.filters_bar = OfferFiltersBar()
        self.filters_bar.changed.connect(self.refresh)
        vLayout.addWidget(self.filters_bar)
        vLayout.addWidget(self.results_banner)
        vLayout.addLayout(vCountRow)
        vLayout.addWidget(vSplitter, 1)

    def restore_layout(self):
        """Rétablit la largeur des colonnes et le partage tableau / fiche gardés."""
        vSettings = QSettings()
        vColumns = vSettings.value(COLUMNS_STATE_KEY)
        vSplitter = vSettings.value(SPLITTER_STATE_KEY)

        # Un état illisible, d'une ancienne version du tableau, est ignoré par Qt.
        if vColumns is not None:
            self.table.horizontalHeader().restoreState(vColumns)

        if vSplitter is not None:
            self.splitter.restoreState(vSplitter)

    def save_layout(self, *_pArguments):
        """Garde la largeur des colonnes et le partage tableau / fiche."""
        vSettings = QSettings()
        vSettings.setValue(COLUMNS_STATE_KEY, self.table.horizontalHeader().saveState())
        vSettings.setValue(SPLITTER_STATE_KEY, self.splitter.saveState())

    def set_detail_visible(self, pVisible):
        """Affiche ou masque toute la fiche de l'offre, au profit du tableau."""
        self.detail_panel.setVisible(pVisible)
        self.detail_button.setText(
            "Masquer la fiche" if pVisible else "Afficher la fiche"
        )
        self.detail_button.setIcon(
            get_icon(
                "chevron-down" if pVisible else "chevron-up", COLORS["primary"], 18
            )
        )

    def toggle_detail(self):
        """Inverse l'affichage de la fiche et le mémorise."""
        vVisible = self.detail_panel.isHidden()
        self.set_detail_visible(vVisible)
        QSettings().setValue(DETAIL_HIDDEN_KEY, not vVisible)

    def create_add_button(self):
        """Crée le bouton de saisie manuelle d'une offre."""
        rButton = create_button(
            "Ajouter une offre", "sparkles", pIconColor=COLORS["primary"]
        )
        rButton.setToolTip("Saisir une offre trouvée en dehors des sources")
        rButton.clicked.connect(self.add_offer)

        return rButton

    def add_offer(self):
        """Ouvre la saisie d'une offre puis l'affiche une fois créée."""
        vDialog = ManualOfferDialog(self.database_file, self)

        if vDialog.exec():
            self.apply_preset("offers")
            self.select_offer((MANUAL_SOURCE, vDialog.source_id))

    def create_import_button(self):
        """Crée le bouton d'import d'offres depuis un fichier."""
        rButton = create_button("Importer", "file-text", pIconColor=COLORS["primary"])
        rButton.setToolTip(
            "Importer des offres depuis un fichier CSV, Excel ou JSON "
            "au format de l'export"
        )
        rButton.clicked.connect(self.choose_import_file)

        return rButton

    def choose_import_file(self):
        """Demande le fichier à importer puis affiche le bilan."""
        vFilter = " ".join(f"*{vSuffix}" for vSuffix in IMPORT_FORMATS)

        vPath, _ = QFileDialog.getOpenFileName(
            self, "Importer des offres", str(Path.home()), f"Offres ({vFilter})"
        )

        if vPath:
            self.import_from(vPath)

    def import_from(self, pPath):
        """Importe un fichier d'offres et affiche le bilan, lignes refusées comprises."""
        try:
            vReport = import_offers_file(
                self.database_file, pPath, Path(pPath).suffix, datetime.now()
            )

        except ValueError as vException:
            QMessageBox.warning(self, "Import impossible", str(vException))
            return

        except Exception:
            logger.exception("Échec de l'import des offres")

            QMessageBox.warning(
                self, "Import impossible", "Le fichier n'a pas pu être importé."
            )
            return

        self.apply_preset("offers")

        vBox = QMessageBox(self)
        vBox.setWindowTitle("Import terminé")
        vBox.setText(describe_import(vReport))

        vProblems = list_import_problems(vReport)

        if vProblems:
            vBox.setDetailedText("\n".join(vProblems))

        vBox.exec()

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
                load_company_rules(self.database_file),
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

        Préréglages : offers, new_offers, applied_offers ou follow_ups. pKeys
        restreint la liste aux offres d'une recherche, décrite par pDescription.
        """
        self.result_keys = pKeys
        self.results_label.setText(pDescription)
        self.results_banner.setVisible(pKeys is not None)

        self.filters_bar.reset(
            pNewOnly=pPreset == "new_offers", pStatus=PRESET_STATUSES.get(pPreset)
        )
        self.refresh()

    def build_filters(
        self, pNow, pNewOfferDays, pExpiryDays=EXPIRY_DAYS, pCompanyRules=None
    ):
        """Traduit les filtres de la page en paramètres de get_offers."""
        rFilters = build_offer_filters(
            self.filters_bar.read_choices(),
            pNow=pNow,
            pNewOfferDays=pNewOfferDays,
            pExpiryDays=pExpiryDays,
            pCompanyKeys=(
                build_company_filter_keys(pCompanyRules) if pCompanyRules else None
            ),
            pAgencies=self.agencies,
            pHome=self.home,
            pKeys=self.result_keys,
        )

        return rFilters

    def update_distance_filter(self, pHome):
        """Garde le domicile et n'active le filtre de distance qu'avec lui."""
        self.home = pHome
        self.filters_bar.set_home(pHome)

    def refresh(self):
        """Relit les offres en base en conservant l'offre sélectionnée."""
        vNow = datetime.now()
        vSelectedKey = self.get_offer_key(self.detail_panel.offer)

        try:
            vSettings = load_settings(self.database_file)
            vNewOfferDays = vSettings["new_offer_days"]
            vCompanyRules = load_company_rules(self.database_file)
            self.update_distance_filter(load_home(self.database_file))
            self.agencies = load_interim_agencies(self.database_file)

            vOffers = get_offers(
                self.database_file,
                # Une offre de plus que la limite est lue pour savoir s'il en reste : le
                # message invite alors à affiner les filtres.
                pLimit=MAX_DISPLAYED_OFFERS + 1,
                **self.build_filters(
                    vNow, vNewOfferDays, vSettings["expiry_days"], vCompanyRules
                ),
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

            mark_preferred_companies(vPrepared, vCompanyRules)
            score_offers(vPrepared, load_profile(self.database_file))
            add_distances(vPrepared, self.home)
            mark_agency_offers(vPrepared, self.agencies)
            mark_experience_fit(vPrepared, vSettings["experience_years"])

            if self.filters_bar.reach_check.isChecked():
                vPrepared = [
                    vOffer for vOffer in vPrepared if not vOffer["above_experience"]
                ]
            vPrepared = filter_by_match(
                vPrepared, self.filters_bar.match_combo.currentData()
            )

            # Les annonces d'une même offre sont regroupées en une seule ligne.
            vPrepared = group_offers(vPrepared, get_decisions(self.database_file))
            add_freshness(vPrepared, datetime.now())
            add_estimated_salaries(self.database_file, vPrepared)

            if self.filters_bar.multiple_check.isChecked():
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

    def set_current_status(self, pStatus):
        """Donne un statut à l'offre choisie, puis reste sur la même ligne.

        Une offre ignorée disparaît de la liste : la ligne suivante est alors
        choisie, pour trier les offres d'affilée au clavier.
        """
        vOffer = self.detail_panel.offer

        if vOffer is None:
            return

        vRow = self.table.currentIndex().row()

        try:
            save_application(
                self.database_file, vOffer["source"], vOffer["source_id"], pStatus
            )

        except Exception:
            logger.exception("Statut non enregistré depuis le clavier")
            return

        self.refresh()

        vRowCount = self.proxy.rowCount()

        if vRowCount:
            self.table.selectRow(min(max(vRow, 0), vRowCount - 1))

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
