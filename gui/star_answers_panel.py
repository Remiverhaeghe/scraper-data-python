"""Panneau des réponses STAR : une réponse par question, liée à une expérience"""

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.interview_journal import collect_asked_questions
from job.profile import load_profile
from job.star_answers import (
    BEHAVIORAL_QUESTIONS,
    STAR_FIELDS,
    load_star_answers,
    save_star_answer,
    suggest_star_answer,
)
from utils.logger import get_logger

logger = get_logger(__name__)

FIELD_HEIGHT = 72

# Questions vécues en entretien rappelées sous les réponses
MAX_ASKED_SHOWN = 5

FIELD_HELP = {
    "situation": "Le contexte : projet, équipe, enjeu",
    "task": "Ce qui vous revenait à vous",
    "action": "Ce que vous avez fait, concrètement",
    "result": "Le résultat, chiffré si possible",
}


class StarAnswersPanel(QWidget):
    """Prépare les réponses aux questions comportementales avec la méthode STAR."""

    def __init__(self, pDatabaseFile):
        """Construit le choix de la question, de l'expérience et les quatre parties."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.answers = {}
        self.profile = None

        self.question_combo = QComboBox()
        self.question_combo.currentIndexChanged.connect(self.show_answer)

        self.experience_combo = QComboBox()

        self.field_edits = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(16)
        vGrid.setVerticalSpacing(8)

        for vIndex, (vName, vLabel) in enumerate(STAR_FIELDS.items()):
            vEdit = QPlainTextEdit()
            vEdit.setPlaceholderText(FIELD_HELP[vName])
            vEdit.setMaximumHeight(FIELD_HEIGHT)
            self.field_edits[vName] = vEdit

            vTitle = QLabel(vLabel)
            vTitle.setObjectName("fieldLabel")

            vGrid.addWidget(vTitle, 2 * (vIndex // 2), vIndex % 2)
            vGrid.addWidget(vEdit, 2 * (vIndex // 2) + 1, vIndex % 2)

        vPrefillButton = create_button(
            "Pré-remplir depuis l'expérience", "sparkles", pIconColor=COLORS["primary"]
        )
        vPrefillButton.setToolTip(
            "Complète les parties vides avec l'intitulé et la réalisation de "
            "l'expérience choisie"
        )
        vPrefillButton.clicked.connect(self.prefill)

        vSaveButton = create_button(
            "Enregistrer la réponse", pObjectName="primaryButton"
        )
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vChoices = QHBoxLayout()
        vChoices.setSpacing(12)
        vChoices.addWidget(self.question_combo, 2)
        vChoices.addWidget(self.experience_combo, 1)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(vPrefillButton)
        vActions.addWidget(self.message_label, 1)

        self.card, vCardLayout = create_card(
            "Réponses STAR",
            "Situation, tâche, action, résultat : une histoire vécue par question "
            "comportementale. Elles sont reprises dans la préparation de chaque offre.",
            pKey="profile/star",
        )
        vCardLayout.addLayout(vChoices)
        vCardLayout.addLayout(vGrid)
        vCardLayout.addLayout(vActions)

        self.asked_label = QLabel()
        self.asked_label.setObjectName("cardSubtitle")
        self.asked_label.setWordWrap(True)
        vCardLayout.addWidget(self.asked_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(self.card)

    def refresh(self):
        """Relit le profil et les réponses enregistrées."""
        try:
            self.profile = load_profile(self.database_file)
            self.answers = load_star_answers(self.database_file)
            vAsked = collect_asked_questions(self.database_file)[:MAX_ASKED_SHOWN]

        except Exception:
            logger.exception("Impossible de lire les réponses STAR")

            show_message(
                self.message_label, "Les réponses n'ont pas pu être lues.", "danger"
            )
            return

        self.asked_label.setText(
            "Questions posées dans vos entretiens : "
            + " · ".join(vItem["question"] for vItem in vAsked)
            if vAsked
            else ""
        )
        self.asked_label.setVisible(bool(vAsked))

        self.experience_combo.clear()
        self.experience_combo.addItem("Sans expérience liée", "")

        for vExperience in self.profile["experiences"]:
            self.experience_combo.addItem(vExperience["title"], vExperience["title"])

        vKey = self.question_combo.currentData()

        self.question_combo.blockSignals(True)
        self.question_combo.clear()

        for vQuestionKey, vQuestion in BEHAVIORAL_QUESTIONS.items():
            vSuffix = " (préparée)" if vQuestionKey in self.answers else ""
            self.question_combo.addItem(vQuestion + vSuffix, vQuestionKey)

        self.question_combo.setCurrentIndex(max(self.question_combo.findData(vKey), 0))
        self.question_combo.blockSignals(False)

        self.show_answer()

    def show_answer(self):
        """Affiche la réponse enregistrée pour la question choisie."""
        vAnswer = self.answers.get(self.question_combo.currentData(), {})

        self.experience_combo.setCurrentIndex(
            max(self.experience_combo.findData(vAnswer.get("experience", "")), 0)
        )

        for vName, vEdit in self.field_edits.items():
            vEdit.setPlainText(vAnswer.get(vName, ""))

        show_message(
            self.message_label,
            f"{len(self.answers)} réponse(s) préparée(s) sur "
            f"{len(BEHAVIORAL_QUESTIONS)}.",
            "success" if self.answers else "warning",
        )

    def prefill(self):
        """Complète les parties vides à partir de l'expérience choisie."""
        if self.profile is None:
            return

        vSuggestion = suggest_star_answer(
            self.profile, self.experience_combo.currentData()
        )

        for vName, vEdit in self.field_edits.items():
            if not vEdit.toPlainText().strip():
                vEdit.setPlainText(vSuggestion[vName])

    def save(self):
        """Enregistre la réponse affichée ; vide, elle est retirée."""
        try:
            save_star_answer(
                self.database_file,
                self.question_combo.currentData(),
                self.experience_combo.currentData(),
                {
                    vName: vEdit.toPlainText()
                    for vName, vEdit in self.field_edits.items()
                },
            )

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except Exception:
            logger.exception("Échec de l'enregistrement de la réponse STAR")

            show_message(
                self.message_label, "La réponse n'a pas pu être enregistrée.", "danger"
            )
            return

        self.refresh()
