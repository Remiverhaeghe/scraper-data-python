"""Page du profil du candidat, utilisé pour préparer les candidatures"""

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.profile import build_profile, load_profile, profile_to_texts, save_profile
from utils.logger import get_logger

logger = get_logger(__name__)

# Aide de saisie, identique au web
EXPERIENCES_HELP = (
    "Une expérience par ligne : Poste | compétences | réalisation marquante\n"
    "Ex. Développeur backend | Java, Spring | Réduit de 40 % le temps de réponse"
)
CV_HELP = (
    "Une variante par ligne : Nom du CV | compétences mises en avant\n"
    "Ex. CV Java backend | Java, Spring, SQL"
)


def create_text_field(pLabel, pWidget):
    """Place un libellé au-dessus de son champ."""

    vLabel = QLabel(pLabel)
    vLabel.setObjectName("fieldLabel")

    rLayout = QVBoxLayout()
    rLayout.setSpacing(6)
    rLayout.addWidget(vLabel)
    rLayout.addWidget(pWidget)

    return rLayout


class ProfilePage(QWidget):
    """Saisie du profil : identité, compétences, expériences et variantes de CV."""

    def __init__(self, pDatabaseFile):
        """Construit le formulaire ; le profil enregistré est lu par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom affiché en signature de la lettre")

        self.headline_edit = QLineEdit()
        self.headline_edit.setPlaceholderText(
            "Ex. Développeur Java depuis 5 ans, orienté qualité et performance."
        )

        self.skills_edit = QLineEdit()
        self.skills_edit.setPlaceholderText("Ex. Java, Spring, SQL, Docker")

        self.experiences_edit = QPlainTextEdit()
        self.experiences_edit.setPlaceholderText(EXPERIENCES_HELP)

        self.cv_edit = QPlainTextEdit()
        self.cv_edit.setPlaceholderText(CV_HELP)
        self.cv_edit.setMaximumHeight(120)

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(16)
        vGrid.setVerticalSpacing(12)
        vGrid.addLayout(create_text_field("Nom", self.name_edit), 0, 0)
        vGrid.addLayout(create_text_field("Présentation", self.headline_edit), 0, 1)
        vGrid.addLayout(create_text_field("Compétences", self.skills_edit), 1, 0, 1, 2)
        vGrid.addLayout(
            create_text_field("Expériences", self.experiences_edit), 2, 0, 1, 2
        )
        vGrid.addLayout(create_text_field("Variantes de CV", self.cv_edit), 3, 0, 1, 2)
        vGrid.setColumnStretch(0, 1)
        vGrid.setColumnStretch(1, 2)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.message_label, 1)

        vCard, vCardLayout = create_card(
            "Mon profil",
            "Sert à comparer chaque offre à vos compétences, à conseiller un CV et à "
            "préparer l'entretien et la lettre. Il reste sur cet ordinateur.",
        )
        vCardLayout.addLayout(vGrid)
        vCardLayout.addLayout(vActions)

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Profil",
            "Vos compétences et expériences, pour préparer chaque candidature",
            pIcon="user",
        )

        vLayout.addWidget(vCard, 1)

    def refresh(self):
        """Remplit le formulaire avec le profil enregistré."""
        try:
            vTexts = profile_to_texts(load_profile(self.database_file))

        except Exception:
            logger.exception("Impossible de lire le profil")

            self.message_label.setText("Le profil n'a pas pu être lu.")

        else:
            self.name_edit.setText(vTexts["name"])
            self.headline_edit.setText(vTexts["headline"])
            self.skills_edit.setText(vTexts["skills"])
            self.experiences_edit.setPlainText(vTexts["experiences"])
            self.cv_edit.setPlainText(vTexts["cv_variants"])

    def save(self):
        """Enregistre le profil saisi."""
        try:
            vProfile = build_profile(
                self.name_edit.text(),
                self.headline_edit.text(),
                self.skills_edit.text(),
                self.experiences_edit.toPlainText(),
                self.cv_edit.toPlainText(),
            )
            save_profile(self.database_file, vProfile)

        except ValueError as vException:
            self.message_label.setText(str(vException))

        except Exception:
            logger.exception("Échec de l'enregistrement du profil")

            self.message_label.setText("Le profil n'a pas pu être enregistré.")

        else:
            self.message_label.setText(
                f"Profil enregistré : {len(vProfile['skills'])} compétence(s), "
                f"{len(vProfile['experiences'])} expérience(s), "
                f"{len(vProfile['cv_variants'])} CV."
            )
