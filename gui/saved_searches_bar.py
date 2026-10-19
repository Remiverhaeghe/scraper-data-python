"""Barre des recherches enregistrées : pastilles, enregistrement et suppression"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.icons import get_icon
from gui.theme import COLORS
from gui.widgets import STATUS_STYLES, create_button
from job.presentation import describe_search, describe_sources
from storage.saved_searches import (
    delete_saved_search,
    get_saved_searches,
    save_search,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Nombre de pastilles par ligne, comme les sources
CHIP_COLUMNS = 6


def describe_saved_search(pSearch):
    """Résume une recherche enregistrée : critères, puis sources."""

    vParameters = {**pSearch["criteria"], "sources": pSearch["sources"]}

    rDescription = " · ".join(
        vPart
        for vPart in (
            describe_search(vParameters) or "Sans critère",
            describe_sources(vParameters),
        )
        if vPart
    )

    return rDescription


class SavedSearchesBar(QWidget):
    """Enregistre la recherche affichée et recharge une recherche enregistrée.

    pGetSearch retourne les sources et les critères actuels du formulaire.
    """

    search_loaded = Signal(list, dict)

    def __init__(self, pDatabaseFile, pGetSearch):
        """Construit l'en-tête, les pastilles et le résumé ; lit les recherches."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.get_search = pGetSearch
        self.searches = {}
        self.selected_name = None

        vLabel = QLabel("Recherches enregistrées")
        vLabel.setObjectName("fieldLabel")

        vSaveButton = create_button(
            "Enregistrer…", "download", "primaryButton", COLORS["on_primary"]
        )
        vSaveButton.setToolTip("Enregistre les critères et les sources actuels")
        vSaveButton.clicked.connect(self.save_current)

        self.delete_button = create_button(
            "Supprimer", "circle-alert", "dangerButton", COLORS["danger"]
        )
        self.delete_button.setToolTip("Supprime la recherche sélectionnée")
        self.delete_button.clicked.connect(self.delete_current)

        self.message_icon = QLabel()
        self.message_label = QLabel()

        # Boutons à côté du libellé, le message de résultat à leur suite
        vHeader = QHBoxLayout()
        vHeader.setSpacing(10)
        vHeader.addWidget(vLabel)
        vHeader.addSpacing(8)
        vHeader.addWidget(vSaveButton)
        vHeader.addWidget(self.delete_button)
        vHeader.addSpacing(12)
        vHeader.addWidget(self.message_icon)
        vHeader.addWidget(self.message_label)
        vHeader.addStretch()

        self.group = QButtonGroup(self)

        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("cardSubtitle")
        self.summary_label.setWordWrap(True)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(8)
        vLayout.addLayout(vHeader)
        vLayout.addLayout(self.grid)
        vLayout.addWidget(self.summary_label)

        self.refresh()

    def set_message(self, pKind, pText):
        """Affiche le résultat d'une action sur les recherches enregistrées."""
        vIcon, vColorName = STATUS_STYLES[pKind]

        self.message_icon.setPixmap(
            get_icon(vIcon, COLORS[vColorName], 16).pixmap(16, 16)
        )
        self.message_label.setStyleSheet(f"color: {COLORS[vColorName]};")
        self.message_label.setText(pText)

    def refresh(self, pSelectedName=None):
        """Recharge les pastilles des recherches enregistrées."""
        try:
            self.searches = {
                vSearch["name"]: vSearch
                for vSearch in get_saved_searches(self.database_file)
            }

        except Exception:
            logger.exception("Impossible de lire les recherches enregistrées")

            self.searches = {}

        for vButton in self.group.buttons():
            self.group.removeButton(vButton)
            vButton.setParent(None)
            vButton.deleteLater()

        for vIndex, (vName, vSearch) in enumerate(self.searches.items()):
            vButton = QPushButton(vName)
            vButton.setObjectName("savedChip")
            vButton.setCheckable(True)
            vButton.setCursor(Qt.CursorShape.PointingHandCursor)
            vButton.setIcon(get_icon("search", COLORS["primary"], 14))
            vButton.setToolTip(describe_saved_search(vSearch))
            vButton.clicked.connect(
                lambda pChecked=False, pName=vName: self.load(pName)
            )

            self.group.addButton(vButton)
            self.grid.addWidget(vButton, *divmod(vIndex, CHIP_COLUMNS))

        self.select(pSelectedName)

    def select(self, pName):
        """Met en avant la recherche choisie et affiche son résumé."""
        self.selected_name = pName if pName in self.searches else None

        # Le groupe exclusif interdit de tout décocher : il est suspendu le temps
        # de mettre à jour les pastilles.
        self.group.setExclusive(False)

        for vButton in self.group.buttons():
            vButton.setChecked(vButton.text() == self.selected_name)

        self.group.setExclusive(True)

        if self.selected_name is not None:
            vSummary = describe_saved_search(self.searches[self.selected_name])
        elif self.searches:
            # Les pastilles parlent d'elles-mêmes : pas de ligne d'aide en plus.
            vSummary = ""
        else:
            vSummary = (
                "Aucune recherche enregistrée : remplissez les critères et les "
                "sources, puis cliquez sur « Enregistrer… »."
            )

        self.summary_label.setText(vSummary)
        self.summary_label.setVisible(bool(vSummary))
        self.delete_button.setEnabled(self.selected_name is not None)

    def load(self, pName):
        """Transmet la recherche choisie au formulaire."""
        if pName in self.searches:
            vSearch = self.searches[pName]

            self.search_loaded.emit(vSearch["sources"], vSearch["criteria"])
            self.select(pName)
            self.set_message("idle", f"Recherche « {pName} » chargée")

    def save_current(self):
        """Demande un nom puis enregistre les critères et les sources actuels."""
        vSources, vCriteria = self.get_search()

        if not vSources:
            self.set_message("warning", "Sélectionnez au moins une source.")
            return

        vName, vAccepted = QInputDialog.getText(
            self,
            "Enregistrer la recherche",
            "Nom de la recherche (un nom existant est remplacé) :",
            text=self.selected_name or "",
        )

        if vAccepted:
            try:
                vSavedName = save_search(
                    self.database_file, vName, vSources, vCriteria, datetime.now()
                )

            except ValueError as vException:
                self.set_message("warning", str(vException))

            except Exception:
                logger.exception("Échec de l'enregistrement de la recherche")

                self.set_message("error", "La recherche n'a pas pu être enregistrée.")

            else:
                self.refresh(vSavedName)
                self.set_message("success", f"Recherche « {vSavedName} » enregistrée")

    def delete_current(self):
        """Supprime la recherche choisie, après confirmation."""
        vName = self.selected_name

        if vName is None:
            self.set_message("warning", "Choisissez d'abord une recherche enregistrée.")
            return

        vAnswer = QMessageBox.question(
            self,
            "Supprimer la recherche",
            f"Supprimer la recherche « {vName} » ?",
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            try:
                delete_saved_search(self.database_file, vName)

            except Exception:
                logger.exception("Échec de la suppression de la recherche")

                self.set_message("error", "La recherche n'a pas pu être supprimée.")

            else:
                self.refresh()
                self.set_message("idle", f"Recherche « {vName} » supprimée")
