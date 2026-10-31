"""Carte des notifications e-mail : adresse, score minimal et envoi de test"""

import smtplib

from PySide6.QtCore import Qt
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
from gui.widgets import create_button, create_card, create_icon_label, show_message
from job.notification import build_test_email
from job.schedule import (
    MIN_SCORE_CHOICES,
    format_min_score,
    load_schedule,
    save_min_score,
    save_notification_email,
)
from utils.logger import get_logger
from utils.mailer import EMAIL_SETTINGS, get_missing_email_settings, send_email

logger = get_logger(__name__)


class NotificationPanel(QWidget):
    """Adresse des notifications et état du compte Gmail."""

    def __init__(self, pDatabaseFile):
        """Construit l'état du compte, l'adresse, le score minimal et les actions."""
        super().__init__()

        self.database_file = pDatabaseFile

        vCard, vCardLayout = create_card(
            "Notifications e-mail",
            "Nouvelles offres de la recherche planifiée et relances du jour, par Gmail",
        )

        # Seuls les noms des variables manquantes sont affichés, jamais leurs valeurs.
        vMissing = get_missing_email_settings()

        if vMissing:
            vIcon, vColor = "circle-alert", COLORS["warning"]
            vText = "À renseigner dans .env : " + ", ".join(vMissing)
        else:
            vIcon, vColor = "circle-check", COLORS["success"]
            vText = f"Compte Gmail configuré dans .env ({', '.join(EMAIL_SETTINGS)})"

        vState = QLabel(vText)
        vState.setObjectName("cardSubtitle")
        vState.setWordWrap(True)

        vStateRow = QHBoxLayout()
        vStateRow.setSpacing(10)
        vStateRow.addWidget(create_icon_label(vIcon, vColor, 18))
        vStateRow.addWidget(vState, 1)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(
            "Adresse de destination, ex. prenom@gmail.com"
        )

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.test_button = create_button(
            "Envoyer un e-mail de test", "send", pIconColor=COLORS["primary"]
        )
        self.test_button.setEnabled(not vMissing)
        self.test_button.clicked.connect(self.send_test_email)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        # Le score compare l'offre aux compétences de la page Profil.
        self.min_score_combo = QComboBox()
        self.min_score_combo.setToolTip(
            "Seules les nouvelles offres assez proches du profil sont envoyées"
        )

        for vScore in MIN_SCORE_CHOICES:
            self.min_score_combo.addItem(format_min_score(vScore), vScore)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.test_button)
        vActions.addStretch()

        vCardLayout.addLayout(vStateRow)
        vCardLayout.addWidget(self.email_edit)
        vCardLayout.addWidget(self.min_score_combo)
        vCardLayout.addLayout(vActions)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Relit l'adresse et le score minimal, rangés avec la planification."""
        try:
            vSchedule = load_schedule(self.database_file)

        except Exception:
            logger.exception("Impossible de lire l'adresse de notification")

            show_message(self.message_label, "L'adresse n'a pas pu être lue.", "danger")

        else:
            self.email_edit.setText(vSchedule["email"] or "")
            self.min_score_combo.setCurrentIndex(
                self.min_score_combo.findData(vSchedule["min_score"])
            )

    def save(self):
        """Enregistre l'adresse de destination des notifications."""
        try:
            vErrors = save_notification_email(
                self.database_file, self.email_edit.text()
            ) or save_min_score(self.database_file, self.min_score_combo.currentData())

        except Exception:
            logger.exception("Échec de l'enregistrement de l'adresse de notification")

            show_message(
                self.message_label, "L'adresse n'a pas pu être enregistrée.", "danger"
            )
            return

        if vErrors:
            show_message(self.message_label, " ".join(vErrors), "warning")
        elif self.email_edit.text().strip():
            show_message(self.message_label, "Adresse enregistrée.")
        else:
            show_message(self.message_label, "Notifications désactivées.", "warning")

    def send_test_email(self):
        """Envoie un e-mail de test à l'adresse saisie."""
        vEmail = self.email_edit.text().strip()

        if not vEmail:
            show_message(
                self.message_label, "Saisissez d'abord une adresse.", "warning"
            )
            return

        # L'envoi est court mais bloquant : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            send_email(vEmail, *build_test_email())

        except (OSError, smtplib.SMTPException, ValueError) as vException:
            logger.error("Échec de l'e-mail de test : %s", vException)

            show_message(
                self.message_label, f"Échec de l'envoi : {vException}", "danger"
            )

        else:
            show_message(self.message_label, "E-mail de test envoyé.")

        finally:
            QApplication.restoreOverrideCursor()
