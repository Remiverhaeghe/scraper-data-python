"""Page de révision technique : thèmes, questions à choix multiple et corrections"""

from datetime import datetime

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QButtonGroup,
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

from gui.theme import COLORS
from gui.widgets import (
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.quiz import (
    QUIZ_MODES,
    answer_question,
    build_quiz_overview,
    load_quiz,
    pick_question,
)
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

        vButtons = QHBoxLayout()
        vButtons.addWidget(self.validate_button)
        vButtons.addWidget(self.next_button)
        vButtons.addStretch()

        vLayout.addWidget(self.meta_label)
        vLayout.addWidget(self.question_label)
        vLayout.addWidget(self.code_edit)
        vLayout.addLayout(self.choices_layout)
        vLayout.addWidget(self.verdict_label)
        vLayout.addWidget(self.explanation_label)
        vLayout.addLayout(vButtons)

        return self.question_card

    def refresh(self):
        """Relit la progression et reconstruit les cartes des thèmes."""
        try:
            vThemes = build_quiz_overview(self.database_file, load_quiz())

        except Exception:
            logger.exception("Impossible de charger la révision")

            self.message_label.setText("Les questions n'ont pas pu être chargées.")
            self.message_label.show()
            return

        clear_layout(self.themes_grid)

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
        vQuiz = load_quiz()

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
            return

        self.meta_label.setText(
            f"{vQuiz[pThemeKey]['label']} · {self.question['level']} · "
            f"{QUIZ_MODES[pMode]}"
        )
        self.question_label.setText(self.question["question"])
        self.code_edit.setPlainText(self.question.get("code", ""))
        self.code_edit.setVisible(bool(self.question.get("code")))
        self.validate_button.show()

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
            load_quiz(),
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
