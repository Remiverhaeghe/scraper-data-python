"""Entretien oral simulé : question lue à voix haute, chrono, grille et progression"""

from datetime import datetime

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gui.speech import Speaker
from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.oral_interview import answer_oral, build_oral_view, start_oral, stop_oral
from utils.logger import get_logger

logger = get_logger(__name__)


def format_clock(pSeconds):
    """Retourne un temps en minutes et secondes : 1:05, ou -0:12 au-delà du temps."""

    vSeconds = abs(int(pSeconds))

    rText = f"{'-' if pSeconds < 0 else ''}{vSeconds // 60}:{vSeconds % 60:02d}"

    return rText


class OralInterviewPanel(QWidget):
    """Séances d'entretien oral : la question est lue, la réponse se dit à voix haute."""

    def __init__(self, pDatabaseFile):
        """Construit le choix de séance, la question, le chrono et la grille."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.view = None
        self.seconds = None
        self.speaker = Speaker(self)
        self.speaker.finished.connect(self.start_clock)
        self.clock = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_clock)

        vCard, vLayout = create_card(
            "Entretien oral simulé",
            "La question est lue à voix haute : répondez à l'oral, dans le temps, "
            "puis notez votre réponse",
            "bell-ring",
            "oral_interview",
        )

        self.progress_label = QLabel()
        self.progress_label.setObjectName("cardSubtitle")
        self.progress_label.setWordWrap(True)

        self.mode_combo = QComboBox()
        self.duration_combo = QComboBox()
        self.start_button = create_button(
            "Commencer", "bell-ring", "primaryButton", COLORS["on_primary"]
        )
        self.start_button.clicked.connect(self.start)
        vStartRow = QHBoxLayout()
        vStartRow.addWidget(self.mode_combo, 1)
        vStartRow.addWidget(self.duration_combo)
        vStartRow.addWidget(self.start_button)
        self.start_widget = QWidget()
        self.start_widget.setLayout(vStartRow)

        self.question_label = QLabel()
        self.question_label.setObjectName("cardTitle")
        self.question_label.setWordWrap(True)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("cardTitle")
        self.listen_button = create_button("Réécouter", "bell-ring")
        self.listen_button.clicked.connect(self.read_question)
        self.begin_button = create_button("Je commence", "timer")
        self.begin_button.clicked.connect(self.start_clock)
        self.done_button = create_button(
            "J'ai terminé", "circle-check", "primaryButton", COLORS["on_primary"]
        )
        self.done_button.clicked.connect(self.finish_answer)
        self.stop_button = create_button("Arrêter la séance", "history")
        self.stop_button.clicked.connect(self.stop)
        vSessionRow = QHBoxLayout()

        for vWidget in (
            self.clock_label,
            self.listen_button,
            self.begin_button,
            self.done_button,
        ):
            vSessionRow.addWidget(vWidget)

        vSessionRow.addStretch(1)
        vSessionRow.addWidget(self.stop_button)

        self.grid_widget = QWidget()
        vGridLayout = QVBoxLayout(self.grid_widget)
        vGridLayout.setContentsMargins(0, 0, 0, 0)
        self.rating_groups = {}
        self.validate_button = create_button(
            "Valider ma note", "circle-check", "primaryButton", COLORS["on_primary"]
        )
        self.validate_button.clicked.connect(self.validate)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.next_button = create_button("Question suivante", "arrow-right")
        self.next_button.clicked.connect(self.refresh)

        for vWidget in (
            self.progress_label,
            self.start_widget,
            self.question_label,
        ):
            vLayout.addWidget(vWidget)

        vLayout.addLayout(vSessionRow)
        vLayout.addWidget(self.grid_widget)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.next_button)

        vOuter = QVBoxLayout(self)
        vOuter.setContentsMargins(0, 0, 0, 0)
        vOuter.addWidget(vCard)

    def build_grid(self, pView):
        """Crée une fois les boutons de la grille : structure et exemple, de Non à Oui."""
        if self.rating_groups:
            return

        vLayout = self.grid_widget.layout()

        for vId, vLabel, vTip in pView["criteria"][:2]:
            vRow = QHBoxLayout()
            vRow.addWidget(QLabel(f"{vLabel} : {vTip}"), 1)
            vGroup = QButtonGroup(self.grid_widget)

            for vRating, vText in pView["ratings"].items():
                vButton = QRadioButton(vText)
                vGroup.addButton(vButton, vRating)
                vRow.addWidget(vButton)

            self.rating_groups[vId] = vGroup
            vLayout.addLayout(vRow)

        vLayout.addWidget(self.validate_button)

    def refresh(self):
        """Affiche la séance en cours, ou le choix d'une nouvelle séance et la progression."""
        self.timer.stop()
        self.speaker.stop()
        self.seconds = None

        try:
            self.view = build_oral_view(self.database_file)

        except Exception:
            logger.exception("Impossible de lire l'entretien oral")
            return

        vView = self.view
        self.build_grid(vView)
        self.fill_choices(vView)
        self.progress_label.setText(self.describe_progress(vView))
        vActive = vView["session"] is not None

        self.start_widget.setVisible(not vActive)
        self.question_label.setVisible(vActive)
        self.clock_label.setVisible(vActive)
        self.listen_button.setVisible(vActive and self.speaker.is_available())
        self.begin_button.setVisible(vActive)
        self.done_button.setVisible(False)
        self.stop_button.setVisible(vActive)
        self.grid_widget.hide()
        self.next_button.hide()
        show_message(self.message_label, "")

        if vActive:
            vSession = vView["session"]
            self.question_label.setText(
                f"Question {vView['position'] + 1} sur {len(vSession['questions'])} : "
                f"{vView['question']['question']}"
            )
            self.clock_label.setText(format_clock(vSession["duration"]))
            self.read_question()

    def fill_choices(self, pView):
        """Remplit une fois les listes de types de questions et de durées."""
        if self.mode_combo.count():
            return

        for vMode, vLabel in pView["modes"].items():
            self.mode_combo.addItem(vLabel, vMode)

        for vDuration in pView["durations"]:
            self.duration_combo.addItem(
                f"{format_clock(vDuration)} par réponse", vDuration
            )

        self.duration_combo.setCurrentIndex(1)

    @staticmethod
    def describe_progress(pView):
        """Retourne la progression : séances, dernière note, critère à travailler."""

        if not pView["count"]:
            return "Aucune séance pour l'instant : cinq questions, environ dix minutes."

        rText = (
            f"{pView['count']} séance(s) · dernière : {pView['last']['score']} % · "
            f"notes récentes : {', '.join(f'{vScore} %' for vScore in pView['recent'])}"
        )

        if pView["weakest"]:
            rText += f"\nÀ travailler : {pView['weakest'][0]}, {pView['weakest'][1].lower()}."

        return rText

    def read_question(self):
        """Lit la question à voix haute ; le chrono démarre à la fin de la lecture."""
        if self.view and self.view["question"] and self.seconds is None:
            self.speaker.speak(self.view["question"]["question"])

    def start_clock(self):
        """Démarre le chrono de la réponse, une seule fois par question."""
        if self.view is None or self.view["session"] is None or self.timer.isActive():
            return

        if self.seconds is not None or self.question_label.isHidden():
            return

        self.speaker.stop()
        self.clock.start()
        self.timer.start(250)
        self.begin_button.hide()
        self.done_button.show()
        self.show_clock()

    def show_clock(self):
        """Affiche le temps restant, en rouge une fois dépassé."""
        vRemaining = self.view["session"]["duration"] - self.clock.elapsed() / 1000
        self.clock_label.setText(format_clock(vRemaining))
        self.clock_label.setStyleSheet(
            f"color: {COLORS['danger']};" if vRemaining < 0 else ""
        )

    def finish_answer(self):
        """Arrête le chrono et affiche la grille de notation."""
        self.timer.stop()
        self.seconds = self.clock.elapsed() / 1000
        self.done_button.hide()

        for vGroup in self.rating_groups.values():
            vGroup.setExclusive(False)

            for vButton in vGroup.buttons():
                vButton.setChecked(False)

            vGroup.setExclusive(True)

        self.grid_widget.show()

    def validate(self, _pChecked=False):
        """Enregistre la note de la réponse et affiche le conseil."""
        vRatings = {
            vId: vGroup.checkedId() for vId, vGroup in self.rating_groups.items()
        }

        if min(vRatings.values()) < 0:
            show_message(
                self.message_label, "Notez la structure et l'exemple.", "warning"
            )
            return

        try:
            vFeedback = answer_oral(
                self.database_file,
                self.view["position"],
                self.seconds,
                vRatings["structure"],
                vRatings["example"],
                datetime.now(),
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.grid_widget.hide()
        show_message(
            self.message_label,
            f"Réponse notée {vFeedback['score']} % · {round(vFeedback['seconds'])} s, "
            f"{vFeedback['duration_label']}.\nConseil : {vFeedback['hint']}",
            "success" if vFeedback["score"] >= 70 else "warning",
        )

        if vFeedback["finished"]:
            self.view = build_oral_view(self.database_file)
            self.message_label.setText(
                self.message_label.text()
                + f"\nSéance terminée : {self.view['last']['score']} %."
            )
            self.next_button.setText("Nouvelle séance")
        else:
            self.next_button.setText("Question suivante")

        self.next_button.show()

    def start(self):
        """Commence une séance avec le type de questions et le temps choisis."""
        try:
            start_oral(
                self.database_file,
                self.mode_combo.currentData(),
                self.duration_combo.currentData(),
                datetime.now(),
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.refresh()

    def stop(self):
        """Abandonne la séance en cours."""
        stop_oral(self.database_file)
        self.refresh()
