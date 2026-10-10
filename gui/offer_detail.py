"""Panneau de détail d'une offre et de son suivi de candidature"""

from datetime import datetime

from PySide6.QtCore import QDate, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.offers_model import format_net_salary
from gui.theme import COLORS
from gui.widgets import create_button, create_card, create_icon_label
from job.presentation import STATUS_LABELS, format_date, safe_url
from job.settings import load_settings
from storage.job_applications import (
    delete_application,
    get_application,
    record_follow_up,
    save_application,
)
from storage.job_offers import FOLLOW_UP_STATUSES
from utils.logger import get_logger

logger = get_logger(__name__)

# Clé, libellé et icône des informations affichées sous le titre de l'offre
INFO_ROWS = (
    ("contract", "Contrat", "file-text"),
    ("salary", "Net mensuel", "banknote"),
    ("salary_label", "Salaire annoncé", "tag"),
    ("remote", "Télétravail", "house"),
    ("benefits", "Avantages", "gift"),
    ("published_at", "Publiée le", "calendar"),
    ("source_label", "Source", "globe"),
)

# Interligne de la description, en pourcentage de la hauteur d'une ligne
DESCRIPTION_LINE_HEIGHT = 145


def describe_application(pApplication):
    """Résume les dates de candidature et de relance."""

    vParts = []

    if pApplication and pApplication.get("applied_at"):
        vParts.append(
            f"Candidature envoyée le {format_date(pApplication['applied_at'])}."
        )

    if pApplication and pApplication.get("follow_up_count"):
        vParts.append(
            f"{pApplication['follow_up_count']} relance(s), la dernière le "
            f"{format_date(pApplication['last_follow_up_at'])}."
        )

    rDescription = " ".join(vParts)

    return rDescription


class OfferDetailPanel(QWidget):
    """Affiche une offre et permet de mettre à jour son suivi."""

    application_changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit le panneau, vide tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None

        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.title_label.setWordWrap(True)

        self.company_label = QLabel()
        self.company_label.setObjectName("pageSubtitle")
        self.company_label.setWordWrap(True)

        self.open_button = create_button(
            "Ouvrir l'offre", "external-link", "primaryButton", COLORS["on_primary"]
        )
        self.open_button.clicked.connect(self.open_offer)

        # Ligne et libellé de valeur de chaque information, masquée si elle est vide
        self.info_rows = {}

        vInfos = QVBoxLayout()
        vInfos.setSpacing(8)

        for vKey, vLabel, vIcon in INFO_ROWS:
            vRow, vValue = self.create_info_row(vLabel, vIcon)

            self.info_rows[vKey] = (vRow, vValue)
            vInfos.addWidget(vRow)

        self.description = QTextBrowser()
        self.description.setObjectName("descriptionText")
        self.description.setPlaceholderText("Aucune description fournie par la source.")

        vDescriptionCard, vDescriptionLayout = create_card("Description")
        vDescriptionLayout.addWidget(self.description, 1)

        vSummaryWidget = QFrame()
        vSummaryWidget.setObjectName("card")
        vSummaryWidget.setFixedWidth(340)

        vSummary = QVBoxLayout(vSummaryWidget)
        vSummary.setContentsMargins(18, 16, 18, 16)
        vSummary.addWidget(self.title_label)
        vSummary.addWidget(self.company_label)
        vSummary.addWidget(self.open_button)
        vSummary.addSpacing(6)
        vSummary.addLayout(vInfos)
        vSummary.addStretch()

        vApplicationGroup = self.create_application_group()
        vApplicationGroup.setFixedWidth(340)

        vContent = QWidget()

        vContentLayout = QHBoxLayout(vContent)
        vContentLayout.setContentsMargins(0, 12, 0, 0)
        vContentLayout.setSpacing(16)
        vContentLayout.addWidget(vSummaryWidget)
        vContentLayout.addWidget(vDescriptionCard, 1)
        vContentLayout.addWidget(vApplicationGroup)

        # Page 0 : aucune offre choisie, page 1 : détail de l'offre
        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_empty_state())
        self.stack.addWidget(vContent)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(self.stack)

    def create_info_row(self, pLabel, pIcon):
        """Crée une ligne icône, libellé et valeur ; retourne la ligne et sa valeur."""
        vName = QLabel(pLabel)
        vName.setObjectName("cardSubtitle")
        vName.setFixedWidth(110)

        vValue = QLabel()
        vValue.setWordWrap(True)

        rRow = QWidget()

        vLayout = QHBoxLayout(rRow)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(10)
        vLayout.addWidget(create_icon_label(pIcon, COLORS["primary"], 16))
        vLayout.addWidget(vName)
        vLayout.addWidget(vValue, 1)

        rRowAndValue = (rRow, vValue)

        return rRowAndValue

    def create_empty_state(self):
        """Construit le message affiché tant qu'aucune offre n'est sélectionnée."""
        vText = QLabel(
            "Aucune offre ne correspond aux filtres, ou aucune n'est sélectionnée."
        )
        vText.setObjectName("cardSubtitle")

        rCard, vLayout = create_card()
        vLayout.addStretch()
        vLayout.addWidget(
            create_icon_label("inbox", COLORS["muted"], 36),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        vLayout.addWidget(vText, 0, Qt.AlignmentFlag.AlignCenter)
        vLayout.addStretch()

        return rCard

    def create_application_group(self):
        """Construit le formulaire de suivi de candidature."""
        self.status_combo = QComboBox()
        self.status_combo.addItem("Aucun suivi", None)

        for vStatus, vLabel in STATUS_LABELS.items():
            self.status_combo.addItem(vLabel, vStatus)

        self.follow_up_check = QCheckBox("Relance prévue le")

        self.follow_up_edit = QDateEdit()
        self.follow_up_edit.setCalendarPopup(True)
        self.follow_up_edit.setDisplayFormat("dd/MM/yyyy")

        self.follow_up_check.toggled.connect(self.follow_up_edit.setEnabled)

        vFollowUp = QHBoxLayout()
        vFollowUp.addWidget(self.follow_up_check)
        vFollowUp.addWidget(self.follow_up_edit)
        vFollowUp.addStretch()

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Notes")

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.follow_up_button = QPushButton("J'ai relancé aujourd'hui")
        self.follow_up_button.clicked.connect(self.add_follow_up)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vSaveButton)
        vButtons.addWidget(self.follow_up_button)
        vButtons.addStretch()

        self.application_label = QLabel()
        self.application_label.setObjectName("pageSubtitle")
        self.application_label.setWordWrap(True)

        rGroup = QGroupBox("Suivi")

        vLayout = QVBoxLayout(rGroup)
        vLayout.addWidget(self.status_combo)
        vLayout.addLayout(vFollowUp)
        vLayout.addWidget(self.notes_edit)
        vLayout.addLayout(vButtons)
        vLayout.addWidget(self.application_label)

        return rGroup

    def show_offer(self, pOffer):
        """Affiche une offre préparée par prepare_offer, ou vide le panneau."""
        self.offer = pOffer
        self.stack.setCurrentIndex(0 if pOffer is None else 1)

        vOffer = pOffer or {}

        self.title_label.setText(
            vOffer.get("title") or "Titre non communiqué par la source"
        )
        self.company_label.setText(
            " · ".join(
                vValue
                for vValue in (vOffer.get("company"), vOffer.get("location"))
                if vValue
            )
        )
        self.open_button.setEnabled(safe_url(vOffer.get("url")) != "#")

        vRemote = vOffer.get("remote")

        vInfos = {
            "contract": vOffer.get("contract"),
            "salary": format_net_salary(vOffer),
            "salary_label": vOffer.get("salary_label"),
            "remote": None if vRemote is None else ("Oui" if vRemote else "Non"),
            "benefits": ", ".join(vOffer.get("benefits") or []),
            "published_at": format_date(vOffer.get("published_at")),
            "source_label": vOffer.get("source_label"),
        }

        # Une information absente est masquée plutôt qu'affichée « Non renseigné ».
        for vKey, (vRow, vValue) in self.info_rows.items():
            vValue.setText(str(vInfos[vKey] or ""))
            vRow.setVisible(bool(vInfos[vKey]))

        self.show_description(vOffer.get("description"))

        self.load_application()

    def show_description(self, pDescription):
        """Affiche la description en texte brut, avec un interligne aéré."""
        # Texte brut : une description ne doit jamais être interprétée en HTML.
        self.description.setPlainText(pDescription or "")

        vFormat = QTextBlockFormat()
        vFormat.setLineHeight(
            DESCRIPTION_LINE_HEIGHT,
            QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
        )
        vFormat.setBottomMargin(8)

        vCursor = QTextCursor(self.description.document())
        vCursor.select(QTextCursor.SelectionType.Document)
        vCursor.setBlockFormat(vFormat)

    def load_application(self):
        """Remplit le formulaire de suivi à partir de la base."""
        vApplication = None

        if self.offer is not None:
            vApplication = get_application(
                self.database_file, self.offer["source"], self.offer["source_id"]
            )

        vApplication = vApplication or {}

        self.status_combo.setCurrentIndex(
            max(self.status_combo.findData(vApplication.get("status")), 0)
        )

        vFollowUpDate = vApplication.get("follow_up_date")

        self.follow_up_check.setChecked(bool(vFollowUpDate))
        self.follow_up_edit.setEnabled(bool(vFollowUpDate))
        self.follow_up_edit.setDate(
            QDate.fromString(vFollowUpDate[:10], "yyyy-MM-dd")
            if vFollowUpDate
            else QDate.currentDate().addDays(self.get_follow_up_days())
        )

        self.notes_edit.setPlainText(vApplication.get("notes") or "")
        self.follow_up_button.setVisible(
            vApplication.get("status") in FOLLOW_UP_STATUSES
        )
        self.application_label.setText(describe_application(vApplication))

    def get_follow_up_days(self):
        """Retourne le délai de relance défini dans les paramètres."""
        rDays = load_settings(self.database_file)["follow_up_days"]

        return rDays

    def get_follow_up_date(self):
        """Retourne la date de relance saisie, ou None si aucune n'est prévue."""
        rDate = None

        if self.follow_up_check.isChecked():
            vDate = self.follow_up_edit.date()
            rDate = datetime(vDate.year(), vDate.month(), vDate.day())

        return rDate

    def save(self):
        """Enregistre le suivi, ou le supprime si aucun statut n'est choisi."""
        vStatus = self.status_combo.currentData()
        vSource = self.offer["source"]
        vSourceId = self.offer["source_id"]

        try:
            if vStatus is None:
                delete_application(self.database_file, vSource, vSourceId)
            else:
                save_application(
                    self.database_file,
                    vSource,
                    vSourceId,
                    vStatus,
                    pFollowUpDate=self.get_follow_up_date(),
                    pNotes=self.notes_edit.toPlainText().strip(),
                    pFollowUpDays=self.get_follow_up_days(),
                )

        except Exception:
            logger.exception(
                "Échec de l'enregistrement du suivi %s %s", vSource, vSourceId
            )

            self.application_label.setText("Le suivi n'a pas pu être enregistré.")

        else:
            self.load_application()
            self.application_changed.emit()

    def add_follow_up(self):
        """Enregistre une relance faite aujourd'hui et programme la suivante."""
        record_follow_up(
            self.database_file,
            self.offer["source"],
            self.offer["source_id"],
            pFollowUpDays=self.get_follow_up_days(),
        )

        self.load_application()
        self.application_changed.emit()

    def open_offer(self):
        """Ouvre l'offre dans le navigateur, uniquement en http ou https."""
        vUrl = safe_url(self.offer.get("url") if self.offer else None)

        if vUrl != "#":
            QDesktopServices.openUrl(QUrl(vUrl))
