"""Carte des entreprises suivies sur les plateformes de pages carrière"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.company_pages import (
    PLATFORMS,
    add_company_from_url,
    check_companies,
    load_company_list,
    save_company_lists,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class CompanyPagesPanel(QWidget):
    """Liste des entreprises suivies par plateforme, enregistrée et vérifiable."""

    def __init__(self, pDatabaseFile):
        """Construit un champ par plateforme, puis les boutons et le bilan."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.edits = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(8)

        for vRow, (vPlatform, (vLabel, _, _, vExample)) in enumerate(PLATFORMS.items()):
            vName = QLabel(vLabel)
            vName.setObjectName("fieldLabel")

            vEdit = QLineEdit()
            vEdit.setPlaceholderText(
                f"Identifiants séparés par des virgules ({vExample})"
            )
            self.edits[vPlatform] = vEdit

            vGrid.addWidget(vName, vRow, 0)
            vGrid.addWidget(vEdit, vRow, 1)

        vGrid.setColumnStretch(1, 1)

        vSaveButton = create_button(
            "Enregistrer", "download", pIconColor=COLORS["primary"]
        )
        vSaveButton.clicked.connect(self.save)

        vCheckButton = create_button(
            "Vérifier", "circle-check", pIconColor=COLORS["primary"]
        )
        vCheckButton.setToolTip(
            "Interroge chaque plateforme : les offres publiées par entreprise"
        )
        vCheckButton.clicked.connect(self.check)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(vCheckButton)
        vActions.addStretch()

        # Adresse copiée depuis le navigateur : plateforme et identifiant déduits
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(
            "Ou collez l'adresse d'un site carrière, par exemple "
            "https://jobs.lever.co/qonto"
        )
        self.url_edit.returnPressed.connect(self.add_from_url)

        vAddButton = create_button(
            "Ajouter", "circle-check", pIconColor=COLORS["primary"]
        )
        vAddButton.clicked.connect(self.add_from_url)

        vAddRow = QHBoxLayout()
        vAddRow.addWidget(self.url_edit, 1)
        vAddRow.addWidget(vAddButton)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextFormat(Qt.TextFormat.PlainText)

        vCard, vCardLayout = create_card(
            "Pages carrière suivies",
            "Entreprises dont les offres sont lues directement sur leur page carrière. "
            "Champ vide : la liste du .env, sinon celle par défaut.",
        )
        vCardLayout.addLayout(vGrid)
        vCardLayout.addLayout(vAddRow)
        vCardLayout.addLayout(vActions)
        vCardLayout.addWidget(self.message_label)
        vCardLayout.addWidget(self.result_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Affiche les entreprises suivies de chaque plateforme."""
        for vPlatform, vEdit in self.edits.items():
            vEdit.setText(
                load_company_list(vPlatform, self.database_file).replace(",", ", ")
            )

    def add_from_url(self):
        """Ajoute l'entreprise de l'adresse collée, après vérification."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vMessage = add_company_from_url(self.database_file, self.url_edit.text())

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        finally:
            QApplication.restoreOverrideCursor()

        self.url_edit.clear()
        self.refresh()
        show_message(self.message_label, vMessage)

    def save(self):
        """Enregistre les listes saisies, prises en compte à la prochaine recherche."""
        try:
            save_company_lists(
                self.database_file,
                {vPlatform: vEdit.text() for vPlatform, vEdit in self.edits.items()},
            )

        except Exception:
            logger.exception("Pages carrière suivies non enregistrées")
            show_message(
                self.message_label,
                "Les listes n'ont pas pu être enregistrées.",
                "danger",
            )
            return

        self.refresh()
        show_message(
            self.message_label,
            "Listes enregistrées : prises en compte à la prochaine recherche.",
        )

    def check(self):
        """Vérifie chaque entreprise saisie auprès de sa plateforme."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vLines = [
                f"{PLATFORMS[vPlatform][0]} · {vCompany} : {vMessage}"
                for vPlatform, vEdit in self.edits.items()
                for vCompany, _, vMessage in check_companies(vPlatform, vEdit.text())
            ]

        finally:
            QApplication.restoreOverrideCursor()

        self.result_label.setText("\n".join(vLines) or "Aucune entreprise à vérifier.")
