"""Ajout de questions de révision : thèmes prioritaires, ChatGPT, import et export"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs import show_text_dialog
from gui.theme import COLORS
from gui.widgets import clear_layout, create_button, create_card, show_message
from job.assistant import CHATGPT_URL
from job.quiz import load_active_quiz
from job.quiz_generation import (
    DEFAULT_GENERATION_COUNT,
    GENERATION_COUNTS,
    GENERATION_LEVELS,
    MIXED_LEVEL,
    TARGET_QUESTIONS,
    build_correction_prompt,
    build_generation_prompt,
    build_priority_themes,
    list_generation_themes,
)
from job.quiz_import import (
    IMPORT_EXTENSIONS,
    clear_imported_questions,
    describe_import_details,
    describe_quiz_import,
    export_quiz_pack,
    get_import_tone,
    import_questions,
    import_questions_file,
)
from job.quiz_packs import import_validated_packs, list_validated_packs
from utils.logger import get_logger

logger = get_logger(__name__)


class QuizImportPanel(QWidget):
    """Cartes « À compléter en priorité » et « Ajouter des questions » de la révision.

    Le panneau ne connaît pas la page : il signale par questions_changed qu'il
    faut relire les thèmes, et par questions_cleared que la question affichée
    n'existe peut-être plus.
    """

    questions_changed = Signal()
    questions_cleared = Signal()

    def __init__(self, pDatabaseFile):
        """Construit les deux cartes ; leur contenu est rempli par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(18)
        vLayout.addWidget(self.create_priority_card())
        vLayout.addWidget(self.create_import_card())

    def refresh(self, pThemes):
        """Met à jour la liste des thèmes proposés et les thèmes prioritaires."""
        vCurrent = self.theme_combo.currentText()
        self.theme_combo.clear()
        self.theme_combo.addItems(list_generation_themes(pThemes))
        self.theme_combo.setCurrentText(vCurrent)

        self.show_priorities()

    def create_import_card(self):
        """Construit la génération de questions avec ChatGPT et leur import."""
        self.theme_combo = QComboBox()
        self.theme_combo.setEditable(True)
        self.theme_combo.setToolTip(
            "Thème du catalogue, existant ou nouveau, par exemple Kafka"
        )

        self.level_combo = QComboBox()

        for vLevel, vLabel in GENERATION_LEVELS.items():
            self.level_combo.addItem(vLabel, vLevel)

        self.count_combo = QComboBox()

        for vCount in GENERATION_COUNTS:
            self.count_combo.addItem(f"{vCount} questions", vCount)

        self.count_combo.setCurrentIndex(
            self.count_combo.findData(DEFAULT_GENERATION_COUNT)
        )

        vGenerateButton = create_button(
            "Générer avec ChatGPT", "bot", "primaryButton", COLORS["on_primary"]
        )
        vGenerateButton.setToolTip(
            "Copie une demande au format attendu et ouvre ChatGPT"
        )
        vGenerateButton.clicked.connect(self.copy_generation_prompt)

        vOptions = QHBoxLayout()
        vOptions.addWidget(self.theme_combo, 2)
        vOptions.addWidget(self.level_combo, 1)
        vOptions.addWidget(self.count_combo, 1)
        vOptions.addWidget(vGenerateButton)

        self.import_edit = QPlainTextEdit()
        self.import_edit.setPlaceholderText(
            "Collez ici la réponse de ChatGPT (JSON), puis importez"
        )
        self.import_edit.setMaximumHeight(110)

        vPasteButton = create_button(
            "Importer le texte collé", "download", pIconColor=COLORS["primary"]
        )
        vPasteButton.clicked.connect(self.import_pasted_questions)

        vFileButton = create_button(
            "Importer un fichier…", "upload", pIconColor=COLORS["primary"]
        )
        vFileButton.setToolTip("Fichier .json, ou archive .zip de fichiers .json")
        vFileButton.clicked.connect(self.choose_questions_file)

        # Lots déjà contrôlés, déposés dans data/packs : un clic les importe tous.
        self.packs_button = create_button(
            "Importer les lots validés", "list-checks", pIconColor=COLORS["primary"]
        )
        self.packs_button.setToolTip(
            "Importe les archives « -valide.zip » du dossier des lots ; "
            "une archive déjà importée ne change rien"
        )
        self.packs_button.clicked.connect(self.import_packs)
        self.packs_button.hide()

        vExportButton = create_button(
            "Exporter mes questions…", "download", pIconColor=COLORS["primary"]
        )
        vExportButton.setToolTip(
            "Pack .zip des questions importées, schémas et guides, réimportable"
        )
        vExportButton.clicked.connect(self.choose_export_file)

        self.import_message = QLabel()
        self.import_message.setObjectName("cardSubtitle")
        self.import_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vPasteButton)
        vActions.addWidget(vFileButton)
        vActions.addWidget(self.packs_button)
        vActions.addWidget(vExportButton)

        vClearButton = create_button(
            "Supprimer les questions importées",
            "trash-2",
            "dangerButton",
            COLORS["danger"],
        )
        vClearButton.setToolTip(
            "Efface les questions importées, leurs schémas, guides et réponses ; "
            "les questions livrées sont gardées"
        )
        vClearButton.clicked.connect(self.confirm_clear_questions)
        vActions.addWidget(vClearButton)
        vActions.addWidget(self.import_message, 1)

        # Le message reste court ; le détail d'un gros import s'ouvre à part.
        self.import_details = ""
        self.details_button = create_button("Voir le détail", "file-text")
        self.details_button.clicked.connect(
            lambda: show_text_dialog(
                self, "Détail de l'import", pText=self.import_details
            )
        )
        self.details_button.hide()
        vActions.addWidget(self.details_button)

        # Un lot qui ne respecte pas la demande repart chez ChatGPT, alertes jointes.
        self.import_review = []
        self.correction_button = create_button(
            "Faire corriger par ChatGPT", "bot", pIconColor=COLORS["warning"]
        )
        self.correction_button.setToolTip(
            "Copie une demande de correction des questions signalées et ouvre ChatGPT"
        )
        self.correction_button.clicked.connect(self.copy_correction_prompt)
        self.correction_button.hide()
        vActions.addWidget(self.correction_button)

        vCard, vLayout = create_card(
            "Ajouter des questions",
            "Générées avec votre compte ChatGPT, puis vérifiées une à une à "
            "l'import : une question incomplète ou en double est écartée.",
        )
        vLayout.addLayout(vOptions)
        vLayout.addWidget(self.import_edit)
        vLayout.addLayout(vActions)

        return vCard

    def copy_generation_prompt(self):
        """Copie la demande de questions pour ChatGPT puis ouvre le site."""
        vTheme = self.theme_combo.currentText().strip()

        if not vTheme:
            show_message(
                self.import_message, "Choisissez ou saisissez un thème.", "warning"
            )
            return

        QApplication.clipboard().setText(
            build_generation_prompt(
                load_active_quiz(self.database_file),
                vTheme,
                self.level_combo.currentData(),
                self.count_combo.currentData(),
            )
        )
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        show_message(
            self.import_message,
            "Demande copiée : collez-la dans ChatGPT, puis sa réponse ci-dessus.",
        )

    def copy_correction_prompt(self):
        """Copie la demande de correction du dernier lot importé puis ouvre ChatGPT."""
        QApplication.clipboard().setText(build_correction_prompt(self.import_review))
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        show_message(
            self.import_message,
            "Demande de correction copiée : importez ensuite le lot corrigé, "
            "il remplacera les questions signalées.",
        )

    def create_priority_card(self):
        """Construit la liste des thèmes à compléter en priorité."""
        vCard, vLayout = create_card(
            "À compléter en priorité",
            "Thèmes les plus demandés dans vos offres, encore loin de "
            f"{TARGET_QUESTIONS} questions",
        )
        self.priority_message = QLabel()
        self.priority_message.setObjectName("cardSubtitle")
        self.priority_message.setWordWrap(True)
        self.priority_layout = QGridLayout()
        self.priority_layout.setHorizontalSpacing(12)
        self.priority_layout.setColumnStretch(0, 1)

        vLayout.addWidget(self.priority_message)
        vLayout.addLayout(self.priority_layout)

        return vCard

    def show_priorities(self):
        """Affiche les thèmes prioritaires, chacun avec sa demande ChatGPT."""
        clear_layout(self.priority_layout)

        try:
            vPriorities = build_priority_themes(
                self.database_file, load_active_quiz(self.database_file)
            )

        except Exception:
            logger.exception("Impossible de calculer les thèmes prioritaires")

            show_message(
                self.priority_message,
                "Les priorités n'ont pas pu être calculées.",
                "danger",
            )
            return

        show_message(
            self.priority_message,
            (
                ""
                if vPriorities
                else "Aucun thème n'est encore demandé dans vos offres : lancez une "
                "recherche pour mesurer la demande."
            ),
            None,
        )

        for vRow, vTheme in enumerate(vPriorities):
            vTitle = QLabel(f"<b>{escape(vTheme['label'])}</b>")
            vDetail = QLabel(
                f"<span style='color:{COLORS['primary']}; font-weight:600'>"
                f"demandé dans {vTheme['offer_count']} offre(s)</span>"
                f" · {vTheme['questions']} question(s)"
            )
            vButton = create_button(
                "Préparer la demande", "bot", pIconColor=COLORS["primary"]
            )
            vButton.setToolTip(
                f"Copie la demande de {TARGET_QUESTIONS} questions pour ce thème "
                "et ouvre ChatGPT"
            )
            vButton.clicked.connect(
                lambda _, pLabel=vTheme["label"]: self.prepare_priority(pLabel)
            )

            self.priority_layout.addWidget(vTitle, vRow, 0)
            self.priority_layout.addWidget(vDetail, vRow, 1)
            self.priority_layout.addWidget(vButton, vRow, 2)

    def prepare_priority(self, pThemeLabel):
        """Prépare la demande d'un lot complet pour un thème prioritaire."""
        self.theme_combo.setCurrentText(pThemeLabel)
        self.level_combo.setCurrentIndex(self.level_combo.findData(MIXED_LEVEL))
        self.count_combo.setCurrentIndex(
            self.count_combo.findData(DEFAULT_GENERATION_COUNT)
        )
        self.copy_generation_prompt()

    def import_packs(self):
        """Importe d'un coup toutes les archives validées du dossier des lots."""
        self.run_import(
            lambda: import_validated_packs(self.database_file, datetime.now())
        )

    def refresh_packs_button(self):
        """Affiche le nombre d'archives validées prêtes à importer."""
        vCount = len(list_validated_packs())

        self.packs_button.setText(f"Importer les lots validés ({vCount})")
        self.packs_button.setVisible(bool(vCount))

    def import_pasted_questions(self):
        """Importe les questions collées dans la zone de texte."""
        self.run_import(
            lambda: import_questions(
                self.database_file,
                self.theme_combo.currentText(),
                self.import_edit.toPlainText(),
                datetime.now(),
            )
        )

    def choose_questions_file(self):
        """Demande le fichier de questions à importer."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer des questions",
            str(Path.home()),
            "Questions ("
            + " ".join(f"*{vExtension}" for vExtension in IMPORT_EXTENSIONS)
            + ")",
        )

        if vPath:
            self.run_import(
                lambda: import_questions_file(
                    self.database_file,
                    self.theme_combo.currentText(),
                    vPath,
                    Path(vPath).read_bytes(),
                    datetime.now(),
                )
            )

    def choose_export_file(self):
        """Demande où enregistrer le pack de questions, puis l'écrit."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter mes questions",
            str(Path.home() / f"questions-revision-{datetime.now():%Y%m%d}.zip"),
            "Archive (*.zip)",
        )

        if vPath:
            self.export_questions(vPath)

    def export_questions(self, pPath):
        """Écrit les questions importées dans un pack réimportable."""
        try:
            vCount = export_quiz_pack(self.database_file, pPath)

        except ValueError as vException:
            show_message(self.import_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de l'export des questions de révision")

            show_message(
                self.import_message, "L'export a échoué. Voir les journaux.", "danger"
            )

        else:
            show_message(
                self.import_message,
                f"{vCount} question(s) exportée(s) : {Path(pPath).name}",
            )

    def confirm_clear_questions(self):
        """Demande confirmation, puis efface toutes les questions importées."""
        vDialog = QMessageBox(self)
        vDialog.setIcon(QMessageBox.Icon.Warning)
        vDialog.setWindowTitle("Supprimer les questions importées")
        vDialog.setText("Toutes les questions importées vont être effacées.")
        vDialog.setInformativeText(
            "Avec leurs thèmes, schémas, guides et vos réponses à ces questions. "
            "Les questions livrées avec l'application sont gardées. Une sauvegarde "
            "de la base est faite avant ; « Exporter mes questions » permet aussi de "
            "les garder dans un fichier. Continuer ?"
        )

        vConfirmButton = vDialog.addButton(
            "Supprimer", QMessageBox.ButtonRole.DestructiveRole
        )
        vCancelButton = vDialog.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)

        # Par sécurité, Entrée annule : il faut cliquer sur Supprimer.
        vDialog.setDefaultButton(vCancelButton)
        vDialog.exec()

        if vDialog.clickedButton() is vConfirmButton:
            self.clear_questions()

    def clear_questions(self):
        """Efface les questions importées après sauvegarde, puis prévient la page."""
        try:
            vCount, vBackupFile = clear_imported_questions(
                self.database_file, datetime.now()
            )

        except Exception:
            logger.exception("Échec de l'effacement des questions importées")

            show_message(
                self.import_message,
                "L'effacement a échoué ; rien n'a été effacé sans sauvegarde. "
                "Voir les journaux.",
                "danger",
            )
            return

        self.questions_cleared.emit()

        show_message(
            self.import_message,
            f"{vCount} question(s) importée(s) effacée(s). Sauvegarde : "
            f"{vBackupFile.name}",
        )

    def run_import(self, pImport):
        """Lance un import, affiche son bilan et fait relire les thèmes."""
        try:
            vReport = pImport()

        except ValueError as vException:
            show_message(self.import_message, str(vException), "warning")
            return

        except Exception:
            logger.exception("Échec de l'import de questions de révision")

            show_message(
                self.import_message, "L'import a échoué. Voir les journaux.", "danger"
            )
            return

        show_message(
            self.import_message,
            describe_quiz_import(vReport),
            get_import_tone(vReport),
        )
        self.import_details = describe_import_details(vReport)
        self.details_button.setVisible(bool(self.import_details))
        self.import_review = vReport["review"]
        self.correction_button.setVisible(bool(self.import_review))

        if vReport["added"]:
            self.import_edit.clear()

        self.questions_changed.emit()
