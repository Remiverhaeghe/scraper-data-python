"""Page des tests de recrutement : choix d'une catégorie, partie chronométrée"""

import random
import time
from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    StatisticCard,
    TileButton,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.aptitude import (
    CATEGORIES,
    QUESTIONS_PER_SESSION,
    READY_SCORE,
    SESSION_SECONDS,
    build_aptitude_overview,
    finish_session,
    generate_session,
)
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
CHOICE_COLUMNS = 2
TICK_MILLISECONDS = 1000

# Couleur de la tuile d'une catégorie selon le dernier score moyen
SCORE_ACCENTS = ((READY_SCORE, "green"), (50, "amber"), (0, "purple"))


def describe_row(pRow):
    """Retourne le détail d'une tuile : meilleur score et nombre de parties."""

    if not pRow["sessions"]:
        return pRow["description"]

    rText = (
        f"Meilleur {pRow['best']} % · moyenne récente {pRow['average']} % · "
        f"{pRow['sessions']} partie{'s' if pRow['sessions'] > 1 else ''}"
    )

    return rText


def get_row_accent(pRow):
    """Retourne la couleur d'une tuile : bleue avant la première partie."""

    if pRow["average"] is None:
        return "blue"

    rAccent = next(
        vAccent for vMinimum, vAccent in SCORE_ACCENTS if pRow["average"] >= vMinimum
    )

    return rAccent


class AptitudePage(QWidget):
    """Entraînement aux tests psychotechniques des recruteurs."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit les scores."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.category = None
        self.seed = None
        self.questions = []
        self.answers = []
        self.started_at = None

        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MILLISECONDS)
        self.timer.timeout.connect(self.tick)

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Tests de recrutement",
            "Les tests psychotechniques que font passer beaucoup d'industriels : "
            f"{QUESTIONS_PER_SESSION} questions en {SESSION_SECONDS // 60} min "
            f"{SESSION_SECONDS % 60:02d}, sans calculatrice",
            pIcon="timer",
        )

        self.cards = {
            "sessions": StatisticCard("Parties jouées", "timer", "blue"),
            "ready": StatisticCard(
                f"Catégories prêtes (≥ {READY_SCORE} %)", "circle-check", "green"
            ),
            "perfect": StatisticCard("Sans faute", "trophy", "purple"),
            "weakest": StatisticCard("À travailler", "target", "amber"),
        }
        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.cards.values():
            vCards.addWidget(vCard)

        vChoiceCard, vChoiceLayout = create_card(
            "Choisir un test",
            "Chaque partie est tirée au hasard : refaites-la jusqu'à dépasser "
            f"{READY_SCORE} % de moyenne",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)
        self.choice_card = vChoiceCard

        self.game_card, vGameLayout = create_card(
            "Partie en cours", pIcon="timer", pOpen=True
        )
        self.step_label = QLabel()
        self.step_label.setObjectName("cardSubtitle")
        self.time_label = QLabel()
        self.time_label.setObjectName("cardSubtitle")
        self.time_bar = QProgressBar()
        self.time_bar.setRange(0, SESSION_SECONDS)
        self.time_bar.setTextVisible(False)
        self.time_bar.setMaximumHeight(8)
        self.question_label = QLabel()
        self.question_label.setObjectName("offerTitle")
        self.question_label.setWordWrap(True)
        self.question_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        vTop = QHBoxLayout()
        vTop.addWidget(self.step_label)
        vTop.addStretch()
        vTop.addWidget(self.time_label)

        self.choices_layout = QGridLayout()
        self.choices_layout.setSpacing(10)
        self.choice_buttons = []

        for vIndex in range(4):
            vButton = create_button("", pObjectName="segmentButton")
            vButton.setMinimumHeight(44)
            vButton.clicked.connect(lambda _=False, pIndex=vIndex: self.choose(pIndex))
            self.choice_buttons.append(vButton)
            self.choices_layout.addWidget(
                vButton, vIndex // CHOICE_COLUMNS, vIndex % CHOICE_COLUMNS
            )

        vStopButton = create_button("Abandonner", pObjectName="linkButton")
        vStopButton.clicked.connect(self.stop_session)

        vGameLayout.addLayout(vTop)
        vGameLayout.addWidget(self.time_bar)
        vGameLayout.addWidget(self.question_label)
        vGameLayout.addLayout(self.choices_layout)
        vGameLayout.addWidget(vStopButton, 0, Qt.AlignmentFlag.AlignLeft)

        self.result_card, vResultLayout = create_card(
            "Résultat", pIcon="award", pOpen=True
        )
        self.result_label = QLabel()
        self.result_label.setObjectName("offerTitle")
        self.result_label.setWordWrap(True)
        self.corrections_layout = QVBoxLayout()
        self.corrections_layout.setSpacing(10)
        vAgainButton = create_button(
            "Rejouer cette catégorie", "timer", "primaryButton", "#FFFFFF"
        )
        vAgainButton.clicked.connect(lambda: self.start_session(self.category))
        vBackButton = create_button("Choisir un autre test", pObjectName="linkButton")
        vBackButton.clicked.connect(self.show_choices)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vAgainButton)
        vButtons.addWidget(vBackButton)
        vButtons.addStretch()

        vResultLayout.addWidget(self.result_label)
        vResultLayout.addLayout(self.corrections_layout)
        vResultLayout.addLayout(vButtons)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(vChoiceCard)
        vLayout.addWidget(self.game_card)
        vLayout.addWidget(self.result_card)
        vLayout.addStretch()

        self.game_card.hide()
        self.result_card.hide()

    def refresh(self):
        """Relit les scores et remplit les tuiles, sauf pendant une partie."""
        if self.timer.isActive():
            return

        try:
            vOverview = build_aptitude_overview(self.database_file)

        except Exception:
            logger.exception("Scores des tests de recrutement non lus")
            show_message(
                self.message_label, "Les scores n'ont pas pu être lus.", "danger"
            )
            return

        self.cards["sessions"].set_value(vOverview["sessions"])
        self.cards["ready"].set_value(f"{vOverview['ready']} / {len(CATEGORIES)}")
        self.cards["perfect"].set_value(vOverview["perfect"])
        self.cards["weakest"].set_value(vOverview["weakest"] or "-")

        clear_layout(self.tiles_layout)

        for vIndex, vRow in enumerate(vOverview["rows"]):
            vTile = TileButton(
                vRow["label"],
                describe_row(vRow),
                vRow["icon"],
                get_row_accent(vRow),
                "Prêt" if vRow["ready"] else "",
            )
            vTile.set_done(vRow["ready"])
            vTile.clicked.connect(
                lambda pCategory=vRow["category"]: self.start_session(pCategory)
            )
            self.tiles_layout.addWidget(
                vTile, vIndex // TILE_COLUMNS, vIndex % TILE_COLUMNS
            )

    def start_session(self, pCategory, pSeed=None):
        """Tire une partie et lance le chronomètre."""
        self.category = pCategory
        self.seed = random.randrange(1 << 30) if pSeed is None else pSeed
        self.questions = generate_session(pCategory, self.seed)
        self.answers = []
        self.started_at = time.monotonic()

        self.choice_card.hide()
        self.result_card.hide()
        self.game_card.show()
        show_message(self.message_label, "")

        self.show_question()
        self.tick()
        self.timer.start()

    def get_elapsed(self):
        """Retourne les secondes écoulées depuis le début de la partie."""

        rElapsed = time.monotonic() - self.started_at

        return rElapsed

    def tick(self):
        """Met à jour le temps restant ; la partie s'arrête à zéro."""
        vRemaining = max(0, SESSION_SECONDS - int(self.get_elapsed()))

        self.time_label.setText(f"{vRemaining // 60}:{vRemaining % 60:02d}")
        self.time_bar.setValue(vRemaining)

        if vRemaining == 0:
            self.finish()

    def show_question(self):
        """Affiche la question suivante et ses quatre choix."""
        vQuestion = self.questions[len(self.answers)]

        self.step_label.setText(
            f"{CATEGORIES[self.category][0]} · question {len(self.answers) + 1} "
            f"sur {len(self.questions)}"
        )
        self.question_label.setText(vQuestion["question"])

        for vButton, vChoice in zip(self.choice_buttons, vQuestion["choices"]):
            vButton.setText(vChoice)

    def choose(self, pIndex):
        """Enregistre le choix et passe à la question suivante, ou termine."""
        if not self.timer.isActive():
            return

        self.answers.append(pIndex)

        if len(self.answers) == len(self.questions):
            self.finish()
        else:
            self.show_question()

    def finish(self):
        """Corrige et enregistre la partie, puis affiche le résultat."""
        self.timer.stop()
        vAnswers = self.answers + [None] * (len(self.questions) - len(self.answers))

        try:
            vResult = finish_session(
                self.database_file,
                self.category,
                self.seed,
                vAnswers,
                self.get_elapsed(),
                datetime.now(),
            )

        except Exception:
            logger.exception("Partie de test de recrutement non enregistrée")
            show_message(
                self.message_label, "La partie n'a pas pu être enregistrée.", "danger"
            )
            self.show_choices()
            return

        self.show_result(vResult)

    def show_result(self, pResult):
        """Affiche le score, les points gagnés et la correction des erreurs."""
        self.game_card.hide()
        self.result_card.show()

        vUnanswered = sum(
            vQuestion["given"] is None for vQuestion in pResult["questions"]
        )
        self.result_label.setText(
            f"{pResult['label']} : {pResult['correct']} / {pResult['total']} "
            f"({pResult['score']} %) en {pResult['duration']} s · +{pResult['xp']} XP"
            + (f" · {vUnanswered} sans réponse, temps écoulé" if vUnanswered else "")
        )

        clear_layout(self.corrections_layout)

        for vQuestion in pResult["questions"]:
            if vQuestion["given"] == vQuestion["answer"]:
                continue

            vGiven = (
                "pas de réponse"
                if vQuestion["given"] is None
                else vQuestion["choices"][vQuestion["given"]]
            )
            vLabel = QLabel(
                f"<b>{escape(vQuestion['question'])}</b><br>"
                f"Votre réponse : {escape(vGiven)} · bonne réponse : "
                f"<b>{escape(vQuestion['choices'][vQuestion['answer']])}</b><br>"
                f"{escape(vQuestion['explanation'])}"
            )
            vLabel.setTextFormat(Qt.TextFormat.RichText)
            vLabel.setWordWrap(True)
            self.corrections_layout.addWidget(vLabel)

        if pResult["correct"] == pResult["total"]:
            self.corrections_layout.addWidget(QLabel("Sans faute, bravo."))

    def stop_session(self):
        """Abandonne la partie en cours sans l'enregistrer."""
        self.timer.stop()
        self.show_choices()

    def show_choices(self):
        """Revient au choix d'un test, avec les scores à jour."""
        self.game_card.hide()
        self.result_card.hide()
        self.choice_card.show()
        self.refresh()
