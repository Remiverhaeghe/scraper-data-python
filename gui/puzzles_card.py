"""Carte des puzzles de code sur la page Défis : série en cours, correction, bilan"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.quiz_answer import add_answer_widgets, read_response
from gui.theme import COLORS
from gui.widgets import clear_layout, create_button, create_card, show_message
from job.code_puzzles import answer_puzzle, build_puzzle_view, start_series
from utils.logger import get_logger

logger = get_logger(__name__)


def create_code_label(pText):
    """Crée une étiquette de code en chasse fixe, sélectionnable."""

    rLabel = QLabel(pText)
    rLabel.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    rLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    return rLabel


def create_text_label(pText, pObjectName=None):
    """Crée une étiquette de texte qui revient à la ligne."""

    rLabel = QLabel(pText)
    rLabel.setWordWrap(True)

    if pObjectName:
        rLabel.setObjectName(pObjectName)

    return rLabel


class PuzzlesCard:
    """Puzzles de code joués par séries de dix, de difficulté croissante."""

    def __init__(self, pDatabaseFile):
        """Construit la carte ; son contenu est rempli par refresh."""
        self.database_file = pDatabaseFile
        self.puzzle = None
        self.widgets = []
        self.group = None
        self.card, vLayout = create_card(
            "Puzzles de code",
            "Lignes à remettre dans l'ordre, ligne fautive, code à compléter : "
            "des séries de dix, de difficulté croissante",
            "code",
            "puzzles",
            pOpen=True,
        )
        self.status_label = create_text_label("", "cardSubtitle")
        self.body = QVBoxLayout()
        self.message_label = create_text_label("")
        vLayout.addWidget(self.status_label)
        vLayout.addLayout(self.body)
        vLayout.addWidget(self.message_label)

    def refresh(self, pFeedback=None):
        """Affiche la correction, le puzzle en cours, ou le bilan et le bouton de série."""
        vView = build_puzzle_view(self.database_file)
        self.puzzle = vView["puzzle"]
        self.status_label.setText(
            f"Niveau {vView['level_label']} · réponses justes d'affilée : "
            f"{vView['streak']} · record : {vView['best_streak']} · séries "
            f"terminées : {vView['series_count']}. Une série à 8 ou plus fait "
            "monter d'un niveau, à 4 ou moins redescendre."
        )
        clear_layout(self.body)
        self.widgets = []

        if pFeedback is not None:
            self.show_feedback(pFeedback)
        elif self.puzzle is not None:
            self.show_puzzle(vView["total"])

        if self.puzzle is None:
            if vView["recap"]:
                self.show_recap(vView["recap"])

            vButton = create_button(
                "Nouvelle série" if vView["series_count"] else "Commencer une série",
                "sparkles",
                "primaryButton",
                COLORS["on_primary"],
            )
            vButton.clicked.connect(self.start)
            self.body.addWidget(vButton)

    def show_puzzle(self, pTotal):
        """Affiche l'énoncé, le code et la zone de réponse du puzzle en cours."""
        vPuzzle = self.puzzle
        vTitle = create_text_label(vPuzzle["title"], "cardTitle")
        vMeta = create_text_label(
            f"Puzzle {vPuzzle['position'] + 1} sur {pTotal} · {vPuzzle['type_label']} "
            f"· {vPuzzle['language']} · {vPuzzle['level_label']}",
            "cardSubtitle",
        )

        for vWidget in (vTitle, vMeta, create_text_label(vPuzzle["prompt"])):
            self.body.addWidget(vWidget)

        if vPuzzle["type"] == "saisie":
            self.body.addWidget(create_code_label(vPuzzle["code"]))

        # Une ligne fautive se choisit comme un QCM, lignes numérotées et dans l'ordre
        vQuestion = (
            {
                **vPuzzle,
                "shuffled": [
                    (vIndex, f"{vIndex + 1:>2}  {vLine}")
                    for vIndex, vLine in vPuzzle["shuffled"]
                ],
            }
            if vPuzzle["type"] == "ligne"
            else vPuzzle
        )
        vAnswers = QWidget()
        vAnswerLayout = QVBoxLayout(vAnswers)
        vAnswerLayout.setContentsMargins(0, 0, 0, 0)
        self.group = QButtonGroup(vAnswers)
        self.widgets = add_answer_widgets(
            vQuestion, vAnswerLayout, self.group, self.submit
        )

        if vPuzzle["type"] != "saisie":
            for vWidget in self.widgets:
                vWidget.setFont(
                    QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
                )

        self.body.addWidget(vAnswers)

        vButton = create_button(
            "Valider", "circle-check", "primaryButton", COLORS["on_primary"]
        )
        vButton.clicked.connect(self.submit)
        vRow = QHBoxLayout()
        vRow.addWidget(vButton)
        vRow.addStretch(1)
        self.body.addLayout(vRow)

    def show_feedback(self, pFeedback):
        """Affiche la correction d'une réponse et le bouton du puzzle suivant."""
        vResult = create_text_label(
            (
                "Bonne réponse"
                if pFeedback["correct"]
                else "Ce n'est pas la bonne réponse"
            )
            + f" · réponses justes d'affilée : {pFeedback['streak']}"
        )
        show_message(
            vResult, vResult.text(), "success" if pFeedback["correct"] else "danger"
        )
        self.body.addWidget(vResult)

        if not pFeedback["correct"]:
            self.body.addWidget(
                create_code_label(f"Votre réponse : {pFeedback['given']}")
            )
            self.body.addWidget(
                create_code_label(f"Réponse attendue : {pFeedback['expected']}")
            )

        self.body.addWidget(create_text_label(pFeedback["explanation"]))

        if not pFeedback["finished"]:
            vButton = create_button(
                "Puzzle suivant", "arrow-right", "primaryButton", COLORS["on_primary"]
            )
            vButton.clicked.connect(lambda: self.refresh())
            self.body.addWidget(vButton)

    def show_recap(self, pRecap):
        """Affiche le bilan de la dernière série : score et erreurs expliquées."""
        self.body.addWidget(
            create_text_label(
                f"Bilan de la série : {pRecap['score']} sur {pRecap['total']}",
                "cardTitle",
            )
        )

        if not pRecap["mistakes"]:
            self.body.addWidget(create_text_label("Aucune erreur : série parfaite."))

        for vMistake in pRecap["mistakes"]:
            self.body.addWidget(
                create_text_label(
                    f"{vMistake['title']} · {vMistake['language']}", "cardSubtitle"
                )
            )
            self.body.addWidget(
                create_code_label(f"Votre réponse : {vMistake['given']}")
            )
            self.body.addWidget(
                create_code_label(f"Réponse attendue : {vMistake['expected']}")
            )
            self.body.addWidget(create_text_label(vMistake["explanation"]))

    def start(self):
        """Tire une nouvelle série."""
        start_series(self.database_file)
        show_message(self.message_label, "")
        self.refresh()

    def submit(self):
        """Corrige la réponse au puzzle en cours."""
        if self.puzzle is None:
            return

        vResponse = read_response(self.puzzle, self.widgets, self.group, None)

        if vResponse is None:
            show_message(self.message_label, "Répondez avant de valider.", "warning")
            return

        try:
            vFeedback = answer_puzzle(
                self.database_file, self.puzzle["position"], vResponse, datetime.now()
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        show_message(self.message_label, "")
        self.refresh(vFeedback)
