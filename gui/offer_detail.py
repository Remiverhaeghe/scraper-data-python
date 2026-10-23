"""Panneau de détail d'une offre : résumé, description, aide et suivi

Le panneau assemble trois parties autonomes : l'aide à la candidature
(gui/offer_assistant.py), le suivi (gui/offer_application.py) et ses pièces
jointes (gui/offer_attachments.py).
"""

from datetime import datetime
from html import escape

import threading

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.offer_application import ApplicationPanel
from gui.offer_assistant import OfferAssistantPanel
from gui.theme import COLORS
from gui.widgets import create_button, create_card, create_icon_label
from job.companies import (
    add_company_rule,
    describe_company_applications,
    find_company_applications,
)
from job.deduplication import COMPARED_FIELDS, MERGED, SEPARATE, get_offer_group
from job.geocoding import describe_location
from job.offer_details import can_fetch_description, fetch_missing_description
from job.salary_market import describe_market_salary, find_market_salary
from job.presentation import (
    build_translate_url,
    format_date,
    format_net_salary,
    prepare_offer,
    safe_url,
)
from job.translation import can_translate, translate_with_cache
from storage.duplicates import save_decision
from utils.logger import get_logger

logger = get_logger(__name__)

# Clé, libellé et icône des informations affichées sous le titre de l'offre
# Au-delà, une liste déborderait du panneau de largeur fixe : le reste est en infobulle.
MAX_LIST_VALUES = 4

TRANSLATE_TEXT = "Traduire en français"

# Place de la barre de défilement à côté d'une colonne de largeur fixe
COLUMN_SCROLL_MARGIN = 20

INFO_ROWS = (
    ("location", "Lieu", "map-pin"),
    ("contract", "Contrat", "file-text"),
    ("salary", "Net mensuel", "banknote"),
    ("salary_label", "Salaire annoncé", "tag"),
    ("market_salary", "Marché", "scale"),
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


def summarize_values(pValues, pLimit=MAX_LIST_VALUES):
    """Résume une liste en ses premières valeurs suivies du nombre restant."""

    vValues = list(pValues or [])

    rText = ", ".join(vValues[:pLimit])

    if len(vValues) > pLimit:
        rText += f" +{len(vValues) - pLimit}"

    return rText


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


def create_column_scroll(pColumn):
    """Place une colonne de la fiche dans une zone qui défile s'il manque de hauteur.

    Sans défilement, la hauteur minimale de la colonne écraserait le tableau des
    offres au-dessus, ou ses champs seraient tronqués.
    """

    rScroll = QScrollArea()
    rScroll.setWidget(pColumn)
    rScroll.setWidgetResizable(True)
    rScroll.setFixedWidth(pColumn.width() + COLUMN_SCROLL_MARGIN)
    rScroll.setFrameShape(QFrame.Shape.NoFrame)
    rScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    return rScroll


class OfferDetailPanel(QWidget):
    """Affiche une offre et rassemble son aide à la candidature et son suivi."""

    application_changed = Signal()
    exam_requested = Signal(dict)
    # Émis depuis le fil de traduction : (description d'origine, traduction, erreur)
    translation_done = Signal(str, object, object)
    # Émis depuis le fil de lecture : offre complétée de sa description
    description_fetched = Signal(object)

    def __init__(self, pDatabaseFile):
        """Construit le panneau, vide tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None

        self.assistant = OfferAssistantPanel(pDatabaseFile)
        self.assistant.exam_requested.connect(self.exam_requested)

        self.application = ApplicationPanel(pDatabaseFile)
        self.application.setFixedWidth(340)
        self.application.changed.connect(self.application_changed)

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

        # Une description étrangère se traduit sur place avec Argos ; sans lui,
        # elle s'ouvre dans Google Traduction, dans le navigateur.
        self.translate_url = None
        self.original_description = None
        self.translated = False
        self.translate_button = create_button(
            TRANSLATE_TEXT, "languages", pIconColor=COLORS["primary"]
        )
        self.translate_button.clicked.connect(self.toggle_translation)
        self.translate_button.hide()
        self.translation_done.connect(self.show_translation)
        self.description_fetched.connect(self.show_fetched_description)

        vDescriptionCard, vDescriptionLayout = create_card("Description", pOpen=True)
        vDescriptionLayout.addWidget(
            self.translate_button, 0, Qt.AlignmentFlag.AlignLeft
        )
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
        vSummary.addWidget(self.assistant)
        vSummary.addWidget(self.create_duplicates_group())
        vSummary.addSpacing(6)
        # Bloc centré sous les boutons, à la largeur de sa ligne la plus longue
        vInfosBlock = QWidget()
        vInfosBlock.setLayout(vInfos)
        vInfosBlock.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        vSummary.addWidget(vInfosBlock, 0, Qt.AlignmentFlag.AlignHCenter)
        vSummary.addStretch()

        vContent = QWidget()

        vContentLayout = QHBoxLayout(vContent)
        vContentLayout.setContentsMargins(0, 12, 0, 0)
        vContentLayout.setSpacing(16)
        vContentLayout.addWidget(create_column_scroll(vSummaryWidget))
        vContentLayout.addWidget(vDescriptionCard, 1)
        vContentLayout.addWidget(create_column_scroll(self.application))

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

        self.original_description = vOffer.get("description")
        self.translated = False
        self.translate_url = build_translate_url(self.original_description)
        self.translate_button.setVisible(self.translate_url is not None)
        self.translate_button.setEnabled(True)
        self.translate_button.setText(TRANSLATE_TEXT)
        self.translate_button.setToolTip(
            "Traduit la description sur cet ordinateur"
            if self.translate_url and can_translate(self.original_description)
            else "Ouvre la description dans Google Traduction, dans le navigateur"
        )
        self.show_duplicates(vOffer)
        self.show_company(vOffer)

        # Description absente pour une partie des offres SmartRecruiters : lue à
        # l'ouverture, hors du fil de l'interface.
        if can_fetch_description(vOffer):
            self.description.setPlaceholderText("Lecture de la description…")
            threading.Thread(
                target=lambda: self.description_fetched.emit(
                    fetch_missing_description(self.database_file, vOffer)
                ),
                daemon=True,
            ).start()
        else:
            self.description.setPlaceholderText(
                "Aucune description fournie par la source."
            )

        vRemote = vOffer.get("remote")

        vInfos = {
            "location": describe_location(vOffer),
            "contract": vOffer.get("contract"),
            "salary": format_net_salary(vOffer),
            "salary_label": vOffer.get("salary_label"),
            "market_salary": self.describe_market(vOffer),
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

        self.assistant.set_offer(pOffer)
        self.application.set_offer(pOffer)

    def describe_market(self, pOffer):
        """Résume le salaire des offres proches ; vide si le calcul échoue."""
        try:
            rText = describe_market_salary(
                find_market_salary(self.database_file, pOffer)
            )

        except Exception:
            logger.exception("Salaire du marché non calculé")
            rText = ""

        return rText

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

    def toggle_translation(self):
        """Traduit la description sur place, ou revient au texte d'origine."""
        vText = self.original_description

        if self.translated:
            self.translated = False
            self.show_description(vText)
            self.translate_button.setText(TRANSLATE_TEXT)

        elif not can_translate(vText):
            QDesktopServices.openUrl(QUrl(self.translate_url))

        else:
            self.translate_button.setEnabled(False)
            self.translate_button.setText("Traduction en cours…")
            # Quelques secondes de calcul : hors du fil de l'interface.
            threading.Thread(
                target=self.run_translation, args=(vText,), daemon=True
            ).start()

    def run_translation(self, pText):
        """Traduit dans un fil séparé et transmet le résultat par signal."""
        vTranslation = None
        vError = None

        try:
            vTranslation = translate_with_cache(self.database_file, pText)

        except ValueError as vException:
            vError = str(vException)

        self.translation_done.emit(pText, vTranslation, vError)

    def show_translation(self, pText, pTranslation, pError):
        """Affiche la traduction, sauf si une autre offre a été choisie entre-temps."""
        if pText != self.original_description:
            return

        self.translate_button.setEnabled(True)

        if pError:
            self.translate_button.setText(TRANSLATE_TEXT)
            QMessageBox.warning(self, TRANSLATE_TEXT, pError)
            return

        self.translated = True
        self.show_description(pTranslation)
        self.translate_button.setText("Texte d'origine")

    def show_fetched_description(self, pOffer):
        """Réaffiche l'offre avec sa description, si elle est toujours affichée."""
        if not self.offer or not pOffer.get("description"):
            self.description.setPlaceholderText(
                "Aucune description fournie par la source."
            )
            return

        if (self.offer["source"], self.offer["source_id"]) == (
            pOffer["source"],
            pOffer["source_id"],
        ):
            self.show_offer({**self.offer, **pOffer})

    def open_offer(self):
        """Ouvre l'offre dans le navigateur, uniquement en http ou https."""
        vUrl = safe_url(self.offer.get("url") if self.offer else None)

        if vUrl != "#":
            QDesktopServices.openUrl(QUrl(vUrl))
