"""Page des défis de programmation : énoncé, données personnelles et réponse"""

from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
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
    show_message,
)
from job.challenges import (
    build_challenge_list,
    build_challenge_view,
    get_challenge_input,
    submit_answer,
)
from utils.logger import get_logger
from utils.markdown import render_markdown

logger = get_logger(__name__)

STAR = "★"
EMPTY_STAR = "☆"
LIST_COLUMNS = 2


def format_stars(pStars):
    """Retourne les deux étoiles d'un défi, pleines selon les parties réussies."""

    rText = STAR * pStars + EMPTY_STAR * (2 - pStars)

    return rText


class ChallengesPage(QWidget):
    """Liste des défis et résolution du défi choisi."""

    def __init__(self, pDatabaseFile):
        """Construit la liste et le détail ; les défis sont lus par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.challenge_id = None
        self.hint_count = 0
        self.hints = []
        self.challenge_buttons = {}

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Défis",
            "Des problèmes à résoudre avec votre propre code, dans le langage de votre "
            "choix : seule la réponse est vérifiée",
            pIcon="trophy",
        )

        self.list_card, vListLayout = create_card(
            "Les défis", "Deux parties par défi, une étoile par partie réussie"
        )
        self.list_layout = QGridLayout()
        self.list_layout.setSpacing(8)
        vListLayout.addLayout(self.list_layout)

        vLayout.addWidget(self.list_card)
        vLayout.addWidget(self.create_detail_card())
        vLayout.addStretch(1)

    def create_detail_card(self):
        """Construit l'énoncé, les données, la réponse, les indices et la solution."""
        self.detail_card, vLayout = create_card()

        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.meta_label = QLabel()
        self.meta_label.setObjectName("cardSubtitle")
        self.statement_label = QLabel()
        self.statement_label.setWordWrap(True)

        self.example_edit = QPlainTextEdit()
        self.example_edit.setReadOnly(True)
        self.example_edit.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.example_edit.setMaximumHeight(140)
        self.example_label = QLabel()
        self.example_label.setObjectName("cardSubtitle")

        vCopyButton = create_button(
            "Copier mes données", "copy", pIconColor=COLORS["primary"]
        )
        vCopyButton.clicked.connect(self.copy_input)
        vSaveButton = create_button(
            "Enregistrer mes données…", "download", pIconColor=COLORS["primary"]
        )
        vSaveButton.clicked.connect(self.choose_input_file)

        self.answer_edit = QLineEdit()
        self.answer_edit.setPlaceholderText("Votre réponse")
        self.answer_edit.returnPressed.connect(self.submit)
        self.submit_button = create_button(
            "Valider", "circle-check", "primaryButton", COLORS["on_primary"]
        )
        self.submit_button.clicked.connect(self.submit)

        vAnswerRow = QHBoxLayout()
        vAnswerRow.addWidget(vCopyButton)
        vAnswerRow.addWidget(vSaveButton)
        vAnswerRow.addWidget(self.answer_edit, 1)
        vAnswerRow.addWidget(self.submit_button)

        self.answer_message = QLabel()
        self.answer_message.setWordWrap(True)

        self.hint_button = create_button("Afficher un indice", "sparkles")
        self.hint_button.clicked.connect(self.show_next_hint)
        self.hints_label = QLabel()
        self.hints_label.setWordWrap(True)
        self.hints_label.setObjectName("cardSubtitle")

        self.note_label = QLabel()
        self.note_label.setWordWrap(True)

        for vWidget in (
            self.title_label,
            self.meta_label,
            self.statement_label,
            self.example_label,
            self.example_edit,
        ):
            vLayout.addWidget(vWidget)

        vLayout.addLayout(vAnswerRow)
        vLayout.addWidget(self.answer_message)
        vLayout.addWidget(self.hint_button)
        vLayout.addWidget(self.hints_label)
        vLayout.addWidget(self.note_label)
        self.detail_card.hide()

        return self.detail_card

    def refresh(self):
        """Relit la progression et reconstruit la liste des défis."""
        try:
            vChallenges = build_challenge_list(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de charger les défis")
            return

        clear_layout(self.list_layout)
        self.challenge_buttons = {}

        for vIndex, vChallenge in enumerate(vChallenges):
            vButton = QPushButton(
                f"{format_stars(vChallenge['stars'])}   {vChallenge['title']}\n"
                f"{vChallenge['series']} · {vChallenge['level']}"
            )
            vButton.setObjectName("categoryButton")
            vButton.setCheckable(True)
            vButton.setChecked(vChallenge["id"] == self.challenge_id)
            vButton.clicked.connect(
                lambda _, pId=vChallenge["id"]: self.open_challenge(pId)
            )
            self.challenge_buttons[vChallenge["id"]] = vButton
            self.list_layout.addWidget(
                vButton, vIndex // LIST_COLUMNS, vIndex % LIST_COLUMNS
            )

        if self.challenge_id:
            self.show_challenge()

    def open_challenge(self, pChallengeId):
        """Affiche un défi choisi dans la liste."""
        self.challenge_id = pChallengeId
        self.hint_count = 0
        self.answer_edit.clear()
        show_message(self.answer_message, "")
        self.refresh()

    def show_challenge(self):
        """Affiche l'énoncé et l'état du défi courant."""
        vView = build_challenge_view(
            self.database_file, self.challenge_id, datetime.now()
        )

        for vId, vButton in self.challenge_buttons.items():
            vButton.setChecked(vId == self.challenge_id)

        self.title_label.setText(
            f"{vView['title']}  {format_stars(len(vView['solved']))}"
        )
        self.meta_label.setText(f"{vView['series']} · {vView['level']}")
        self.statement_label.setText(
            "".join(
                f"<h3>Partie {vIndex}</h3>{render_markdown(vStatement)}"
                for vIndex, vStatement in enumerate(vView["statements"], start=1)
            )
        )
        self.example_label.setText(
            "Exemple, avec ses réponses : "
            + " · ".join(
                f"partie {vIndex} : {vAnswer}"
                for vIndex, vAnswer in enumerate(vView["example_answers"], start=1)
            )
        )
        self.example_edit.setPlainText(vView["example"])

        vFinished = vView["next_part"] is None
        self.answer_edit.setEnabled(not vFinished)
        self.submit_button.setEnabled(not vFinished)
        self.answer_edit.setPlaceholderText(
            "Défi terminé"
            if vFinished
            else f"Réponse de la partie {vView['next_part']}"
        )
        self.hints = vView["hints"]
        self.hints_label.setText(
            "<br>".join(
                f"Indice {vIndex} : {vHint}"
                for vIndex, vHint in enumerate(self.hints[: self.hint_count], start=1)
            )
        )
        self.hint_button.setEnabled(self.hint_count < len(self.hints))
        self.note_label.setText(
            f"<h3>Solution commentée</h3>{render_markdown(vView['note'])}"
            if vView["note"]
            else ""
        )
        self.detail_card.show()

    def show_next_hint(self):
        """Dévoile l'indice suivant du défi courant."""
        self.hint_count += 1
        self.show_challenge()

    def copy_input(self):
        """Copie les données personnelles du défi dans le presse-papiers."""
        QApplication.clipboard().setText(
            get_challenge_input(self.database_file, self.challenge_id, datetime.now())
        )
        show_message(
            self.answer_message,
            "Données copiées : collez-les dans un fichier pour votre programme.",
        )

    def choose_input_file(self):
        """Demande où enregistrer les données personnelles du défi."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données",
            f"{self.challenge_id}.txt",
            "Fichier texte (*.txt)",
        )

        if vPath:
            self.save_input(vPath)

    def save_input(self, pPath):
        """Écrit les données personnelles du défi dans un fichier texte."""
        try:
            Path(pPath).write_text(
                get_challenge_input(
                    self.database_file, self.challenge_id, datetime.now()
                ),
                encoding="utf-8",
            )

        except OSError:
            logger.exception("Échec de l'enregistrement des données d'un défi")

            show_message(
                self.answer_message,
                "Les données n'ont pas pu être enregistrées.",
                "danger",
            )

        else:
            show_message(
                self.answer_message, f"Données enregistrées : {Path(pPath).name}"
            )

    def submit(self):
        """Vérifie la réponse saisie pour la partie en cours."""
        vView = build_challenge_view(
            self.database_file, self.challenge_id, datetime.now()
        )

        if vView["next_part"] is None:
            return

        try:
            _, vMessage, vTone = submit_answer(
                self.database_file,
                self.challenge_id,
                vView["next_part"],
                self.answer_edit.text(),
                datetime.now(),
            )

        except ValueError as vException:
            show_message(self.answer_message, str(vException), "warning")
            return

        self.answer_edit.clear()
        self.refresh()
        show_message(self.answer_message, vMessage, vTone)
