"""Carte du domicile : point de départ du filtre de distance des offres"""

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.geocoding import (
    DISTANCE_FILTERS,
    load_home,
    locate_offers,
    save_alert_radius,
    save_home,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class HomeLocationPanel(QWidget):
    """Adresse du domicile, cherchée puis enregistrée ; les offres sont ensuite placées."""

    # Bilan de locate_offers, ou None en cas d'échec, émis depuis le thread
    offers_located = Signal(object)

    def __init__(self, pDatabaseFile):
        """Construit le champ d'adresse, le bouton et le message."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText(
            "Ville ou adresse, par exemple 59000 Lille"
        )
        self.address_edit.returnPressed.connect(self.save)

        vSaveButton = create_button(
            "Enregistrer", "map-pin", pIconColor=COLORS["primary"]
        )
        vSaveButton.clicked.connect(self.save)

        vRow = QHBoxLayout()
        vRow.addWidget(self.address_edit, 1)
        vRow.addWidget(vSaveButton)

        # Le téléphone et le récapitulatif par e-mail ne signalent que ces offres.
        self.radius_combo = QComboBox()
        self.radius_combo.setToolTip(
            "Offres signalées par le téléphone et l'e-mail de la semaine ; "
            "le télétravail reste toujours signalé"
        )

        for vDistance, vLabel in DISTANCE_FILTERS.items():
            self.radius_combo.addItem(vLabel, vDistance)

        self.radius_combo.activated.connect(self.save_radius)

        vRadiusLabel = QLabel("Alertes")
        vRadiusLabel.setObjectName("fieldLabel")

        vRadiusRow = QHBoxLayout()
        vRadiusRow.addWidget(vRadiusLabel)
        vRadiusRow.addWidget(self.radius_combo)
        vRadiusRow.addStretch()

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Domicile",
            "Sert au filtre de distance des offres en France, à vol d'oiseau. "
            "Adresse cherchée sur le géocodeur public de l'IGN, gardée sur ce PC.",
        )
        vCardLayout.addLayout(vRow)
        vCardLayout.addLayout(vRadiusRow)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

        self.offers_located.connect(self.show_located)

    def refresh(self):
        """Affiche l'adresse enregistrée et le lieu reconnu."""
        vHome = load_home(self.database_file)

        self.address_edit.setText(vHome["address"] if vHome else "")
        self.radius_combo.setEnabled(vHome is not None)
        self.radius_combo.setCurrentIndex(
            max(self.radius_combo.findData((vHome or {}).get("alert_radius_km", 0)), 0)
        )
        show_message(
            self.message_label,
            f"Lieu reconnu : {vHome['label']}" if vHome else "",
            None,
        )

    def save_radius(self):
        """Enregistre le rayon des alertes choisi."""
        try:
            save_alert_radius(self.database_file, self.radius_combo.currentData())

        except Exception:
            logger.exception("Rayon des alertes non enregistré")
            show_message(
                self.message_label, "Le rayon n'a pas pu être enregistré.", "danger"
            )
            return

        show_message(self.message_label, "Rayon des alertes enregistré.")

    def save(self):
        """Cherche l'adresse saisie, l'enregistre puis place les offres en arrière-plan."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vHome = save_home(self.database_file, self.address_edit.text())

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except Exception:
            logger.exception("Domicile non enregistré")
            show_message(
                self.message_label,
                "Le géocodeur est injoignable : vérifiez la connexion.",
                "danger",
            )
            return

        finally:
            QApplication.restoreOverrideCursor()

        if vHome is None:
            show_message(self.message_label, "Domicile effacé.")
            return

        show_message(
            self.message_label,
            f"Lieu reconnu : {vHome['label']}. Placement des offres en cours…",
        )
        # Plusieurs centaines de lieux à chercher la première fois : l'interface
        # reste utilisable pendant ce temps.
        threading.Thread(target=self.run_location, daemon=True).start()

    def run_location(self):
        """Place les offres sans position ; appelé dans un thread."""
        try:
            vReport = locate_offers(self.database_file)

        except Exception:
            logger.exception("Échec du placement des offres sur la carte")
            vReport = None

        self.offers_located.emit(vReport)

    def show_located(self, pReport):
        """Affiche le bilan du placement des offres."""
        if pReport is None:
            show_message(
                self.message_label,
                "Les offres n'ont pas pu être placées. Voir les journaux.",
                "danger",
            )
            return

        show_message(
            self.message_label,
            f"{pReport['located']} offre(s) placée(s) ; les suivantes le seront "
            "après chaque recherche.",
        )
