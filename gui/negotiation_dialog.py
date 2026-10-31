"""Fenêtre du jeu de négociation salariale : dialogue, réponses, score et conseils"""

from html import escape

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextBrowser, QVBoxLayout

from gui.widgets import clear_layout, create_button, show_message
from job.presentation import format_euros
from job.salary_negotiation import (
    build_negotiation_view,
    play_negotiation,
    start_negotiation,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def describe_transcript(pGame):
    """Retourne le dialogue en HTML, réplique par réplique."""

    rHtml = "".join(
        f"<p><b>{'Recruteur' if vSpeaker == 'recruiter' else 'Vous'} :</b> "
        f"{escape(vText)}</p>"
        for vSpeaker, vText in pGame["transcript"]
    )

    return rHtml


class NegotiationDialog(QDialog):
    """Partie de négociation sur le marché d'une offre."""

    def __init__(self, pParent, pDatabaseFile, pOffer):
        """Construit le dialogue et commence la partie."""
        super().__init__(pParent)

        self.database_file = pDatabaseFile
        self.offer = pOffer
        self.setWindowTitle("Simuler la négociation salariale")
        self.resize(640, 620)

        self.context_label = QLabel()
        self.context_label.setObjectName("cardSubtitle")
        self.context_label.setWordWrap(True)
        self.transcript = QTextBrowser()
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.choices_layout = QVBoxLayout()

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.context_label)
        vLayout.addWidget(self.transcript, 1)
        vLayout.addWidget(self.message_label)
        vLayout.addLayout(self.choices_layout)

        self.start()

    def start(self):
        """Commence une partie ; sans marché, explique pourquoi."""
        try:
            start_negotiation(self.database_file, self.offer)

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.show_game(build_negotiation_view(self.database_file)["game"])

    def show_game(self, pGame):
        """Affiche le dialogue, puis les réponses possibles ou le résultat."""
        self.context_label.setText(
            f"{pGame['title']} · marché {format_euros(pGame['low'])} à "
            f"{format_euros(pGame['high'])} brut annuel, médiane "
            f"{format_euros(pGame['median'])} · votre salaire visé : "
            f"{format_euros(pGame['target'])}"
        )
        self.transcript.setHtml(describe_transcript(pGame))
        clear_layout(self.choices_layout)
        show_message(self.message_label, "")

        for vChoice, vText in pGame["choices"]:
            vButton = QPushButton(vText)
            vButton.clicked.connect(lambda _pChecked=False, pId=vChoice: self.play(pId))
            self.choices_layout.addWidget(vButton)

        if not pGame["choices"]:
            show_message(
                self.message_label,
                (
                    f"Accord à {format_euros(pGame['offer'])} brut annuel"
                    if pGame["deal"]
                    else "Pas d'accord"
                )
                + f" · score {pGame['score']} / 100\n"
                + "\n".join(f"• {vAdvice}" for vAdvice in pGame["advice"]),
                "success" if pGame["score"] >= 70 else "warning",
            )
            vReplay = create_button("Rejouer", "banknote")
            vReplay.clicked.connect(self.start)
            self.choices_layout.addWidget(vReplay)

    def play(self, pChoice):
        """Joue une réponse et affiche la réaction du recruteur."""
        try:
            vGame = play_negotiation(self.database_file, pChoice)

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.show_game(vGame)
