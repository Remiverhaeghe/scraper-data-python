"""Page Certifications : celles que demandent les offres, celles du candidat"""

from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.certification_dialog import CertificationDialog
from gui.theme import ACCENTS, COLORS
from gui.widgets import (
    StatisticCard,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.certifications import CATEGORIES, build_overview, save_owned
from job.statistics import load_scored_offers
from utils.logger import get_logger

logger = get_logger(__name__)

COLUMNS = (
    "Certification",
    "Offres proches",
    "Toutes offres",
    "Durée et coût",
    "Validité",
    "Je l'ai",
    "Mon suivi",
)
OWNED_COLUMN = COLUMNS.index("Je l'ai")

# Au-delà, le texte est abrégé : le tableau tient dans la fenêtre sans défiler.
MAX_COLUMN_WIDTH = 280
NAME_COLUMN_WIDTH = 300

# Échéance d'une certification à renouveler, dans le rappel du plan
RENEWAL_TEXTS = {"soon": "avant le", "expired": "expirée le"}

STATUS_TEXTS = {
    "valid": ("Valide jusqu'au", "green"),
    "soon": ("À renouveler avant le", "amber"),
    "expired": ("Expirée le", None),
}


def format_iso_date(pValue):
    """Retourne une date ISO au format jj/mm/aaaa, ou une chaîne vide."""

    rText = date.fromisoformat(pValue).strftime("%d/%m/%Y") if pValue else ""

    return rText


def describe_follow_up(pRow):
    """Retourne le suivi d'une certification : obtention, validité et documents."""

    vParts = []

    # L'échéance compte davantage que la date d'obtention, reprise en infobulle.
    if pRow["obtained"] and not pRow["valid_until"]:
        vParts.append(f"Obtenue le {format_iso_date(pRow['obtained'])}")

    if pRow["status"] and pRow["valid_until"]:
        vParts.append(
            f"{STATUS_TEXTS[pRow['status']][0]} "
            f"{format_iso_date(pRow['valid_until'])}"
        )

    if pRow["documents"]:
        vParts.append(
            f"{pRow['documents']} document{'s' if pRow['documents'] > 1 else ''}"
        )

    rText = " · ".join(vParts)

    return rText


def describe_validity_months(pMonths):
    """Retourne la validité en clair : années ou mois, ou sans limite."""

    if pMonths is None:
        rText = "Sans limite fixée"
    elif pMonths % 12 == 0:
        rText = f"{pMonths // 12} an{'s' if pMonths > 12 else ''}"
    else:
        rText = f"{pMonths} mois"

    return rText


def get_status_color(pAccent):
    """Retourne la couleur d'un état : l'accent donné, ou la couleur d'alerte."""

    rColor = QColor(ACCENTS[pAccent][0] if pAccent else COLORS["danger"])

    return rColor


class CertificationsPage(QWidget):
    """Classe les certifications selon les offres et suit celles du candidat."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh la remplit."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.rows = []
        self.filling = False

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Certifications",
            "Celles que demandent vos offres, celles que vous avez et leur validité",
            pIcon="award",
        )

        self.cards = {
            "citing": StatisticCard(
                "Offres proches qui en citent", "briefcase", "blue"
            ),
            "covered_before": StatisticCard(
                "Couvertes aujourd'hui (%)", "circle-check", "green"
            ),
            "covered_after": StatisticCard(
                "Avec le plan conseillé (%)", "target", "purple"
            ),
        }
        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.cards.values():
            vCards.addWidget(vCard)

        vPlanCard, vPlanLayout = create_card(
            "Plan conseillé",
            "Les certifications qui couvriraient le plus d'offres proches de votre profil",
            pIcon="target",
            pOpen=True,
        )
        self.plan_label = QLabel()
        self.plan_label.setWordWrap(True)
        self.renewal_label = QLabel()
        self.renewal_label.setWordWrap(True)
        vPlanLayout.addWidget(self.plan_label)
        vPlanLayout.addWidget(self.renewal_label)

        vTableCard, vTableLayout = create_card(
            "Toutes les certifications",
            "Double-cliquez sur une certification pour saisir l'organisme, le numéro, "
            "joindre le certificat ou ouvrir sa fiche. Durées et coûts sont des "
            "ordres de grandeur : la fiche de l'organisme fait foi.",
            pIcon="list-checks",
            pOpen=True,
        )
        self.category_combo = QComboBox()
        self.category_combo.addItem("Toutes les catégories", None)

        for vCategory in CATEGORIES:
            self.category_combo.addItem(vCategory, vCategory)

        self.category_combo.currentIndexChanged.connect(self.fill_table)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(520)
        self.table.cellDoubleClicked.connect(self.open_details)
        self.table.itemChanged.connect(self.toggle_owned)

        vFilters = QHBoxLayout()
        vFilters.addWidget(self.category_combo)
        vFilters.addWidget(self.message_label, 1)
        vTableLayout.addLayout(vFilters)
        vTableLayout.addWidget(self.table)

        vLayout.addLayout(vCards)
        vLayout.addWidget(vPlanCard)
        vLayout.addWidget(vTableCard, 1)

    def refresh(self):
        """Relit les offres notées et recalcule les certifications."""
        try:
            vOffers = load_scored_offers(self.database_file, datetime.now())
            vOverview = build_overview(self.database_file, vOffers, date.today())

        except Exception:
            logger.exception("Certifications non calculées")
            show_message(
                self.message_label,
                "Les certifications n'ont pas pu être calculées.",
                "danger",
            )
            return

        self.rows = vOverview["rows"]

        for vKey, vCard in self.cards.items():
            vCard.set_value(vOverview[vKey])

        self.plan_label.setText(
            "En passant "
            + ", puis ".join(vOverview["plan_labels"])
            + f", vous couvririez {vOverview['covered_after']} % des offres proches qui "
            "citent une certification."
            if vOverview["plan_labels"]
            else "Aucune certification à conseiller pour vos offres proches : "
            "complétez votre profil ou lancez une recherche."
        )

        vRenewals = [
            vRow for vRow in self.rows if vRow["status"] in ("soon", "expired")
        ]
        self.renewal_label.setText(
            "À renouveler : "
            + ", ".join(
                f"{vRow['label']} ({RENEWAL_TEXTS[vRow['status']]} "
                f"{format_iso_date(vRow['valid_until'])})"
                for vRow in vRenewals
            )
            if vRenewals
            else ""
        )
        self.renewal_label.setVisible(bool(vRenewals))
        self.fill_table()

    def fill_table(self):
        """Affiche les certifications de la catégorie choisie."""
        vCategory = self.category_combo.currentData()
        vRows = [vRow for vRow in self.rows if vCategory in (None, vRow["category"])]

        self.filling = True
        self.table.setRowCount(len(vRows))

        for vIndex, vRow in enumerate(vRows):
            vName = QTableWidgetItem(vRow["label"])
            vName.setData(Qt.ItemDataRole.UserRole, vRow)
            vName.setToolTip(
                f"{vRow['advice']}\n{vRow['funding']}\n"
                "Double-clic : informations, documents et fiche de l'organisme"
            )

            vOwned = QTableWidgetItem()
            vOwned.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            vOwned.setCheckState(
                Qt.CheckState.Checked if vRow["obtained"] else Qt.CheckState.Unchecked
            )

            vEffort = QTableWidgetItem(f"{vRow['duration']} · {vRow['cost']}")
            vEffort.setToolTip(vEffort.text())

            vStatus = QTableWidgetItem(describe_follow_up(vRow))
            vStatus.setToolTip(
                f"Obtenue le {format_iso_date(vRow['obtained'])}"
                if vRow["obtained"]
                else ""
            )

            if vRow["status"]:
                vStatus.setForeground(get_status_color(STATUS_TEXTS[vRow["status"]][1]))

            for vColumn, vItem in enumerate(
                (
                    vName,
                    QTableWidgetItem(str(vRow["close_count"])),
                    QTableWidgetItem(str(vRow["count"])),
                    vEffort,
                    QTableWidgetItem(describe_validity_months(vRow["validity_months"])),
                    vOwned,
                    vStatus,
                )
            ):
                self.table.setItem(vIndex, vColumn, vItem)

        self.table.resizeColumnsToContents()

        for vColumn in range(len(COLUMNS) - 1):
            self.table.setColumnWidth(
                vColumn,
                min(
                    self.table.columnWidth(vColumn),
                    NAME_COLUMN_WIDTH if vColumn == 0 else MAX_COLUMN_WIDTH,
                ),
            )

        self.filling = False

    def get_row(self, pIndex):
        """Retourne la certification affichée à la ligne donnée."""
        rRow = self.table.item(pIndex, 0).data(Qt.ItemDataRole.UserRole)

        return rRow

    def toggle_owned(self, pItem):
        """Enregistre ou retire une certification quand sa case est cochée."""
        if self.filling or pItem.column() != OWNED_COLUMN:
            return

        vRow = self.get_row(pItem.row())
        vChecked = pItem.checkState() == Qt.CheckState.Checked

        save_owned(self.database_file, vRow["id"], date.today() if vChecked else None)
        show_message(
            self.message_label,
            (
                f"{vRow['label']} : ajoutée à votre profil. Double-cliquez pour préciser "
                "la date, l'organisme et joindre le certificat."
                if vChecked
                else f"{vRow['label']} : retirée de votre profil."
            ),
        )
        self.refresh()

    def open_details(self, pRow, _pColumn):
        """Ouvre la fenêtre de la certification, puis relit la page."""
        CertificationDialog(self.database_file, self.get_row(pRow), self).exec()

        # Les documents sont rangés dès leur ajout, même si la fenêtre est fermée.
        self.refresh()
