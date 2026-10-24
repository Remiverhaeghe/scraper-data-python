"""Panneau des données : sauvegarde complète, sauvegardes de la base et réinitialisation"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from config import BACKUP_NAS_DIRECTORY
from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.personal_export import export_personal_data
from job.presentation import describe_backup
from storage.archive import export_archive, restore_archive, restore_backup
from storage.backup import describe_backups, describe_nas_copies, fetch_nas_copy
from storage.encrypted_archive import (
    ENCRYPTED_ARCHIVE_SUFFIX,
    MIN_PASSWORD_LENGTH,
    export_encrypted_archive,
    restore_encrypted_archive,
)
from storage.maintenance import reset_database
from utils.logger import get_logger

logger = get_logger(__name__)


class DataPanel(QWidget):
    """Exporte, restaure ou efface les données ; signale toute restauration."""

    # Message à afficher une fois les pages reconstruites sur les nouvelles données
    data_reset = Signal(str)

    def __init__(self, pDatabaseFile, pNasDirectory=BACKUP_NAS_DIRECTORY):
        """Construit les trois cartes ; la liste des sauvegardes est lue par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.nas_directory = pNasDirectory

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(18)
        vLayout.addWidget(self.create_archive_card())
        vLayout.addWidget(self.create_usb_card())
        vLayout.addWidget(self.create_backups_card())
        vLayout.addWidget(self.create_reset_card())

        self.refresh()

    def create_backups_card(self):
        """Construit le choix d'une sauvegarde de la base à restaurer."""
        vCard, vLayout = create_card(
            "Sauvegardes de la base",
            "Faites chaque jour et avant chaque opération risquée. Restaurer remet "
            "la base dans cet état ; l'état actuel est d'abord sauvegardé, les "
            "pièces jointes ne changent pas.",
        )

        self.backups_combo = QComboBox()

        self.restore_backup_button = create_button(
            "Restaurer", "history", "dangerButton", COLORS["danger"]
        )
        self.restore_backup_button.clicked.connect(self.confirm_backup_restore)

        self.backup_message = QLabel()
        self.backup_message.setObjectName("cardSubtitle")
        self.backup_message.setWordWrap(True)

        # Le NAS n'est lu qu'au clic : éteint, il ralentirait l'ouverture de la page.
        self.nas_button = create_button("Depuis le NAS…", "server")
        self.nas_button.setToolTip(
            "Choisir une des copies quotidiennes du NAS, utile après la perte du PC"
        )
        self.nas_button.setVisible(bool(self.nas_directory))
        self.nas_button.clicked.connect(self.choose_nas_copy)

        vActions = QHBoxLayout()
        vActions.addWidget(self.backups_combo, 1)
        vActions.addWidget(self.restore_backup_button)
        vActions.addWidget(self.nas_button)

        vLayout.addLayout(vActions)
        vLayout.addWidget(self.backup_message)

        return vCard

    def refresh(self):
        """Relit la liste des sauvegardes de la base."""
        try:
            vBackups = describe_backups(self.database_file)

        except OSError:
            logger.exception("Impossible de lister les sauvegardes de la base")

            vBackups = []

        self.backups_combo.clear()

        for vBackup in vBackups:
            self.backups_combo.addItem(describe_backup(vBackup), vBackup["name"])

        if not vBackups:
            self.backups_combo.addItem("Aucune sauvegarde pour le moment", None)

        self.restore_backup_button.setEnabled(bool(vBackups))

    def confirm_backup_restore(self):
        """Demande confirmation, puis restaure la sauvegarde choisie."""
        vName = self.backups_combo.currentData()

        # Par sécurité, Entrée annule : il faut cliquer sur Oui.
        if vName and (
            QMessageBox.warning(
                self,
                "Restaurer la sauvegarde",
                f"La base sera remise dans l'état du {self.backups_combo.currentText()}"
                ". L'état actuel est d'abord sauvegardé. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.restore_backup(vName)

    def choose_nas_copy(self):
        """Liste les copies du NAS, puis restaure celle choisie après confirmation."""
        try:
            vCopies = describe_nas_copies(self.database_file, self.nas_directory)

        except OSError as vException:
            logger.warning("Copies du NAS illisibles : %s", vException)

            show_message(
                self.backup_message,
                "Le NAS est injoignable : vérifiez qu'il est allumé et accessible.",
                "warning",
            )
            return

        if not vCopies:
            show_message(self.backup_message, "Aucune copie sur le NAS.", "warning")
            return

        vLabels = [describe_backup(vCopy) for vCopy in vCopies]
        vLabel, vChosen = QInputDialog.getItem(
            self, "Restaurer depuis le NAS", "Copie à restaurer :", vLabels, 0, False
        )

        if not vChosen:
            return

        vName = vCopies[vLabels.index(vLabel)]["name"]

        if (
            QMessageBox.warning(
                self,
                "Restaurer depuis le NAS",
                f"La base sera remise dans l'état du {vLabel}. L'état actuel est "
                "d'abord sauvegardé. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            vLocalFile = fetch_nas_copy(self.database_file, vName, self.nas_directory)

        except ValueError as vException:
            # Copie chiffrée sans la bonne clé : le message dit quoi corriger.
            logger.warning("Copie du NAS non rapatriée : %s", vException)
            show_message(self.backup_message, str(vException), "danger")
            return

        except OSError as vException:
            logger.warning("Copie du NAS non rapatriée : %s", vException)

            show_message(
                self.backup_message,
                "La copie n'a pas pu être lue sur le NAS.",
                "danger",
            )
            return

        self.restore_backup(vLocalFile.name)

    def restore_backup(self, pName):
        """Restaure une sauvegarde ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = restore_backup(self.database_file, pName, datetime.now())

        except ValueError as vException:
            logger.warning("Restauration de sauvegarde refusée : %s", vException)

            show_message(self.backup_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de la restauration de la sauvegarde %s", pName)

            show_message(
                self.backup_message,
                "La restauration a échoué. Voir les journaux.",
                "danger",
            )

        else:
            self.data_reset.emit(
                f"Sauvegarde restaurée. Anciennes données : {vBackupFile.name}"
            )

    def create_archive_card(self):
        """Construit l'export et la restauration de la sauvegarde complète."""
        vCard, vLayout = create_card(
            "Sauvegarde complète",
            "Base et pièces jointes dans une archive .zip, pour changer de PC sans "
            "rien perdre. La restauration sauvegarde d'abord les données actuelles.",
        )

        self.export_archive_button = create_button(
            "Exporter…", "download", pIconColor=COLORS["primary"]
        )
        self.export_archive_button.clicked.connect(self.choose_archive_target)

        self.restore_archive_button = create_button(
            "Restaurer…", "upload", "dangerButton", COLORS["danger"]
        )
        self.restore_archive_button.clicked.connect(self.choose_archive_source)

        self.personal_data_button = create_button(
            "Mes données (lisibles)…", "file-text"
        )
        self.personal_data_button.setToolTip(
            "Fichiers JSON lisibles sans l'application, pièces jointes comprises, "
            "sans secret ni jeton"
        )
        self.personal_data_button.clicked.connect(self.choose_personal_data_target)

        self.archive_message = QLabel()
        self.archive_message.setObjectName("cardSubtitle")
        self.archive_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.export_archive_button)
        vActions.addWidget(self.restore_archive_button)
        vActions.addWidget(self.personal_data_button)
        vActions.addWidget(self.archive_message, 1)

        vLayout.addLayout(vActions)

        return vCard

    def choose_archive_target(self):
        """Demande où enregistrer la sauvegarde complète puis l'écrit."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la sauvegarde complète",
            str(Path.home() / f"jobboard-{datetime.now():%Y%m%d}.zip"),
            "Archive (*.zip)",
        )

        if vPath:
            self.export_archive(vPath)

    def export_archive(self, pPath):
        """Écrit la base et les pièces jointes dans l'archive choisie."""
        try:
            vCount = export_archive(self.database_file, pPath)

        except Exception:
            logger.exception("Échec de l'export de la sauvegarde complète")

            show_message(
                self.archive_message, "L'export a échoué. Voir les journaux.", "danger"
            )

        else:
            show_message(
                self.archive_message,
                f"Sauvegarde exportée : base et {vCount} pièce(s) jointe(s).",
            )

    def choose_personal_data_target(self):
        """Demande où enregistrer vos données lisibles puis les écrit."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter mes données",
            str(Path.home() / f"mes-donnees-jobboard-{datetime.now():%Y%m%d}.zip"),
            "Archive (*.zip)",
        )

        if vPath:
            self.export_personal_data(vPath)

    def export_personal_data(self, pPath):
        """Écrit vos données personnelles lisibles dans l'archive choisie."""
        try:
            vCount = export_personal_data(self.database_file, pPath, datetime.now())

        except Exception:
            logger.exception("Échec de l'export des données personnelles")

            show_message(
                self.archive_message, "L'export a échoué. Voir les journaux.", "danger"
            )

        else:
            show_message(
                self.archive_message, f"Données exportées : {vCount} fichier(s)."
            )

    def choose_archive_source(self):
        """Demande l'archive à restaurer, puis une confirmation."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Restaurer une sauvegarde complète",
            str(Path.home()),
            "Archive (*.zip)",
        )

        # Par sécurité, Entrée annule : il faut cliquer sur Oui.
        if vPath and (
            QMessageBox.warning(
                self,
                "Restaurer la sauvegarde",
                "Les données actuelles seront remplacées par celles de l'archive. "
                "Elles sont d'abord sauvegardées dans data/backups. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.restore_archive(vPath)

    def restore_archive(self, pPath):
        """Restaure l'archive ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = restore_archive(self.database_file, pPath, datetime.now())

        except ValueError as vException:
            logger.warning("Restauration refusée : %s", vException)

            show_message(self.archive_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de la restauration de la sauvegarde complète")

            show_message(
                self.archive_message,
                "La restauration a échoué. Voir les journaux.",
                "danger",
            )

        else:
            self.data_reset.emit(
                f"Sauvegarde restaurée. Anciennes données : {vBackupFile.name}"
            )

    def create_usb_card(self):
        """Construit la sauvegarde chiffrée par mot de passe, pour une clé USB."""
        vCard, vLayout = create_card(
            "Clé USB chiffrée",
            "Base et pièces jointes chiffrées par un mot de passe : la copie se "
            "restaure sur un autre PC, mais un mot de passe oublié la rend illisible.",
        )

        self.usb_export_button = create_button(
            "Sauvegarder sur la clé…", "lock", pIconColor=COLORS["primary"]
        )
        self.usb_export_button.clicked.connect(self.choose_usb_target)

        self.usb_restore_button = create_button(
            "Restaurer depuis la clé…", "upload", "dangerButton", COLORS["danger"]
        )
        self.usb_restore_button.clicked.connect(self.choose_usb_source)

        self.usb_message = QLabel()
        self.usb_message.setObjectName("cardSubtitle")
        self.usb_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.usb_export_button)
        vActions.addWidget(self.usb_restore_button)
        vActions.addWidget(self.usb_message, 1)

        vLayout.addLayout(vActions)

        return vCard

    def ask_password(self, pLabel):
        """Demande un mot de passe masqué ; retourne None si la saisie est annulée."""
        vPassword, vAccepted = QInputDialog.getText(
            self, "Clé USB chiffrée", pLabel, QLineEdit.EchoMode.Password
        )

        rPassword = vPassword if vAccepted else None

        return rPassword

    def choose_usb_target(self):
        """Demande le dossier de la clé et le mot de passe, puis écrit la copie."""
        vDirectory = QFileDialog.getExistingDirectory(
            self, "Choisir la clé USB ou son dossier", str(Path.home())
        )

        if not vDirectory:
            return

        vPassword = self.ask_password(
            f"Mot de passe ({MIN_PASSWORD_LENGTH} caractères au moins) :"
        )

        if vPassword is None:
            return

        if self.ask_password("Saisissez de nouveau le mot de passe :") != vPassword:
            show_message(
                self.usb_message, "Les deux mots de passe diffèrent.", "warning"
            )
            return

        self.export_to_usb(vDirectory, vPassword)

    def export_to_usb(self, pDirectory, pPassword):
        """Écrit la sauvegarde chiffrée dans le dossier choisi."""
        try:
            vFile = export_encrypted_archive(
                self.database_file, pDirectory, pPassword, datetime.now()
            )

        except ValueError as vException:
            show_message(self.usb_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de la sauvegarde chiffrée")

            show_message(
                self.usb_message,
                "La sauvegarde a échoué : clé pleine, retirée ou protégée ?",
                "danger",
            )

        else:
            show_message(self.usb_message, f"Sauvegarde chiffrée : {vFile.name}")

    def choose_usb_source(self):
        """Demande la copie chiffrée, son mot de passe et une confirmation."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Restaurer une sauvegarde chiffrée",
            str(Path.home()),
            f"Sauvegarde chiffrée (*{ENCRYPTED_ARCHIVE_SUFFIX})",
        )

        if not vPath:
            return

        vPassword = self.ask_password("Mot de passe de la sauvegarde :")

        # Par sécurité, Entrée annule : il faut cliquer sur Oui.
        if vPassword is not None and (
            QMessageBox.warning(
                self,
                "Restaurer la sauvegarde chiffrée",
                "Les données actuelles seront remplacées par celles de la clé. "
                "Elles sont d'abord sauvegardées dans data/backups. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.restore_from_usb(vPath, vPassword)

    def restore_from_usb(self, pPath, pPassword):
        """Restaure la copie chiffrée ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = restore_encrypted_archive(
                self.database_file, pPath, pPassword, datetime.now()
            )

        except ValueError as vException:
            logger.warning("Restauration chiffrée refusée : %s", vException)

            show_message(self.usb_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de la restauration chiffrée")

            show_message(
                self.usb_message,
                "La restauration a échoué. Voir les journaux.",
                "danger",
            )

        else:
            self.data_reset.emit(
                f"Sauvegarde chiffrée restaurée. Anciennes données : {vBackupFile.name}"
            )

    def create_reset_card(self):
        """Construit la réinitialisation des données, précédée d'une sauvegarde."""
        vCard, vLayout = create_card(
            "Réinitialisation",
            "Efface les offres, candidatures, relances, historique, réglages et "
            "recherches enregistrées. Les questions de révision sont conservées. "
            "Une sauvegarde de la base est faite juste avant.",
        )

        self.reset_button = create_button(
            "Réinitialiser les données",
            "circle-alert",
            "dangerButton",
            COLORS["danger"],
        )
        self.reset_button.clicked.connect(self.confirm_reset)

        self.reset_message = QLabel()
        self.reset_message.setObjectName("cardSubtitle")
        self.reset_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.reset_button)
        vActions.addWidget(self.reset_message, 1)

        vLayout.addLayout(vActions)

        return vCard

    def confirm_reset(self):
        """Demande confirmation, puis réinitialise les données."""
        vDialog = QMessageBox(self)
        vDialog.setIcon(QMessageBox.Icon.Warning)
        vDialog.setWindowTitle("Réinitialiser les données")
        vDialog.setText("Toutes les données de l'application vont être effacées.")
        vDialog.setInformativeText(
            "Offres, candidatures, relances, historique, réglages, recherches "
            "enregistrées et planifiée, adresse de notification, progression de "
            "révision. Les questions de révision importées sont conservées. Une "
            "sauvegarde de la base est faite avant, dans data/backups. Continuer ?"
        )

        vConfirmButton = vDialog.addButton(
            "Réinitialiser", QMessageBox.ButtonRole.DestructiveRole
        )
        vCancelButton = vDialog.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)

        # Par sécurité, Entrée annule : il faut cliquer sur Réinitialiser.
        vDialog.setDefaultButton(vCancelButton)
        vDialog.exec()

        if vDialog.clickedButton() is vConfirmButton:
            self.reset_data()

    def reset_data(self):
        """Sauvegarde puis efface les données ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = reset_database(self.database_file, datetime.now())

        except Exception:
            logger.exception("Échec de la réinitialisation des données")

            show_message(
                self.reset_message,
                "La réinitialisation a échoué, aucune donnée n'a été effacée "
                "si la sauvegarde n'a pas pu être faite. Voir les journaux.",
                "danger",
            )

        else:
            # Les pages sont reconstruites : le message est affiché sur la nouvelle.
            self.data_reset.emit(
                f"Données réinitialisées. Sauvegarde : {vBackupFile.name}"
            )

    def set_actions_enabled(self, pEnabled):
        """Bloque les restaurations et la réinitialisation pendant une recherche."""
        self.reset_button.setEnabled(pEnabled)
        self.restore_archive_button.setEnabled(pEnabled)
        self.restore_backup_button.setEnabled(
            pEnabled and self.backups_combo.currentData() is not None
        )
