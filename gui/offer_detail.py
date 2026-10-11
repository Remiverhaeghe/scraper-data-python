"""Panneau de détail d'une offre et de son suivi de candidature"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs import show_preparation, show_text_dialog
from gui.theme import COLORS
from gui.widgets import (
    align_spin_box,
    create_button,
    create_card,
    create_icon_label,
)
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.company_info import lookup_company, summarize_company
from job.companies import (
    add_company_rule,
    describe_company_applications,
    find_company_applications,
)
from job.deduplication import COMPARED_FIELDS, MERGED, SEPARATE, get_offer_group
from job.preparation import prepare_application
from job.presentation import (
    AVAILABILITY_LABELS,
    AVAILABILITY_MESSAGES,
    STATUS_LABELS,
    format_date,
    format_net_salary,
    prepare_offer,
    safe_url,
)
from job.profile import is_profile_empty, load_profile
from job.settings import load_settings
from storage.job_applications import (
    delete_application,
    get_application,
    record_follow_up,
    save_application,
)
from storage.attachments import (
    ALLOWED_EXTENSIONS,
    add_attachment,
    delete_attachment,
    get_attachment,
    get_attachments,
)
from storage.duplicates import save_decision
from storage.job_offers import FOLLOW_UP_STATUSES, set_availability
from utils.link_checker import check_offer_link
from utils.logger import get_logger

logger = get_logger(__name__)

# Clé, libellé et icône des informations affichées sous le titre de l'offre
# Au-delà, une liste déborderait du panneau de largeur fixe : le reste est en infobulle.
MAX_LIST_VALUES = 4

INFO_ROWS = (
    ("location", "Lieu", "map-pin"),
    ("contract", "Contrat", "file-text"),
    ("salary", "Net mensuel", "banknote"),
    ("salary_label", "Salaire annoncé", "tag"),
    ("remote", "Télétravail", "house"),
    ("benefits", "Avantages", "gift"),
    ("experience_level", "Expérience", "timer"),
    ("skills", "Compétences", "list-checks"),
    ("published_at", "Publiée le", "calendar"),
    ("first_seen_at", "Découverte le", "search"),
    ("expires_at", "Date limite", "calendar"),
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


def summarize_values(pValues, pLimit=MAX_LIST_VALUES):
    """Résume une liste en ses premières valeurs suivies du nombre restant."""

    vValues = list(pValues or [])

    rText = ", ".join(vValues[:pLimit])

    if len(vValues) > pLimit:
        rText += f" +{len(vValues) - pLimit}"

    return rText


def describe_availability(pOffer):
    """Résume la disponibilité connue d'une offre, sous le bouton de vérification."""

    rText = ""

    if pOffer.get("availability_checked_at"):
        rText = (
            f"Vérifiée le {format_date(pOffer['availability_checked_at'])} : "
            f"{AVAILABILITY_LABELS[pOffer['availability']]}"
        )
    elif pOffer.get("is_expired"):
        rText = "Probablement expirée : plus vue dans les recherches récentes."

    return rText


def describe_companies_html(pCompanies):
    """Présente les entreprises trouvées, avec le lien vers leur fiche officielle."""

    vItems = []

    for vCompany in pCompanies:
        # Textes reçus d'un service extérieur : échappés avant d'être affichés en HTML.
        vLink = (
            f"<br><a href='{escape(vCompany['url'])}'>Fiche sur l'Annuaire des "
            "entreprises</a>"
            if vCompany["url"]
            else ""
        )
        vItems.append(
            f"<li><b>{escape(vCompany['name'])}</b><br>"
            f"{escape(summarize_company(vCompany).split(' : ', 1)[-1])}{vLink}</li>"
        )

    rHtml = (
        "<p>Plusieurs sociétés portent souvent le même nom (groupe, filiales) : "
        "vérifiez la bonne avant l'entretien.</p>"
        f"<ul>{''.join(vItems)}</ul>"
    )

    return rHtml


def describe_duplicates(pGroup):
    """Décrit en HTML les annonces d'une offre, valeurs différentes en orange."""

    vRows = []

    for vOffer in pGroup["offers"]:
        vCells = []

        for vField, vLabel in COMPARED_FIELDS:
            vValue = vOffer.get(vField)

            if vField == "remote" and vValue is not None:
                vValue = "télétravail" if vValue else "sur site"

            if vValue:
                vText = escape(str(vValue))

                if vLabel in pGroup["differences"]:
                    vText = f"<span style='color: {COLORS['warning']}'>{vText}</span>"

                vCells.append(vText)

        vSource = escape(vOffer.get("source_label") or vOffer.get("source") or "")
        vRows.append(f"<b>{vSource}</b> : {' · '.join(vCells)}")

    vDecision = {MERGED: "Fusionnées.", SEPARATE: "Gardées séparées."}.get(
        pGroup["decision"], "Différences à valider." if pGroup["differences"] else ""
    )

    rHtml = "<br>".join(vRows) + (f"<br><i>{vDecision}</i>" if vDecision else "")

    return rHtml


class OfferDetailPanel(QWidget):
    """Affiche une offre et permet de mettre à jour son suivi."""

    application_changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit le panneau, vide tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None
        self.attachments_list = None
        self.company_summary = None

        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.title_label.setWordWrap(True)

        self.company_label = QLabel()
        self.company_label.setObjectName("pageSubtitle")
        self.company_label.setWordWrap(True)

        # Avertissement si une candidature a déjà été envoyée à cette entreprise
        self.company_warning = QLabel()
        self.company_warning.setObjectName("companyWarning")
        self.company_warning.setWordWrap(True)
        self.company_warning.hide()

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
        vSummary.addWidget(self.company_warning)
        vSummary.addLayout(self.create_company_row())
        vSummary.addWidget(self.open_button)
        vSummary.addLayout(self.create_availability_row())
        vSummary.addWidget(self.create_duplicates_group())
        vSummary.addSpacing(6)
        vSummary.addLayout(vInfos)
        vSummary.addStretch()

        vApplicationGroup = self.create_application_group()
        vApplicationGroup.setFixedWidth(340)

        vContent = QWidget()

        vContentLayout = QHBoxLayout(vContent)
        vContentLayout.setContentsMargins(0, 12, 0, 0)
        vContentLayout.setSpacing(16)
        # Le résumé défile s'il manque de hauteur : sans cela, sa hauteur minimale
        # écraserait le tableau des offres au-dessus.
        vSummaryScroll = QScrollArea()
        vSummaryScroll.setWidget(vSummaryWidget)
        vSummaryScroll.setWidgetResizable(True)
        vSummaryScroll.setFixedWidth(360)
        vSummaryScroll.setFrameShape(QFrame.Shape.NoFrame)
        vSummaryScroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        vContentLayout.addWidget(vSummaryScroll)
        vContentLayout.addWidget(vDescriptionCard, 1)
        vContentLayout.addWidget(vApplicationGroup)

        # Page 0 : aucune offre choisie, page 1 : détail de l'offre
        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_empty_state())
        self.stack.addWidget(vContent)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(self.stack)

    def create_company_row(self):
        """Construit les boutons qui excluent ou privilégient l'entreprise de l'offre."""
        self.company_buttons = {}

        rLayout = QHBoxLayout()
        rLayout.setSpacing(12)

        for vKind, vText in (("preferred", "Privilégier"), ("excluded", "Exclure")):
            vButton = QPushButton(f"{vText} l'entreprise")
            vButton.setObjectName("linkButton")
            vButton.clicked.connect(
                lambda pChecked=False, pKind=vKind: self.set_company_rule(pKind)
            )

            self.company_buttons[vKind] = vButton
            rLayout.addWidget(vButton)

        rLayout.addStretch()

        return rLayout

    def set_company_rule(self, pKind):
        """Range l'entreprise de l'offre dans une liste, après confirmation pour l'exclusion."""
        vCompany = self.offer.get("company")

        if pKind == "excluded":
            vAnswer = QMessageBox.question(
                self,
                "Exclure l'entreprise",
                f"Masquer toutes les offres de « {vCompany} » ? La liste se modifie "
                "dans les Paramètres.",
            )

            if vAnswer != QMessageBox.StandardButton.Yes:
                return

        try:
            add_company_rule(self.database_file, vCompany, pKind)

        except Exception:
            logger.exception("Échec de l'enregistrement de la liste d'entreprises")

            QMessageBox.warning(
                self, "Entreprise", "La liste d'entreprises n'a pas pu être modifiée."
            )

        else:
            # La liste des offres se recharge : une entreprise exclue en disparaît.
            self.application_changed.emit()

    def show_company(self, pOffer):
        """Affiche l'avertissement de candidature déjà envoyée et l'état de l'entreprise."""
        vHasCompany = bool(pOffer.get("company"))

        self.company_summary = None
        self.assistant_label.clear()
        self.company_info_button.setEnabled(vHasCompany)
        vText = None

        if pOffer and vHasCompany:
            try:
                vText = describe_company_applications(
                    find_company_applications(self.database_file, pOffer)
                )

            except Exception:
                logger.exception("Impossible de lire les candidatures de l'entreprise")

        self.company_warning.setText(vText or "")
        self.company_warning.setVisible(vText is not None)

        vPreferred = bool(pOffer.get("company_preferred"))

        self.company_buttons["preferred"].setVisible(vHasCompany and not vPreferred)
        self.company_buttons["excluded"].setVisible(vHasCompany)

    def create_availability_row(self):
        """Construit la vérification du lien et son résultat."""
        self.availability_button = create_button(
            "Vérifier la disponibilité", "circle-check", pIconColor=COLORS["primary"]
        )
        self.availability_button.clicked.connect(self.check_availability)

        self.availability_label = QLabel()
        self.availability_label.setObjectName("cardSubtitle")
        self.availability_label.setWordWrap(True)

        self.prepare_button = create_button(
            "Préparer ma candidature", "sparkles", pIconColor=COLORS["primary"]
        )
        self.prepare_button.clicked.connect(self.open_preparation)

        # Demandes à coller dans ChatGPT : aucune API payante n'est appelée.
        self.chatgpt_button = create_button(
            "Préparer avec ChatGPT", "send", pIconColor=COLORS["primary"]
        )
        self.chatgpt_button.setToolTip(
            "Copie une demande complète et ouvre ChatGPT : collez-la avec Ctrl+V"
        )

        vMenu = QMenu(self.chatgpt_button)

        for vKind, vLabel in PROMPT_KINDS.items():
            vMenu.addAction(vLabel, lambda pKind=vKind: self.copy_prompt(pKind))

        self.chatgpt_button.setMenu(vMenu)

        self.company_info_button = create_button(
            "Infos sur l'entreprise", "globe", pIconColor=COLORS["primary"]
        )
        self.company_info_button.setToolTip(
            "Activité, taille et siège, depuis l'annuaire public des entreprises"
        )
        self.company_info_button.clicked.connect(self.show_company_info)

        self.assistant_label = QLabel()
        self.assistant_label.setObjectName("cardSubtitle")
        self.assistant_label.setWordWrap(True)

        rLayout = QVBoxLayout()
        rLayout.setSpacing(4)
        rLayout.addWidget(self.prepare_button)
        rLayout.addWidget(self.chatgpt_button)
        rLayout.addWidget(self.company_info_button)
        rLayout.addWidget(self.assistant_label)
        rLayout.addWidget(self.availability_button)
        rLayout.addWidget(self.availability_label)

        return rLayout

    def open_preparation(self):
        """Ouvre la préparation de candidature, ou invite à remplir le profil."""
        if self.offer is None:
            return

        vProfile = load_profile(self.database_file)

        if is_profile_empty(vProfile):
            QMessageBox.information(
                self,
                "Préparer ma candidature",
                "Renseignez d'abord vos compétences et expériences dans la page Profil.",
            )
        else:
            show_preparation(
                self,
                self.offer.get("title") or "offre",
                prepare_application(vProfile, self.offer),
            )

    def copy_prompt(self, pKind):
        """Copie une demande préparée pour ChatGPT puis ouvre le site."""
        vPrompt = build_prompts(
            load_profile(self.database_file), self.offer, self.company_summary
        )[pKind]

        QApplication.clipboard().setText(vPrompt)
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        self.assistant_label.setText(
            f"Demande « {PROMPT_KINDS[pKind]} » copiée : collez-la dans ChatGPT "
            "(Ctrl+V) et relisez-la avant de l'envoyer."
        )

        logger.info("Demande ChatGPT copiée : %s", pKind)

    def show_company_info(self):
        """Affiche les entreprises trouvées dans l'annuaire public sous ce nom."""
        vCompanyName = self.offer.get("company")

        vCompanies = None
        vMessage = None

        # Requête courte mais bloquante : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vCompanies = lookup_company(vCompanyName)

        except ValueError as vException:
            vMessage = str(vException)

        finally:
            QApplication.restoreOverrideCursor()

        if vCompanies is None:
            QMessageBox.warning(self, "Infos sur l'entreprise", vMessage)

        elif not vCompanies:
            QMessageBox.information(
                self,
                "Infos sur l'entreprise",
                f"Aucune entreprise française trouvée sous le nom « {vCompanyName} ».",
            )

        else:
            # Les résultats possibles sont repris dans la demande « Comprendre
            # l'entreprise » : ChatGPT peut reconnaître la bonne société.
            self.company_summary = " ; ".join(
                summarize_company(vCompany) for vCompany in vCompanies
            )
            show_text_dialog(
                self,
                f"Entreprises trouvées pour « {vCompanyName} »",
                pHtml=describe_companies_html(vCompanies),
            )

    def check_availability(self):
        """Vérifie le lien de l'offre et enregistre un résultat net."""
        if self.offer is None:
            return

        # Requête courte mais bloquante : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vAvailability = check_offer_link(self.offer.get("url") or "")

            if vAvailability is not None:
                set_availability(
                    self.database_file,
                    self.offer["source"],
                    self.offer["source_id"],
                    vAvailability,
                    datetime.now(),
                )
                self.offer["availability"] = vAvailability

        finally:
            QApplication.restoreOverrideCursor()

        self.availability_label.setText(AVAILABILITY_MESSAGES[vAvailability])

    def create_duplicates_group(self):
        """Construit la comparaison des annonces d'une offre publiée plusieurs fois."""
        self.duplicates_label = QLabel()
        self.duplicates_label.setObjectName("cardSubtitle")
        self.duplicates_label.setWordWrap(True)
        self.duplicates_label.setTextFormat(Qt.TextFormat.RichText)

        vMergeButton = create_button("Fusionner", "circle-check")
        vMergeButton.setToolTip("Une seule offre, malgré les différences")
        vMergeButton.clicked.connect(lambda: self.decide_duplicates(MERGED))

        vSeparateButton = create_button("Garder séparées")
        vSeparateButton.clicked.connect(lambda: self.decide_duplicates(SEPARATE))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vMergeButton)
        vButtons.addWidget(vSeparateButton)

        self.duplicates_group = QGroupBox("Annonces de cette offre")

        vLayout = QVBoxLayout(self.duplicates_group)
        vLayout.addWidget(self.duplicates_label)
        vLayout.addLayout(vButtons)

        self.duplicates_group.hide()

        return self.duplicates_group

    def show_duplicates(self, pOffer):
        """Affiche les annonces d'une offre et leurs différences, s'il y en a plusieurs."""
        vGroup = get_offer_group(
            self.database_file,
            pOffer,
            lambda pItem: prepare_offer(pItem, datetime.now()),
        )

        vHasDuplicates = len(vGroup["offers"]) > 1

        self.duplicates_group.setVisible(vHasDuplicates)
        self.duplicates_label.setText(
            describe_duplicates(vGroup) if vHasDuplicates else ""
        )

    def decide_duplicates(self, pDecision):
        """Enregistre la fusion ou la séparation, puis recharge la liste."""
        if self.offer is not None and self.offer.get("fingerprint"):
            save_decision(
                self.database_file, self.offer["fingerprint"], pDecision, datetime.now()
            )
            self.application_changed.emit()

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

        self.follow_up_edit = align_spin_box(QDateEdit())
        self.follow_up_edit.setCalendarPopup(True)
        self.follow_up_edit.setDisplayFormat("dd/MM/yyyy")
        self.follow_up_edit.calendarWidget().setMinimumSize(320, 240)

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
        vLayout.addLayout(self.create_attachments_row())

        return rGroup

    def create_attachments_row(self):
        """Construit la liste des pièces jointes et ses boutons."""
        vTitle = QLabel("Pièces jointes")
        vTitle.setObjectName("fieldLabel")

        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(90)
        self.attachments_list.setToolTip("Double-clic pour ouvrir le fichier")
        self.attachments_list.itemDoubleClicked.connect(self.open_attachment)

        vAddButton = QPushButton("Joindre un fichier…")
        vAddButton.setObjectName("linkButton")
        vAddButton.setToolTip(
            "CV envoyé, lettre : " + ", ".join(ALLOWED_EXTENSIONS) + ", 10 Mo maximum"
        )
        vAddButton.clicked.connect(self.add_attachment)

        vDeleteButton = QPushButton("Supprimer")
        vDeleteButton.setObjectName("linkButton")
        vDeleteButton.clicked.connect(self.delete_attachment)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vAddButton)
        vButtons.addWidget(vDeleteButton)
        vButtons.addStretch()

        rLayout = QVBoxLayout()
        rLayout.setSpacing(4)
        rLayout.addWidget(vTitle)
        rLayout.addWidget(self.attachments_list)
        rLayout.addLayout(vButtons)

        return rLayout

    def load_attachments(self):
        """Affiche les pièces jointes de l'offre."""
        self.attachments_list.clear()

        if self.offer is None:
            return

        try:
            vAttachments = get_attachments(
                self.database_file, self.offer["source"], self.offer["source_id"]
            )

        except Exception:
            logger.exception("Impossible de lire les pièces jointes")
            vAttachments = []

        for vAttachment in vAttachments:
            vItem = QListWidgetItem(
                f"{vAttachment['file_name']} · {format_date(vAttachment['added_at'])}"
            )
            vItem.setData(Qt.ItemDataRole.UserRole, vAttachment["id"])
            self.attachments_list.addItem(vItem)

    def add_attachment(self):
        """Joint un fichier choisi sur le disque à l'offre affichée."""
        vFilter = " ".join(f"*{vExtension}" for vExtension in ALLOWED_EXTENSIONS)

        vPath, _ = QFileDialog.getOpenFileName(
            self, "Joindre un fichier", str(Path.home()), f"Documents ({vFilter})"
        )

        if vPath:
            self.attach_file(vPath)

    def attach_file(self, pPath):
        """Range le fichier avec l'offre, ou explique pourquoi il est refusé."""
        try:
            add_attachment(
                self.database_file,
                self.offer["source"],
                self.offer["source_id"],
                Path(pPath).name,
                Path(pPath).read_bytes(),
                datetime.now(),
            )

        except ValueError as vException:
            QMessageBox.warning(self, "Pièce jointe refusée", str(vException))

        except Exception:
            logger.exception("Échec de l'ajout de la pièce jointe")

            QMessageBox.warning(
                self, "Pièce jointe", "Le fichier n'a pas pu être joint."
            )

        self.load_attachments()

    def open_attachment(self, pItem):
        """Ouvre une pièce jointe avec l'application associée à son type."""
        vAttachment = get_attachment(
            self.database_file, pItem.data(Qt.ItemDataRole.UserRole)
        )

        if vAttachment is not None and vAttachment["path"].exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(vAttachment["path"])))
        else:
            QMessageBox.warning(self, "Pièce jointe", "Le fichier est introuvable.")

    def delete_attachment(self):
        """Supprime la pièce jointe sélectionnée, après confirmation."""
        vItem = self.attachments_list.currentItem()

        if vItem is None:
            return

        vAnswer = QMessageBox.question(
            self, "Supprimer la pièce jointe", f"Supprimer « {vItem.text()} » ?"
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            delete_attachment(self.database_file, vItem.data(Qt.ItemDataRole.UserRole))
            self.load_attachments()

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
        self.availability_button.setEnabled(safe_url(vOffer.get("url")) != "#")
        self.availability_label.setText(describe_availability(vOffer))
        self.show_duplicates(vOffer)
        self.show_company(vOffer)

        vRemote = vOffer.get("remote")

        vInfos = {
            "location": vOffer.get("location"),
            "contract": vOffer.get("contract"),
            "salary": format_net_salary(vOffer),
            "salary_label": vOffer.get("salary_label"),
            "remote": None if vRemote is None else ("Oui" if vRemote else "Non"),
            "benefits": summarize_values(vOffer.get("benefits")),
            "experience_level": vOffer.get("experience_level"),
            "skills": summarize_values(vOffer.get("skills_list")),
            "published_at": format_date(vOffer.get("published_at")),
            "first_seen_at": format_date(vOffer.get("first_seen_at")),
            "expires_at": format_date(vOffer.get("expires_at")),
            "source_label": vOffer.get("source_label"),
        }

        # Une information absente est masquée plutôt qu'affichée « Non renseigné ».
        vFullLists = {
            "benefits": ", ".join(vOffer.get("benefits") or []),
            "skills": ", ".join(vOffer.get("skills_list") or []),
        }

        for vKey, (vRow, vValue) in self.info_rows.items():
            vValue.setText(str(vInfos[vKey] or ""))
            vValue.setToolTip(vFullLists.get(vKey, ""))
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
        self.load_attachments()

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
