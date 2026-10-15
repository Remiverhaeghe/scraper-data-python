"""Page de révision technique : thèmes, questions à choix multiple et corrections"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.dialogs import show_text_dialog
from gui.icons import get_icon
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    clear_layout,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.assistant import CHATGPT_URL
from job.quiz_types import BLANK, DEFAULT_TOLERANCE, format_number
from job.quiz import (
    DEFAULT_MODE,
    QUIZ_MODES,
    THEME_STATUSES,
    answer_question,
    build_quiz_overview,
    build_quiz_statistics,
    describe_no_question,
    get_next_review,
    get_review_schedule,
    flag_question,
    load_active_quiz,
    pick_question,
)
from job.quiz_domains import (
    DOMAIN_ICONS,
    build_category_progress,
    filter_guides,
    group_themes,
)
from job.quiz_exam import (
    EXAM_QUESTION_COUNT,
    answer_exam,
    describe_exam_summary,
    get_exam_question,
    load_exam,
    start_exam,
    stop_exam,
    summarize_exam,
)
from job.quiz_generation import (
    DEFAULT_GENERATION_COUNT,
    GENERATION_COUNTS,
    GENERATION_LEVELS,
    MIXED_LEVEL,
    TARGET_QUESTIONS,
    build_priority_themes,
    build_correction_prompt,
    build_generation_prompt,
    list_generation_themes,
)
from job.quiz_import import (
    IMPORT_EXTENSIONS,
    clear_imported_questions,
    describe_import_details,
    describe_quiz_import,
    get_import_tone,
    export_quiz_pack,
    import_questions,
    import_questions_file,
)
from job.presentation import CHART_PALETTE
from job.quiz_packs import import_validated_packs, list_validated_packs
from storage.quiz_answers import get_last_answers
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from utils.markdown import render_markdown
from utils.logger import get_logger

logger = get_logger(__name__)

THEME_COLUMNS = 3

# Mode de la page pendant un examen, à côté des modes de révision
EXAM_MODE = "exam"

# Colonnes du tableau de progression par catégorie
PROGRESS_COLUMNS = ["Catégorie", "Thèmes", "Acquises", "Progression", "À revoir"]
PROGRESS_BAR_WIDTH = 140
PROGRESS_BAR_HEIGHT = 14

# Largeur du panneau des catégories, à gauche des thèmes
CATEGORY_WIDTH = 270

# Hauteur d'affichage des schémas des questions importées
VISUAL_HEIGHT = 280


class QuizPage(QWidget):
    """Propose des questions par thème et suit la progression."""

    def __init__(self, pDatabaseFile):
        """Construit la carte de question, masquée, puis la liste des thèmes."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.theme_key = None
        self.mode = None
        self.question = None

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Révision",
            "QCM techniques pour préparer les entretiens, thèmes conseillés selon "
            "vos offres",
            pIcon="graduation-cap",
        )

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.hide()

        # Catégorie affichée : domaine puis sous-domaine, None pour tout montrer
        self.domain = None
        self.subdomain = None
        self.themes = []

        # Catégories en arborescence, toujours visibles à gauche des thèmes
        # Catégories en liste verticale, toujours visibles à gauche des thèmes :
        # domaines puis sous-domaines en retrait, chacun avec son icône.
        self.category_buttons = {}
        self.category_card = QFrame()
        self.category_card.setObjectName("card")
        self.category_card.setFixedWidth(CATEGORY_WIDTH)
        self.category_layout = QVBoxLayout(self.category_card)
        self.category_layout.setContentsMargins(10, 10, 10, 10)
        self.category_layout.setSpacing(2)

        self.filter_label = QLabel()
        self.filter_label.setObjectName("cardTitle")

        self.exam_button = create_button(
            "", "timer", "primaryButton", COLORS["on_primary"]
        )
        self.exam_button.setToolTip(
            "Questions tirées au hasard dans la catégorie choisie, notées et "
            "chronométrées"
        )
        self.exam_button.clicked.connect(self.start_exam)

        vHeader = QHBoxLayout()
        vHeader.addWidget(self.filter_label, 1)
        vHeader.addWidget(self.exam_button)

        # Les thèmes sont reconstruits à chaque rafraîchissement dans un conteneur
        # remplacé d'un bloc : domaines et sous-domaines y sont imbriqués.
        self.themes_holder = QVBoxLayout()
        self.themes_holder.setContentsMargins(0, 0, 0, 0)

        vThemesColumn = QVBoxLayout()
        vThemesColumn.setSpacing(12)
        vThemesColumn.addLayout(vHeader)
        vThemesColumn.addLayout(self.themes_holder)

        vBody = QHBoxLayout()
        vBody.setSpacing(18)
        vBody.addWidget(self.category_card, 0, Qt.AlignmentFlag.AlignTop)
        vBody.addLayout(vThemesColumn, 1)

        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.create_question_card())
        vLayout.addLayout(vBody)

        # Guides pratiques des packs importés, masqués tant qu'il n'y en a pas
        self.guides_card, vGuidesLayout = create_card(
            "Guides pratiques", "Méthodes de diagnostic livrées avec les questions"
        )
        # Plusieurs guides par ligne, sans déborder dans une fenêtre réduite
        self.guides_layout = QGridLayout()
        self.guides_layout.setSpacing(8)
        vGuidesLayout.addLayout(self.guides_layout)
        self.guides_card.hide()

        vLayout.addWidget(self.guides_card)
        vLayout.addWidget(self.create_priority_card())
        vLayout.addWidget(self.create_import_card())
        vLayout.addWidget(self.create_statistics_card())
        # Facteur 1 : la place libre d'une page courte va ici, et non aux cartes
        # qui contiennent une zone de texte extensible.
        vLayout.addStretch(1)

    def create_question_card(self):
        """Construit la carte de la question, de ses choix et de sa correction."""
        self.question_card, vLayout = create_card()
        self.question_card.hide()

        self.meta_label = QLabel()
        self.meta_label.setObjectName("cardSubtitle")

        self.question_label = QLabel()
        self.question_label.setObjectName("cardTitle")
        self.question_label.setWordWrap(True)

        self.code_edit = QPlainTextEdit()
        self.code_edit.setReadOnly(True)
        self.code_edit.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.code_edit.setMaximumHeight(160)

        self.choices_group = QButtonGroup(self)
        self.answer_widgets = []

        self.choices_layout = QVBoxLayout()
        self.choices_layout.setSpacing(8)

        self.verdict_label = QLabel()
        self.verdict_label.setWordWrap(True)

        self.explanation_label = QLabel()
        self.explanation_label.setWordWrap(True)

        # Schéma et références des questions importées, montrés avec la correction
        self.visual_widget = QSvgWidget()
        # Schémas dessinés en sombre sur blanc : fond blanc, même en thème sombre.
        self.visual_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.visual_widget.setStyleSheet("background: #ffffff; border-radius: 8px;")
        self.visual_widget.hide()

        self.references_label = QLabel()
        self.references_label.setTextFormat(Qt.TextFormat.RichText)
        self.references_label.setOpenExternalLinks(True)
        self.references_label.setWordWrap(True)
        self.references_label.hide()

        self.validate_button = create_button("Valider", pObjectName="primaryButton")
        self.validate_button.clicked.connect(self.validate)

        self.next_button = create_button(
            "Question suivante", "arrow-right", pIconColor=COLORS["primary"]
        )
        self.next_button.clicked.connect(self.go_next)

        self.stop_exam_button = create_button("Abandonner l'examen")
        self.stop_exam_button.clicked.connect(self.close_exam)
        self.stop_exam_button.hide()

        # Une question importée peut être fausse : elle sort des tirages.
        self.flag_button = create_button(
            "Question douteuse", "circle-alert", pIconColor=COLORS["warning"]
        )
        self.flag_button.setToolTip("Retire cette question des prochains tirages")
        self.flag_button.clicked.connect(self.flag_current_question)

        vButtons = QHBoxLayout()
        vButtons.addWidget(self.validate_button)
        vButtons.addWidget(self.next_button)
        vButtons.addStretch()
        vButtons.addWidget(self.stop_exam_button)
        vButtons.addWidget(self.flag_button)

        vLayout.addWidget(self.meta_label)
        vLayout.addWidget(self.question_label)
        vLayout.addWidget(self.code_edit)
        vLayout.addLayout(self.choices_layout)
        vLayout.addWidget(self.verdict_label)
        vLayout.addWidget(self.explanation_label)
        vLayout.addWidget(self.visual_widget)
        vLayout.addWidget(self.references_label)
        vLayout.addLayout(vButtons)

        return self.question_card

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
        """Efface les questions importées après sauvegarde, puis met la page à jour."""
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

        self.mode = None
        self.question_card.hide()
        self.refresh()

        show_message(
            self.import_message,
            f"{vCount} question(s) importée(s) effacée(s). Sauvegarde : "
            f"{vBackupFile.name}",
        )

    def run_import(self, pImport):
        """Lance un import, affiche son bilan et met à jour les thèmes."""
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

        self.refresh()

    def flag_current_question(self):
        """Retire la question affichée des tirages, après confirmation."""
        if (
            QMessageBox.question(
                self,
                "Question douteuse",
                "Cette question ne sera plus proposée. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        flag_question(self.database_file, self.question["id"])

        self.refresh()
        self.start(self.theme_key, self.mode)

    def create_statistics_card(self):
        """Construit les chiffres de la révision et le graphique des derniers jours."""
        self.statistic_cards = {
            "acquired": StatisticCard("Questions acquises", "circle-check", "green"),
            "answers": StatisticCard("Réponses données", "graduation-cap", "blue"),
            "rate": StatisticCard("Bonnes réponses", "sparkles", "purple"),
            "streak": StatisticCard("Jours de révision d'affilée", "calendar", "amber"),
        }

        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.statistic_cards.values():
            vCards.addWidget(vCard, 1)

        self.statistics_chart = BarChart()

        # Progression par catégorie : domaines puis sous-domaines, sans le détail
        # des thèmes pour rester lisible.
        self.progress_tree = QTreeWidget()
        self.progress_tree.setObjectName("progressTree")
        self.progress_tree.setColumnCount(len(PROGRESS_COLUMNS))
        self.progress_tree.setHeaderLabels(PROGRESS_COLUMNS)
        self.progress_tree.setIconSize(QSize(16, 16))
        self.progress_tree.setUniformRowHeights(True)
        self.progress_tree.setRootIsDecorated(True)
        self.progress_tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.progress_tree.header().setStretchLastSection(False)
        self.progress_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

        for vColumn in range(1, len(PROGRESS_COLUMNS)):
            self.progress_tree.header().setSectionResizeMode(
                vColumn, QHeaderView.ResizeMode.ResizeToContents
            )

        vProgressTitle = QLabel("Progression par catégorie")
        vProgressTitle.setObjectName("fieldLabel")

        vCard, vLayout = create_card(
            "Mes statistiques", "Progression globale et réponses des 14 derniers jours"
        )
        vLayout.addLayout(vCards)
        vLayout.addWidget(vProgressTitle)
        vLayout.addWidget(self.progress_tree)
        vLayout.addWidget(self.statistics_chart)

        return vCard

    def show_category_progress(self, pThemes):
        """Remplit le tableau de progression par domaine et sous-domaine."""
        self.progress_tree.clear()

        vDomainItem = None

        for vRow in build_category_progress(pThemes):
            vItem = QTreeWidgetItem(
                [
                    vRow["label"],
                    str(vRow["themes"]),
                    f"{vRow['correct']} / {vRow['total']}",
                    "",
                    str(vRow["due"]) if vRow["due"] else "",
                ]
            )
            vItem.setIcon(
                0,
                get_icon(
                    vRow["icon"],
                    COLORS["primary"] if vRow["level"] == 0 else COLORS["muted"],
                    16,
                ),
            )
            vItem.setForeground(4, QColor(COLORS["warning"]))

            if vRow["level"] == 0:
                vFont = vItem.font(0)
                vFont.setBold(True)
                vItem.setFont(0, vFont)
                self.progress_tree.addTopLevelItem(vItem)
                vDomainItem = vItem
            else:
                vDomainItem.addChild(vItem)

            vBar = QProgressBar()
            vBar.setValue(vRow["score"])
            vBar.setFormat(f"{vRow['score']} %")
            vBar.setFixedSize(PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT)
            self.progress_tree.setItemWidget(vItem, 3, vBar)

        self.progress_tree.expandAll()

        # Toutes les lignes visibles : la page défile, pas le tableau.
        vRows = sum(
            1 + self.progress_tree.topLevelItem(vIndex).childCount()
            for vIndex in range(self.progress_tree.topLevelItemCount())
        )
        self.progress_tree.setFixedHeight(
            self.progress_tree.header().sizeHint().height()
            + vRows * self.progress_tree.sizeHintForRow(0)
            + 8
        )

    def show_statistics(self, pStatistics):
        """Affiche les chiffres de la révision et le graphique des derniers jours."""
        vCards = self.statistic_cards

        vCards["acquired"].set_value(
            f"{pStatistics['acquired']} / {pStatistics['total']}"
        )
        vCards["answers"].set_value(str(pStatistics["answers"]))
        vCards["rate"].set_value(
            "-" if pStatistics["rate"] is None else f"{pStatistics['rate']} %"
        )
        vCards["streak"].set_value(str(pStatistics["streak"]))

        self.statistics_chart.set_series(
            [f"{vDay:%d/%m}" for vDay, _, _ in pStatistics["days"]],
            [
                (
                    "Réponses",
                    CHART_PALETTE[0],
                    [vCount for _, vCount, _ in pStatistics["days"]],
                ),
                (
                    "Bonnes réponses",
                    CHART_PALETTE[1],
                    [vCorrect for _, _, vCorrect in pStatistics["days"]],
                ),
            ],
            pAxes=("Jour", "Réponses par jour"),
            pEmptyText="Aucune réponse ces 14 derniers jours",
        )

    def refresh(self):
        """Relit la progression et reconstruit les cartes des thèmes."""
        self.refresh_packs_button()

        try:
            vThemes = build_quiz_overview(
                self.database_file, load_active_quiz(self.database_file)
            )
            self.show_statistics(
                build_quiz_statistics(self.database_file, vThemes, datetime.now())
            )

        except Exception:
            logger.exception("Impossible de charger la révision")

            show_message(
                self.message_label,
                "Les questions n'ont pas pu être chargées.",
                "danger",
            )
            self.message_label.show()
            return

        vCurrent = self.theme_combo.currentText()
        self.theme_combo.clear()
        self.theme_combo.addItems(list_generation_themes(vThemes))
        self.theme_combo.setCurrentText(vCurrent)

        self.themes = vThemes
        self.show_category_progress(vThemes)
        self.show_priorities()
        self.select_category(self.domain, self.subdomain)

    def refresh_categories(self):
        """Reconstruit la liste des domaines et sous-domaines, avec leurs comptes."""
        clear_layout(self.category_layout)
        self.category_buttons = {}

        vEntries = [
            ((None, None), "graduation-cap", f"Tous les thèmes ({len(self.themes)})")
        ]

        for vDomain, vSections in group_themes(self.themes):
            vCount = sum(len(vThemes) for _, vThemes in vSections)
            vEntries.append(
                (
                    (vDomain, None),
                    DOMAIN_ICONS.get(vDomain, "sparkles"),
                    f"{vDomain} ({vCount})",
                )
            )
            vEntries += [
                (
                    (vDomain, vSubdomain),
                    DOMAIN_ICONS.get(vSubdomain, "tag"),
                    f"{vSubdomain} ({len(vThemes)})",
                )
                for vSubdomain, vThemes in vSections
            ]

        # Catégorie disparue (dernier thème supprimé) : retour à l'ensemble.
        if (self.domain, self.subdomain) not in [vKey for vKey, _, _ in vEntries]:
            self.domain, self.subdomain = None, None

        for vKey, vIcon, vText in vEntries:
            vChild = vKey[1] is not None
            vButton = create_button(
                vText,
                vIcon,
                "categoryChildButton" if vChild else "categoryButton",
                COLORS["muted"] if vChild else COLORS["primary"],
            )
            vButton.setCheckable(True)
            vButton.setChecked(vKey == (self.domain, self.subdomain))
            vButton.clicked.connect(
                lambda _=False, pKey=vKey: self.on_category_clicked(pKey)
            )
            self.category_buttons[vKey] = vButton
            self.category_layout.addWidget(vButton)

    def on_category_clicked(self, pCategory):
        """Filtre sur la catégorie cliquée ; un second clic revient à l'ensemble."""
        vCategory = (
            (None, None) if pCategory == (self.domain, self.subdomain) else pCategory
        )

        self.select_category(*vCategory)

    def select_category(self, pDomain, pSubdomain=None):
        """Affiche les thèmes, guides et l'examen d'une catégorie, ou de toutes."""
        self.domain = pDomain
        self.subdomain = pSubdomain

        self.refresh_categories()
        self.refresh_exam_button()
        self.refresh_guides()
        self.show_themes()

    def select_domain(self, pDomain):
        """Limite l'affichage des thèmes à un domaine, ou les montre tous."""
        self.select_category(pDomain)

    def select_subdomain(self, pSubdomain):
        """Limite l'affichage aux thèmes d'un sous-domaine du domaine choisi."""
        self.select_category(self.domain, pSubdomain)

    def refresh_exam_button(self):
        """Propose de reprendre l'examen en cours, ou d'en commencer un."""
        vExam = load_exam(self.database_file)

        self.exam_button.setText(
            f"Reprendre l'examen ({vExam['index'] + 1} / {len(vExam['ids'])})"
            if vExam and not vExam["finished_at"]
            else f"Mode examen ({EXAM_QUESTION_COUNT} questions)"
        )
        self.filter_label.setText(
            " › ".join(vPart for vPart in (self.domain, self.subdomain) if vPart)
            or "Tous les thèmes"
        )

    def show_themes(self):
        """Affiche les thèmes du domaine choisi, rangés par sous-domaine."""
        clear_layout(self.themes_holder)

        vContainer = QWidget()
        vLayout = QVBoxLayout(vContainer)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(12)

        for vDomain, vSections in group_themes(
            self.themes, self.domain, self.subdomain
        ):
            vLayout.addWidget(self.create_domain_header(vDomain, vSections))

            for vSubdomain, vThemes in vSections:
                vSubtitle = self.create_subdomain_badge(vSubdomain, len(vThemes))

                vGrid = QGridLayout()
                vGrid.setSpacing(16)

                for vColumn in range(THEME_COLUMNS):
                    vGrid.setColumnStretch(vColumn, 1)

                for vIndex, vTheme in enumerate(vThemes):
                    vGrid.addWidget(
                        self.create_theme_card(vTheme), *divmod(vIndex, THEME_COLUMNS)
                    )

                vLayout.addWidget(vSubtitle, 0, Qt.AlignmentFlag.AlignLeft)
                vLayout.addLayout(vGrid)

        self.themes_holder.addWidget(vContainer)

    def create_subdomain_badge(self, pSubdomain, pCount):
        """Crée le badge d'un sous-domaine : icône, nom et nombre de thèmes."""
        rBadge = QFrame()
        rBadge.setObjectName("subdomainBadge")

        vText = QLabel(f"{pSubdomain} · {pCount}")
        vText.setObjectName("subdomainBadgeText")

        vLayout = QHBoxLayout(rBadge)
        vLayout.setContentsMargins(10, 3, 12, 3)
        vLayout.setSpacing(6)
        vLayout.addWidget(
            create_icon_label(
                DOMAIN_ICONS.get(pSubdomain, "tag"), COLORS["primary"], 14
            )
        )
        vLayout.addWidget(vText)

        return rBadge

    def create_domain_header(self, pDomain, pSections):
        """Crée l'en-tête d'un domaine : icône, nom et progression d'ensemble."""
        vThemes = [vTheme for _, vThemes in pSections for vTheme in vThemes]

        vTitle = QLabel(pDomain)
        vTitle.setObjectName("cardTitle")

        vSummary = QLabel(
            f"{len(vThemes)} thème(s) · "
            f"{sum(vTheme['correct'] for vTheme in vThemes)} / "
            f"{sum(vTheme['total'] for vTheme in vThemes)} questions acquises"
        )
        vSummary.setObjectName("cardSubtitle")

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(vSummary)

        rHeader = QWidget()
        vLayout = QHBoxLayout(rHeader)
        vLayout.setContentsMargins(0, 12, 0, 0)
        vLayout.setSpacing(12)
        vLayout.addWidget(
            create_icon_label(
                DOMAIN_ICONS.get(pDomain, "sparkles"), COLORS["primary"], 22
            )
        )
        vLayout.addLayout(vTexts, 1)

        return rHeader

    def create_theme_card(self, pTheme):
        """Crée la carte d'un thème : progression, intérêt et boutons."""
        rCard, vLayout = create_card()

        vTitle = QLabel(pTheme["label"])
        vTitle.setObjectName("cardTitle")
        vTitle.setWordWrap(True)

        vTitleRow = QHBoxLayout()
        vTitleRow.setSpacing(8)

        if pTheme["status"]:
            vIcon, vTone, vText = THEME_STATUSES[pTheme["status"]]
            vStatus = create_icon_label(vIcon, COLORS[vTone], 18)
            vStatus.setToolTip(vText)
            vTitleRow.addWidget(vStatus)

        vTitleRow.addWidget(vTitle, 1)
        vLayout.addLayout(vTitleRow)

        # Largeur fixée par la grille seule : les colonnes restent égales.
        rCard.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        # Les indications utiles ressortent en couleur : intérêt pour les offres
        # en bleu, révisions dues en orange.
        def highlight(pText, pTone):
            rHtml = (
                f'<span style="color: {COLORS[pTone]}; font-weight: 600;">'
                f"{escape(pText)}</span>"
            )

            return rHtml

        vParts = [escape(f"{pTheme['correct']} / {pTheme['total']} acquises")]

        if pTheme["to_review"]:
            vParts.append(escape(f"{pTheme['to_review']} ratée(s)"))

        if pTheme["due"]:
            vParts.append(highlight(f"{pTheme['due']} à revoir aujourd'hui", "warning"))

        vParts.append(
            highlight(f"demandé dans {pTheme['offer_count']} offre(s)", "primary")
            if pTheme["offer_count"]
            else escape("pas encore demandé dans vos offres")
        )

        vInfo = QLabel(" · ".join(vParts))
        vInfo.setTextFormat(Qt.TextFormat.RichText)
        vInfo.setObjectName("cardSubtitle")
        vInfo.setWordWrap(True)

        vProgress = QProgressBar()
        vProgress.setTextVisible(False)
        vProgress.setValue(pTheme["score"])

        vStart = create_button("Réviser", pObjectName="primaryButton")
        vStart.setToolTip(
            "Répétition espacée : questions à revoir aujourd'hui, puis nouvelles"
        )
        vStart.clicked.connect(lambda: self.start(pTheme["key"], DEFAULT_MODE))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vStart)

        if pTheme["to_review"]:
            vReview = create_button("Revoir les erreurs")
            vReview.clicked.connect(lambda: self.start(pTheme["key"], "review"))
            vButtons.addWidget(vReview)

        if pTheme["guide"]:
            vGuide = create_button("Guide", "file-text", pIconColor=COLORS["primary"])
            vGuide.clicked.connect(lambda: self.show_guide(pTheme["guide"]))
            vButtons.addWidget(vGuide)

        vButtons.addStretch()

        vLayout.addWidget(vInfo)
        vLayout.addWidget(vProgress)
        vLayout.addLayout(vButtons)

        return rCard

    def show_extras(self, pQuestion):
        """Affiche le schéma et les références d'une question, s'il y en a."""
        vVisual = pQuestion.get("visual")
        vContent = (
            get_quiz_asset(self.database_file, vVisual["asset"]) if vVisual else None
        )

        if vContent:
            self.visual_widget.load(QByteArray(vContent.encode("utf-8")))
            self.visual_widget.setToolTip(vVisual["alt"])

            # Chaque chargement remet le rendu à zéro : proportions et taille
            # d'origine sont réappliquées, à une hauteur fixe.
            vRenderer = self.visual_widget.renderer()
            vRenderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            vSize = vRenderer.defaultSize()
            self.visual_widget.setFixedSize(
                round(VISUAL_HEIGHT * vSize.width() / max(vSize.height(), 1)),
                VISUAL_HEIGHT,
            )

        self.visual_widget.setVisible(bool(vContent))

        vLinks = [
            f'<a href="{escape(vReference["url"])}">{escape(vReference["title"])}</a>'
            for vReference in pQuestion.get("references", [])
        ]

        self.references_label.setText("Pour aller plus loin : " + " · ".join(vLinks))
        self.references_label.setVisible(bool(vLinks))

    def show_guide(self, pName):
        """Ouvre un guide pratique, mis en forme."""
        vGuide = get_quiz_guide(self.database_file, pName)

        if vGuide:
            show_text_dialog(
                self, vGuide["title"], pHtml=render_markdown(vGuide["content"])
            )

    def refresh_guides(self):
        """Liste les guides pratiques importés avec les questions."""
        clear_layout(self.guides_layout)

        vGuides = filter_guides(
            get_quiz_guides(self.database_file),
            self.themes,
            self.domain,
            self.subdomain,
        )

        for vIndex, vGuide in enumerate(vGuides):
            vButton = create_button(
                vGuide["title"], "file-text", pIconColor=COLORS["primary"]
            )
            vButton.clicked.connect(
                lambda _=False, pName=vGuide["name"]: self.show_guide(pName)
            )
            self.guides_layout.addWidget(vButton, *divmod(vIndex, THEME_COLUMNS))

        self.guides_card.setVisible(bool(vGuides))

    def start(self, pThemeKey, pMode):
        """Affiche une nouvelle question du thème, ou signale qu'il n'y en a plus."""
        vQuiz = load_active_quiz(self.database_file)

        self.theme_key = pThemeKey
        self.mode = pMode
        vSchedule = get_review_schedule(self.database_file)
        vQuestion = pick_question(
            vQuiz,
            pThemeKey,
            pMode,
            get_last_answers(self.database_file),
            pSchedule=vSchedule,
        )

        self.display_question(
            vQuestion,
            (
                f"{vQuiz[pThemeKey]['label']} · {vQuestion['level']} · "
                f"{vQuestion['type_label']} · {QUIZ_MODES[pMode]}"
                if vQuestion
                else vQuiz[pThemeKey]["label"]
            ),
            describe_no_question(pMode, get_next_review(vQuiz, pThemeKey, vSchedule)),
        )

    def display_question(self, pQuestion, pMeta, pEmptyText):
        """Affiche une question et ses choix, ou pEmptyText s'il n'y en a pas."""
        self.question = pQuestion
        self.question_card.show()

        # La question s'affiche en haut de la page : on y remonte.
        self.findChild(QScrollArea).verticalScrollBar().setValue(0)
        self.verdict_label.clear()
        self.explanation_label.clear()
        self.visual_widget.hide()
        self.references_label.hide()
        self.next_button.hide()
        self.next_button.setText("Question suivante")
        self.stop_exam_button.setVisible(self.mode == EXAM_MODE)
        self.meta_label.setText(pMeta)

        clear_layout(self.choices_layout)
        self.answer_widgets = []

        for vButton in self.choices_group.buttons():
            self.choices_group.removeButton(vButton)

        if pQuestion is None:
            self.question_label.setText(pEmptyText)
            self.code_edit.hide()
            self.validate_button.hide()
            self.flag_button.hide()
            return

        self.question_label.setText(pQuestion["question"])
        self.code_edit.setPlainText(pQuestion.get("code", ""))
        self.code_edit.setVisible(bool(pQuestion.get("code")))
        self.validate_button.show()
        self.flag_button.setVisible(self.mode != EXAM_MODE)

        self.add_answer_widgets(pQuestion)

    def add_answer_widgets(self, pQuestion):
        """Ajoute la zone de réponse propre au type de la question."""
        vType = pQuestion["type"]

        if vType in ("numerique", "saisie"):
            vEdit = QLineEdit()
            vEdit.returnPressed.connect(self.validate)

            if vType == "saisie":
                vEdit.setPlaceholderText(f"Ce qui remplace {BLANK}")
                vEdit.setFont(
                    QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
                )
            else:
                vUnit = pQuestion.get("unit", "")
                vEdit.setPlaceholderText(f"Votre résultat, par exemple 2,5 {vUnit}")
                vEdit.setToolTip(
                    f"Tolérance "
                    f"{format_number(pQuestion.get('tolerance', DEFAULT_TOLERANCE))} %"
                    + (f", préfixes m, k, µ… acceptés devant {vUnit}" if vUnit else "")
                )

            self.answer_widgets = [vEdit]
        elif vType == "ordre":
            vList = QListWidget()
            vList.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            vList.setToolTip("Glissez les éléments pour les remettre dans l'ordre")

            for vIndex, vItem in pQuestion["shuffled"]:
                vListItem = QListWidgetItem(vItem)
                vListItem.setData(Qt.ItemDataRole.UserRole, vIndex)
                vList.addItem(vListItem)

            vList.setFixedHeight(vList.sizeHintForRow(0) * vList.count() + 8)
            self.answer_widgets = [vList]
        elif vType == "association":
            vContainer = QWidget()
            vGrid = QGridLayout(vContainer)
            vGrid.setContentsMargins(0, 0, 0, 0)

            for vRow, (vLeft, _) in enumerate(pQuestion["pairs"]):
                vCombo = QComboBox()
                vCombo.addItem("Choisir…", None)

                for vIndex, vRight in pQuestion["shuffled"]:
                    vCombo.addItem(vRight, vIndex)

                vGrid.addWidget(QLabel(vLeft), vRow, 0)
                vGrid.addWidget(vCombo, vRow, 1)
                self.answer_widgets.append(vCombo)

            self.choices_layout.addWidget(vContainer)
            return

        # L'identifiant du bouton est l'indice d'origine du choix, avant mélange.
        for vIndex, vChoice in pQuestion["shuffled"]:
            vButton = QRadioButton(vChoice)
            self.choices_group.addButton(vButton, vIndex)
            self.answer_widgets.append(vButton)

        for vWidget in self.answer_widgets:
            self.choices_layout.addWidget(vWidget)

    def read_response(self):
        """Retourne la réponse saisie selon le type, ou None si elle est incomplète."""
        vType = self.question["type"]

        if vType in ("numerique", "saisie"):
            rResponse = self.answer_widgets[0].text().strip() or None
        elif vType == "ordre":
            vList = self.answer_widgets[0]
            rResponse = [
                vList.item(vRow).data(Qt.ItemDataRole.UserRole)
                for vRow in range(vList.count())
            ]
        elif vType == "association":
            rResponse = [vCombo.currentData() for vCombo in self.answer_widgets]
            rResponse = None if None in rResponse else rResponse
        else:
            rResponse = self.choices_group.checkedId()
            rResponse = None if rResponse < 0 else rResponse

        return rResponse

    def start_exam(self):
        """Reprend l'examen en cours, ou en commence un sur le domaine choisi."""
        vExam = load_exam(self.database_file)

        if not vExam or vExam["finished_at"]:
            try:
                start_exam(
                    self.database_file,
                    load_active_quiz(self.database_file),
                    self.domain,
                    datetime.now(),
                    pSubdomain=self.subdomain,
                )

            except ValueError as vException:
                show_message(self.message_label, str(vException), "warning")
                self.message_label.show()
                return

        self.mode = EXAM_MODE
        self.show_exam_question()

    def show_exam_question(self):
        """Affiche la question en cours de l'examen, ou son résultat."""
        vQuiz = load_active_quiz(self.database_file)
        vExam = load_exam(self.database_file)

        if vExam and vExam["finished_at"]:
            self.display_question(
                None,
                "Examen terminé",
                describe_exam_summary(summarize_exam(vQuiz, vExam)),
            )
            self.stop_exam_button.setText("Fermer l'examen")
            return

        vQuestion = get_exam_question(vQuiz, vExam)

        self.stop_exam_button.setText("Abandonner l'examen")
        self.display_question(
            vQuestion,
            (
                f"Examen · question {vQuestion['position']} / {vQuestion['count']} · "
                f"{vQuestion['theme_label']} · {vQuestion['level']}"
                if vQuestion
                else "Examen"
            ),
            "Cette question n'existe plus : passez à la suivante.",
        )

    def close_exam(self):
        """Abandonne ou referme l'examen, puis revient à la liste des thèmes."""
        stop_exam(self.database_file)

        self.mode = None
        self.question_card.hide()
        self.refresh()

    def go_next(self):
        """Passe à la question suivante du thème ou de l'examen."""
        if self.mode == EXAM_MODE:
            self.show_exam_question()
        else:
            self.start(self.theme_key, self.mode)

    def validate(self):
        """Corrige la réponse choisie et affiche l'explication."""
        vResponse = self.read_response()

        if vResponse is None:
            show_message(self.verdict_label, "Complétez votre réponse.", "warning")
            return

        try:
            if self.mode == EXAM_MODE:
                vResult, vExam = answer_exam(
                    self.database_file,
                    load_active_quiz(self.database_file),
                    vResponse,
                    datetime.now(),
                )

                if vExam["finished_at"]:
                    self.next_button.setText("Voir le résultat")
            else:
                vResult = answer_question(
                    self.database_file,
                    load_active_quiz(self.database_file),
                    self.question["id"],
                    vResponse,
                    datetime.now(),
                )

        except ValueError as vException:
            show_message(self.verdict_label, str(vException), "warning")
            return

        # Question supprimée depuis le début de l'examen : elle est passée.
        if vResult is None:
            self.go_next()
            return

        vTone = "success" if vResult["correct"] else "danger"

        self.verdict_label.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")
        self.verdict_label.setText(
            "Bonne réponse."
            if vResult["correct"]
            else f"Réponse incorrecte. Votre réponse : {vResult['chosen']}. "
            f"Réponse attendue : {vResult['answer']}"
        )
        self.explanation_label.setText(vResult["explanation"])
        self.show_extras(vResult["question"])

        for vWidget in self.answer_widgets:
            vWidget.setEnabled(False)

        self.validate_button.hide()
        self.next_button.show()

        self.refresh()
