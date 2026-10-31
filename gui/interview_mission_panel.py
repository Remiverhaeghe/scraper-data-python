"""Mission d'entretien d'une offre : étapes à cocher, avancement et boss"""

from PySide6.QtWidgets import QCheckBox, QLabel, QProgressBar, QVBoxLayout, QWidget

from gui.widgets import clear_layout, show_message
from job.interview_mission import build_mission, set_step
from job.preparation import match_offer
from job.profile import is_profile_empty, load_profile
from utils.logger import get_logger

logger = get_logger(__name__)


class InterviewMissionPanel(QWidget):
    """Avancement de la préparation d'un entretien, masqué tant que le profil est vide."""

    def __init__(self, pDatabaseFile):
        """Construit le titre, la barre d'avancement et la liste des étapes."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None
        self.missing = []

        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.steps_layout = QVBoxLayout()
        self.steps_layout.setSpacing(2)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 8)
        vLayout.addWidget(self.title_label)
        vLayout.addWidget(self.progress_bar)
        vLayout.addWidget(self.message_label)
        vLayout.addLayout(self.steps_layout)
        self.hide()

    def set_offer(self, pOffer):
        """Affiche la mission de l'offre, ou rien sans offre ni profil."""
        self.offer = pOffer
        vProfile = load_profile(self.database_file)

        if not pOffer or not pOffer.get("source") or is_profile_empty(vProfile):
            self.hide()
            return

        self.missing = match_offer(vProfile, pOffer)["missing"]
        self.refresh()

    def refresh(self):
        """Relit la mission et reconstruit les étapes."""
        try:
            vMission = build_mission(self.database_file, self.offer, self.missing)

        except Exception:
            logger.exception("Impossible de lire la mission d'entretien")
            self.hide()
            return

        self.title_label.setText(f"Mission entretien · {vMission['percent']} %")
        self.progress_bar.setValue(vMission["percent"])
        show_message(
            self.message_label,
            (
                "Mission accomplie : vous êtes prêt pour le jour J."
                if vMission["completed_at"]
                else "Les manques et le boss se valident seuls d'après vos examens blancs."
            ),
            "success" if vMission["completed_at"] else None,
        )
        clear_layout(self.steps_layout)

        for vStep in vMission["steps"]:
            vText = f"{vStep['label']} · {vStep['task']}"

            if vStep["automatic"]:
                vLabel = QLabel(
                    f"{'✓' if vStep['done'] else '○'} {vText}\n{vStep['detail']}"
                )
                vLabel.setWordWrap(True)
                vLabel.setObjectName("cardSubtitle")
                self.steps_layout.addWidget(vLabel)
            else:
                vCheck = QCheckBox(vText)
                vCheck.setChecked(vStep["done"])
                vCheck.toggled.connect(
                    lambda pDone, pStep=vStep["id"]: self.tick(pStep, pDone)
                )
                self.steps_layout.addWidget(vCheck)

        self.show()

    def tick(self, pStep, pDone):
        """Coche ou décoche une étape, puis met l'avancement à jour."""
        set_step(self.database_file, self.offer, pStep, pDone)
        self.refresh()
