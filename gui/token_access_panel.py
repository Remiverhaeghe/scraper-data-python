"""Carte d'un accès secret : adresse ou jeton affiché, renouvelé et copié"""

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenAccessPanel(QWidget):
    """Affiche un accès secret, le crée ou le renouvelle après confirmation.

    pTexts donne les libellés de la carte ; pRead retourne la valeur affichée, ou
    None ; pRenew en crée une nouvelle. pFixedText ajoute une ligne en lecture seule,
    l'adresse du serveur par exemple. pQrCode, s'il est donné, retourne en PNG le
    QR code de la valeur, montré à la demande.
    """

    def __init__(self, pTexts, pRead, pRenew, pFixedText=None, pQrCode=None):
        """Construit la carte ; la valeur est lue par refresh."""
        super().__init__()

        self.texts = pTexts
        self.read = pRead
        self.renew_access = pRenew

        self.edit = QLineEdit()
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText(pTexts["placeholder"])

        self.button = create_button(
            pTexts["create"], pTexts["icon"], pIconColor=COLORS["primary"]
        )
        self.button.setToolTip(pTexts["tooltip"])
        self.button.clicked.connect(self.renew)

        self.copy_button = create_button("Copier", "copy", pIconColor=COLORS["primary"])
        self.copy_button.clicked.connect(self.copy)

        self.qr_code = pQrCode
        self.qr_button = create_button(
            "QR code", "qr-code", pIconColor=COLORS["primary"]
        )
        self.qr_button.setToolTip("Affiche le QR code à scanner avec l'application")
        self.qr_button.clicked.connect(self.show_qr_code)
        self.qr_button.setVisible(pQrCode is not None)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.button)
        vActions.addWidget(self.copy_button)
        vActions.addWidget(self.qr_button)
        vActions.addWidget(self.message_label, 1)

        vCard, vCardLayout = create_card(pTexts["title"], pTexts["subtitle"])

        if pFixedText:
            vFixed = QLineEdit(pFixedText)
            vFixed.setReadOnly(True)
            vCardLayout.addWidget(vFixed)

        vCardLayout.addWidget(self.edit)
        vCardLayout.addLayout(vActions)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Affiche la valeur enregistrée."""
        try:
            vValue = self.read()

        except Exception:
            logger.exception("Impossible de lire : %s", self.texts["title"])

            vValue = None

        self.edit.setText(vValue or "")
        self.button.setText(self.texts["renew"] if vValue else self.texts["create"])
        self.copy_button.setEnabled(bool(vValue))
        self.qr_button.setEnabled(bool(vValue))

    def renew(self):
        """Crée la valeur ; une valeur existante n'est remplacée qu'après confirmation."""
        if self.edit.text() and (
            QMessageBox.question(self, self.texts["renew"], self.texts["confirm"])
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.renew_access()

        except Exception:
            logger.exception("Échec de la création : %s", self.texts["title"])

            show_message(self.message_label, self.texts["failed"], "danger")

        else:
            self.refresh()
            show_message(self.message_label, self.texts["created"])

    def show_qr_code(self):
        """Affiche le QR code dans une fenêtre, le temps de le scanner."""
        vPixmap = QPixmap()
        vPixmap.loadFromData(self.qr_code(self.edit.text()))

        vImage = QLabel()
        vImage.setPixmap(vPixmap)

        vHelp = QLabel(
            "Dans l'application, écran « Connexion au serveur » : "
            "« Scanner le QR code »."
        )
        vHelp.setWordWrap(True)

        vDialog = QDialog(self)
        vDialog.setWindowTitle(self.texts["title"])

        vLayout = QVBoxLayout(vDialog)
        vLayout.addWidget(vImage)
        vLayout.addWidget(vHelp)

        vDialog.exec()

    def copy(self):
        """Copie la valeur affichée dans le presse-papiers."""
        QApplication.clipboard().setText(self.edit.text())

        show_message(self.message_label, self.texts["copied"])
