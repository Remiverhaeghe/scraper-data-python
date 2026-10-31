"""Carte des listes d'entreprises : exclues, privilégiées et agences d'intérim"""

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, create_icon_label, show_message
from job.agencies import load_interim_agencies, save_interim_agencies
from job.companies import load_company_rules, save_company_rules
from utils.logger import get_logger

logger = get_logger(__name__)

# Hauteur des listes : quelques lignes, la liste défile au-delà.
COMPANY_EDIT_HEIGHT = 76


class CompanyListsPanel(QWidget):
    """Entreprises à exclure, à privilégier, et agences d'intérim à reconnaître."""

    def __init__(self, pDatabaseFile):
        """Construit les trois listes et le bouton d'enregistrement."""
        super().__init__()

        self.database_file = pDatabaseFile

        vCard, vCardLayout = create_card(
            "Entreprises",
            "Une entreprise par ligne. Les exclues sont masquées de la liste des "
            "offres, les privilégiées marquées d'une étoile.",
        )

        self.edits = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)

        # Exclues en rouge, privilégiées en vert : le rôle de chaque liste se voit.
        for vColumn, (vKind, vLabel, vIcon, vTone) in enumerate(
            (
                ("excluded", "À exclure", "circle-alert", "danger"),
                ("preferred", "À privilégier", "circle-check", "success"),
            )
        ):
            vTitle = QLabel(vLabel)
            vTitle.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")

            vTitleRow = QHBoxLayout()
            vTitleRow.setSpacing(6)
            vTitleRow.addWidget(create_icon_label(vIcon, COLORS[vTone], 16))
            vTitleRow.addWidget(vTitle, 1)

            vEdit = QPlainTextEdit()
            vEdit.setObjectName(f"{vKind}Companies")
            vEdit.setPlaceholderText("Ex. Acme\nGlobex")
            vEdit.setFixedHeight(COMPANY_EDIT_HEIGHT)

            self.edits[vKind] = vEdit
            vGrid.addLayout(vTitleRow, 0, vColumn)
            vGrid.addWidget(vEdit, 1, vColumn)

        vAgencyTitle = QLabel("Agences d'intérim, pour le filtre « Sans intérim »")
        vAgencyTitle.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")

        vAgencyEdit = QPlainTextEdit()
        vAgencyEdit.setPlaceholderText("Vide : liste par défaut (Proman, Adecco…)")
        vAgencyEdit.setFixedHeight(COMPANY_EDIT_HEIGHT)
        self.edits["agencies"] = vAgencyEdit

        vGrid.addWidget(vAgencyTitle, 2, 0, 1, 2)
        vGrid.addWidget(vAgencyEdit, 3, 0, 1, 2)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.message_label, 1)

        vCardLayout.addLayout(vGrid)
        vCardLayout.addLayout(vActions)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

        self.refresh()

    def refresh(self):
        """Relit les listes d'entreprises en base."""
        try:
            vRules = load_company_rules(self.database_file)

        except Exception:
            logger.exception("Impossible de lire les listes d'entreprises")

            show_message(
                self.message_label, "Les listes n'ont pas pu être lues.", "danger"
            )

        else:
            vRules["agencies"] = load_interim_agencies(self.database_file)

            for vKind, vEdit in self.edits.items():
                vEdit.setPlainText("\n".join(vRules[vKind]))

    def save(self):
        """Enregistre les listes d'entreprises et d'agences."""
        try:
            vRules = save_company_rules(
                self.database_file,
                self.edits["excluded"].toPlainText(),
                self.edits["preferred"].toPlainText(),
            )
            vAgencies = save_interim_agencies(
                self.database_file, self.edits["agencies"].toPlainText()
            )

        except ValueError as vException:
            vMessage, vTone = str(vException), "warning"

        except Exception:
            logger.exception("Échec de l'enregistrement des listes d'entreprises")

            vMessage, vTone = "Les listes n'ont pas pu être enregistrées.", "danger"

        else:
            self.refresh()

            vMessage, vTone = (
                f"{len(vRules['excluded'])} entreprise(s) exclue(s), "
                f"{len(vRules['preferred'])} privilégiée(s), "
                f"{len(vAgencies)} agence(s) d'intérim.",
                "success",
            )

        show_message(self.message_label, vMessage, vTone)
