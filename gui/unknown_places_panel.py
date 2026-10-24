"""Panneau des lieux introuvables : la commune indiquée place leurs offres"""

import requests
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import clear_layout, create_button, create_card, show_message
from job.geocoding import list_unknown_places, resolve_place
from utils.logger import get_logger

logger = get_logger(__name__)


class UnknownPlacesPanel(QWidget):
    """Liste les lieux non reconnus et associe chacun à la commune saisie."""

    placed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit la carte vide ; remplie par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Lieux introuvables",
            "Lieux d'offres en France que le géocodeur n'a pas reconnus, les plus "
            "fréquents d'abord. Indiquez la commune : elle est retenue pour toutes "
            "les offres de ce lieu.",
            pIcon="map-pin",
        )
        vCardLayout.addLayout(self.rows_layout)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Relit les lieux introuvables, une ligne chacun."""
        clear_layout(self.rows_layout)
        vPlaces = list_unknown_places(self.database_file)

        for vPlace in vPlaces:
            self.rows_layout.addWidget(self.create_row(vPlace))

        if not vPlaces:
            vEmpty = QLabel("Tous les lieux des offres en France sont reconnus.")
            vEmpty.setObjectName("cardSubtitle")
            self.rows_layout.addWidget(vEmpty)

    def create_row(self, pPlace):
        """Construit la ligne d'un lieu : exemple, nombre d'offres, commune à saisir."""
        vEdit = QLineEdit()
        vEdit.setPlaceholderText("Commune ou code postal")

        vButton = create_button("Associer")
        vButton.clicked.connect(lambda: self.resolve(pPlace["key"], vEdit.text()))
        vEdit.returnPressed.connect(vButton.click)

        rRow = QWidget()

        vLayout = QHBoxLayout(rRow)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(
            QLabel(f"{pPlace['example']} ({pPlace['count']} offre(s))"), 1
        )
        vLayout.addWidget(vEdit)
        vLayout.addWidget(vButton)

        return rRow

    def resolve(self, pKey, pCommune):
        """Cherche la commune, place les offres du lieu et relit la liste."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vLabel = resolve_place(self.database_file, pKey, pCommune)

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except requests.RequestException:
            logger.warning("Géocodeur injoignable pour la correction d'un lieu")
            show_message(
                self.message_label,
                "Le géocodeur ne répond pas : réessayez plus tard.",
                "danger",
            )
            return

        finally:
            QApplication.restoreOverrideCursor()

        self.refresh()
        show_message(
            self.message_label, f"Lieu associé à {vLabel} : ses offres sont placées."
        )
        self.placed.emit()
