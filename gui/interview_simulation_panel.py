"""Simulation d'entretien technique : question ouverte, réponse modèle, points cochés"""

from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.interview_simulation import (
    get_current_question,
    get_history,
    list_themes,
    load_simulation,
    record_answer,
    start_simulation,
    stop_simulation,
    summarize_simulation,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Séries récentes rappelées sous la carte
SHOWN_HISTORY = 3

ANSWER_EDIT_HEIGHT = 90


class InterviewSimulationPanel(QWidget):  # pylint: disable=too-many-instance-attributes
    """Pose une série de questions techniques comme un recruteur."""

    def __init__(self, pDatabaseFile):
        """Construit la carte ; la série en cours est relue par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.question = None
        self.point_checks = []

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list_themes())

        self.start_button = create_button(
            "Commencer", "graduation-cap", "primaryButton"
        )
        self.start_button.clicked.connect(self.start)

        self.stop_button = create_button("Arrêter", "history")
        self.stop_button.clicked.connect(self.stop)

        self.position_label = QLabel()
        self.position_label.setObjectName("cardSubtitle")

        self.question_label = QLabel()
        self.question_label.setObjectName("activityTitle")
        self.question_label.setWordWrap(True)

        self.answer_edit = QPlainTextEdit()
        self.answer_edit.setPlaceholderText(
            "Votre réponse, à l'oral ou ici pour vous entraîner à la formuler"
        )
        self.answer_edit.setFixedHeight(ANSWER_EDIT_HEIGHT)

        self.reveal_button = create_button(
            "Voir la réponse attendue", "file-text", pIconColor=COLORS["primary"]
        )
        self.reveal_button.clicked.connect(self.reveal)

        self.model_label = QLabel()
        self.model_label.setWordWrap(True)

        self.points_title = QLabel("Cochez les points clés que vous avez cités :")
        self.points_title.setObjectName("fieldLabel")

        self.points_layout = QVBoxLayout()
        self.points_layout.setSpacing(4)

        self.next_button = create_button(
            "Valider et continuer", pObjectName="primaryButton"
        )
        self.next_button.clicked.connect(self.validate)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        self.history_label = QLabel()
        self.history_label.setObjectName("cardSubtitle")
        self.history_label.setWordWrap(True)

        vStartRow = QHBoxLayout()
        vStartRow.addWidget(self.theme_combo)
        vStartRow.addWidget(self.start_button)
        vStartRow.addWidget(self.stop_button)
        vStartRow.addStretch()

        vCard, vCardLayout = create_card(
            "Simulation d'entretien technique",
            "Cinq questions ouvertes, comme face à un recruteur. Répondez, puis "
            "cochez les points clés cités : une question à moins de la moitié "
            "rejoint l'entraînement à l'oral.",
            pIcon="graduation-cap",
            pKey="profile/simulation",
        )
        vCardLayout.addLayout(vStartRow)
        vCardLayout.addWidget(self.position_label)
        vCardLayout.addWidget(self.question_label)
        vCardLayout.addWidget(self.answer_edit)
        vCardLayout.addWidget(self.reveal_button)
        vCardLayout.addWidget(self.model_label)
        vCardLayout.addWidget(self.points_title)
        vCardLayout.addLayout(self.points_layout)
        vCardLayout.addWidget(self.next_button)
        vCardLayout.addWidget(self.message_label)
        vCardLayout.addWidget(self.history_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Reprend la série en cours, ou propose d'en commencer une."""
        try:
            vSimulation = load_simulation(self.database_file)
            vHistory = get_history(self.database_file)

        except Exception:
            logger.exception("Impossible de lire la simulation d'entretien")

            vSimulation, vHistory = None, []

        self.history_label.setText(
            "Dernières séries : "
            + " · ".join(
                f"{vEntry['theme']} {vEntry['score']} %"
                for vEntry in vHistory[:SHOWN_HISTORY]
            )
            if vHistory
            else ""
        )
        self.show_simulation(vSimulation)

    def show_simulation(self, pSimulation):
        """Affiche la question en cours, le bilan d'une série finie, ou rien."""
        self.question = get_current_question(pSimulation)
        vFinished = pSimulation is not None and self.question is None

        self.clear_points()
        self.model_label.hide()
        self.points_title.hide()
        self.next_button.hide()
        self.answer_edit.clear()
        self.answer_edit.setVisible(self.question is not None)
        self.reveal_button.setVisible(self.question is not None)
        self.stop_button.setVisible(pSimulation is not None)

        if self.question is not None:
            self.position_label.setText(
                f"{self.question['theme']} · question {self.question['position']} "
                f"sur {self.question['count']}"
            )
            self.question_label.setText(self.question["question"])

        elif vFinished:
            vSummary = summarize_simulation(pSimulation)

            self.position_label.setText("Série terminée")
            self.question_label.setText(
                f"Score : {vSummary['score']} % des points clés cités."
                + (
                    "\nÀ retravailler : " + " ; ".join(vSummary["weak"])
                    if vSummary["weak"]
                    else ""
                )
            )

        else:
            self.position_label.setText("")
            self.question_label.setText(
                "Choisissez un thème et commencez une série de questions."
            )

    def clear_points(self):
        """Retire les cases des points clés de la question précédente."""
        while self.points_layout.count():
            self.points_layout.takeAt(0).widget().deleteLater()

        self.point_checks = []

    def start(self):
        """Commence une série sur le thème choisi."""
        try:
            vSimulation = start_simulation(
                self.database_file, self.theme_combo.currentText(), datetime.now()
            )

        except Exception:
            logger.exception("Impossible de commencer la simulation d'entretien")
            show_message(
                self.message_label, "La simulation n'a pas pu commencer.", "danger"
            )
            return

        show_message(self.message_label, "")
        self.show_simulation(vSimulation)

    def reveal(self):
        """Montre la réponse modèle et une case par point clé."""
        if self.question is None:
            return

        self.model_label.setText(self.question["answer"])
        self.model_label.show()
        self.points_title.show()
        self.clear_points()

        for vPoint in self.question["points"]:
            vCheck = QCheckBox(vPoint)
            self.points_layout.addWidget(vCheck)
            self.point_checks.append(vCheck)

        self.reveal_button.hide()
        self.next_button.show()

    def validate(self):
        """Note la question d'après les points cochés et passe à la suivante."""
        vChecked = [
            vIndex
            for vIndex, vCheck in enumerate(self.point_checks)
            if vCheck.isChecked()
        ]

        try:
            record_answer(self.database_file, vChecked, datetime.now())

        except Exception:
            logger.exception("Échec de l'enregistrement de la simulation")
            show_message(
                self.message_label, "La réponse n'a pas pu être notée.", "danger"
            )
            return

        self.refresh()

    def stop(self):
        """Ferme la série en cours ou son bilan."""
        stop_simulation(self.database_file)
        self.refresh()
