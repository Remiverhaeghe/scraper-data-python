"""Page de révision technique : thèmes, questions à choix multiple et corrections"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.assistant import CHATGPT_URL
from job.quiz import (
    GENERATION_COUNTS,
    IMPORT_EXTENSIONS,
    QUIZ_LEVELS,
    QUIZ_MODES,
    answer_question,
    build_quiz_overview,
    build_generation_prompt,
    build_quiz_statistics,
    describe_quiz_import,
    flag_question,
    import_questions,
    import_questions_file,
    load_active_quiz,
    pick_question,
)
from job.presentation import CHART_PALETTE
from storage.quiz_answers import get_last_answers
from utils.logger import get_logger

logger = get_logger(__name__)

THEME_COLUMNS = 3


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

        self.themes_grid = QGridLayout()
        self.themes_grid.setSpacing(16)

        for vColumn in range(THEME_COLUMNS):
            self.themes_grid.setColumnStretch(vColumn, 1)

        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.create_question_card())
        vLayout.addLayout(self.themes_grid)
        vLayout.addWidget(self.create_import_card())
        vLayout.addWidget(self.create_statistics_card())
        vLayout.addStretch()

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

        self.choices_layout = QVBoxLayout()
        self.choices_layout.setSpacing(8)

        self.verdict_label = QLabel()
        self.verdict_label.setWordWrap(True)

        self.explanation_label = QLabel()
        self.explanation_label.setWordWrap(True)

        self.validate_button = create_button("Valider", pObjectName="primaryButton")
        self.validate_button.clicked.connect(self.validate)

        self.next_button = create_button(
            "Question suivante", "arrow-right", pIconColor=COLORS["primary"]
        )
        self.next_button.clicked.connect(lambda: self.start(self.theme_key, self.mode))

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
        vButtons.addWidget(self.flag_button)

        vLayout.addWidget(self.meta_label)
        vLayout.addWidget(self.question_label)
        vLayout.addWidget(self.code_edit)
        vLayout.addLayout(self.choices_layout)
        vLayout.addWidget(self.verdict_label)
        vLayout.addWidget(self.explanation_label)
        vLayout.addLayout(vButtons)

        return self.question_card

    def create_import_card(self):
        """Construit la génération de questions avec ChatGPT et leur import."""
        self.theme_combo = QComboBox()
        self.theme_combo.setEditable(True)
        self.theme_combo.setToolTip("Thème existant ou nouveau, par exemple Kafka")

        self.level_combo = QComboBox()

        for vLevel in QUIZ_LEVELS:
            self.level_combo.addItem(vLevel.capitalize(), vLevel)

        self.count_combo = QComboBox()

        for vCount in GENERATION_COUNTS:
            self.count_combo.addItem(f"{vCount} questions", vCount)

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

        self.import_message = QLabel()
        self.import_message.setObjectName("cardSubtitle")
        self.import_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vPasteButton)
        vActions.addWidget(vFileButton)
        vActions.addWidget(self.import_message, 1)

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
            self.import_message.setText("Choisissez ou saisissez un thème.")
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

        self.import_message.setText(
            "Demande copiée : collez-la dans ChatGPT, puis sa réponse ci-dessus."
        )

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

    def run_import(self, pImport):
        """Lance un import, affiche son bilan et met à jour les thèmes."""
        try:
            vReport = pImport()

        except ValueError as vException:
            self.import_message.setText(str(vException))
            return

        except Exception:
            logger.exception("Échec de l'import de questions de révision")

            self.import_message.setText("L'import a échoué. Voir les journaux.")
            return

        self.import_message.setText(describe_quiz_import(vReport))

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

        vCard, vLayout = create_card(
            "Mes statistiques", "Progression globale et réponses des 14 derniers jours"
        )
        vLayout.addLayout(vCards)
        vLayout.addWidget(self.statistics_chart)

        return vCard

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
        try:
            vThemes = build_quiz_overview(
                self.database_file, load_active_quiz(self.database_file)
            )
            self.show_statistics(
                build_quiz_statistics(self.database_file, vThemes, datetime.now())
            )

        except Exception:
            logger.exception("Impossible de charger la révision")

            self.message_label.setText("Les questions n'ont pas pu être chargées.")
            self.message_label.show()
            return

        clear_layout(self.themes_grid)

        vCurrent = self.theme_combo.currentText()
        self.theme_combo.clear()
        self.theme_combo.addItems(sorted(vTheme["label"] for vTheme in vThemes))
        self.theme_combo.setCurrentText(vCurrent)

        for vIndex, vTheme in enumerate(vThemes):
            self.themes_grid.addWidget(
                self.create_theme_card(vTheme), *divmod(vIndex, THEME_COLUMNS)
            )

    def create_theme_card(self, pTheme):
        """Crée la carte d'un thème : progression, intérêt et boutons."""
        rCard, vLayout = create_card(pTheme["label"])

        # Largeur fixée par la grille seule : les colonnes restent égales.
        rCard.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        vParts = [f"{pTheme['correct']} / {pTheme['total']} acquises"]

        if pTheme["to_review"]:
            vParts.append(f"{pTheme['to_review']} à revoir")

        if pTheme["offer_count"]:
            vParts.append(f"demandé dans {pTheme['offer_count']} offre(s)")

        vInfo = QLabel(" · ".join(vParts))
        vInfo.setObjectName("cardSubtitle")
        vInfo.setWordWrap(True)

        vProgress = QProgressBar()
        vProgress.setTextVisible(False)
        vProgress.setValue(pTheme["score"])

        vStart = create_button("Réviser", pObjectName="primaryButton")
        vStart.clicked.connect(lambda: self.start(pTheme["key"], "discover"))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vStart)

        if pTheme["to_review"]:
            vReview = create_button("Revoir les erreurs")
            vReview.clicked.connect(lambda: self.start(pTheme["key"], "review"))
            vButtons.addWidget(vReview)

        vButtons.addStretch()

        vLayout.addWidget(vInfo)
        vLayout.addWidget(vProgress)
        vLayout.addLayout(vButtons)

        return rCard

    def start(self, pThemeKey, pMode):
        """Affiche une nouvelle question du thème, ou signale qu'il n'y en a plus."""
        vQuiz = load_active_quiz(self.database_file)

        self.theme_key = pThemeKey
        self.mode = pMode
        self.question = pick_question(
            vQuiz, pThemeKey, pMode, get_last_answers(self.database_file)
        )

        self.question_card.show()
        self.verdict_label.clear()
        self.explanation_label.clear()
        self.next_button.hide()

        clear_layout(self.choices_layout)

        for vButton in self.choices_group.buttons():
            self.choices_group.removeButton(vButton)

        if self.question is None:
            self.meta_label.setText(vQuiz[pThemeKey]["label"])
            self.question_label.setText("Aucune question ratée à revoir dans ce thème.")
            self.code_edit.hide()
            self.validate_button.hide()
            self.flag_button.hide()
            return

        self.meta_label.setText(
            f"{vQuiz[pThemeKey]['label']} · {self.question['level']} · "
            f"{QUIZ_MODES[pMode]}"
        )
        self.question_label.setText(self.question["question"])
        self.code_edit.setPlainText(self.question.get("code", ""))
        self.code_edit.setVisible(bool(self.question.get("code")))
        self.validate_button.show()
        self.flag_button.show()

        # L'identifiant du bouton est l'indice d'origine du choix, avant mélange.
        for vIndex, vChoice in self.question["shuffled"]:
            vButton = QRadioButton(vChoice)
            self.choices_group.addButton(vButton, vIndex)
            self.choices_layout.addWidget(vButton)

    def validate(self):
        """Corrige la réponse choisie et affiche l'explication."""
        vChoice = self.choices_group.checkedId()

        if vChoice < 0:
            self.verdict_label.setText("Choisissez une réponse.")
            return

        vResult = answer_question(
            self.database_file,
            load_active_quiz(self.database_file),
            self.question["id"],
            vChoice,
            datetime.now(),
        )

        vTone = "success" if vResult["correct"] else "danger"

        self.verdict_label.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")
        self.verdict_label.setText(
            "Bonne réponse."
            if vResult["correct"]
            else f"Réponse incorrecte. Réponse attendue : {vResult['answer']}"
        )
        self.explanation_label.setText(vResult["explanation"])

        for vButton in self.choices_group.buttons():
            vButton.setEnabled(False)

        self.validate_button.hide()
        self.next_button.show()

        self.refresh()
