"""Page du profil du candidat, utilisé pour préparer les candidatures"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.interview_drill_panel import InterviewDrillPanel
from gui.star_answers_panel import StarAnswersPanel
from gui.theme import COLORS
from gui.widgets import (
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.assistant import CHATGPT_URL
from job.cv_import import (
    CV_EXTENSIONS,
    build_cv_prompt,
    extract_profile,
    merge_profile_texts,
    read_cv_text,
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
        self.cv_prompt = None

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
        # La hauteur libre va aux expériences : les variantes de CV, limitées en
        # hauteur, laisseraient sinon un vide au-dessus de leur champ.
        vGrid.setRowStretch(2, 1)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        self.import_button = create_button(
            "Importer un CV…", "upload", pIconColor=COLORS["primary"]
        )
        self.import_button.setToolTip(
            "Remplit le nom, la présentation et les compétences depuis un CV "
            "(" + ", ".join(CV_EXTENSIONS) + ")"
        )
        self.import_button.clicked.connect(self.choose_cv)

        # Les expériences se convertissent avec ChatGPT, après l'import du CV.
        self.prompt_button = create_button(
            "Copier la demande pour ChatGPT", "copy", pIconColor=COLORS["primary"]
        )
        self.prompt_button.setToolTip(
            "Convertit les expériences du CV au format attendu, à coller ici"
        )
        self.prompt_button.clicked.connect(self.copy_cv_prompt)
        self.prompt_button.hide()

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.import_button)
        vActions.addWidget(self.prompt_button)
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

        self.star_panel = StarAnswersPanel(pDatabaseFile)
        self.drill_panel = InterviewDrillPanel(pDatabaseFile)

        vLayout.addWidget(vCard, 1)
        vLayout.addWidget(self.star_panel)
        vLayout.addWidget(self.drill_panel)

    def refresh(self):
        """Remplit le formulaire avec le profil enregistré."""
        self.star_panel.refresh()
        self.drill_panel.refresh()

        try:
            vTexts = profile_to_texts(load_profile(self.database_file))

        except Exception:
            logger.exception("Impossible de lire le profil")

            show_message(self.message_label, "Le profil n'a pas pu être lu.", "danger")

        else:
            self.name_edit.setText(vTexts["name"])
            self.headline_edit.setText(vTexts["headline"])
            self.skills_edit.setText(vTexts["skills"])
            self.experiences_edit.setPlainText(vTexts["experiences"])
            self.cv_edit.setPlainText(vTexts["cv_variants"])

    def get_texts(self):
        """Retourne les textes saisis dans le formulaire."""
        rTexts = {
            "name": self.name_edit.text(),
            "headline": self.headline_edit.text(),
            "skills": self.skills_edit.text(),
            "experiences": self.experiences_edit.toPlainText(),
            "cv_variants": self.cv_edit.toPlainText(),
        }

        return rTexts

    def choose_cv(self):
        """Demande le CV à importer."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer un CV",
            str(Path.home()),
            "CV (" + " ".join(f"*{vExtension}" for vExtension in CV_EXTENSIONS) + ")",
        )

        if vPath:
            self.import_cv(vPath)

    def import_cv(self, pPath):
        """Complète le formulaire depuis le CV, sans écraser ce qui est saisi."""
        try:
            vText = read_cv_text(pPath, Path(pPath).read_bytes())

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except OSError:
            logger.exception("CV illisible sur le disque")

            show_message(self.message_label, "Le CV n'a pas pu être ouvert.", "danger")
            return

        vExtracted = extract_profile(vText)
        vTexts = merge_profile_texts(self.get_texts(), vExtracted)

        self.name_edit.setText(vTexts["name"])
        self.headline_edit.setText(vTexts["headline"])
        self.skills_edit.setText(vTexts["skills"])

        self.cv_prompt = build_cv_prompt(vText)
        self.prompt_button.show()

        show_message(
            self.message_label,
            f"CV importé : {len(vExtracted['skills'])} compétence(s) repérée(s). "
            "Pour les expériences, copiez la demande pour ChatGPT et collez sa "
            "réponse ci-dessus. Vérifiez puis enregistrez.",
        )

    def copy_cv_prompt(self):
        """Copie la demande de conversion du CV puis ouvre ChatGPT."""
        QApplication.clipboard().setText(self.cv_prompt)
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        show_message(
            self.message_label,
            "Demande copiée : collez-la dans ChatGPT (Ctrl+V), puis sa réponse "
            "dans Expériences et Variantes de CV.",
        )

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
            show_message(self.message_label, str(vException), "warning")

        except Exception:
            logger.exception("Échec de l'enregistrement du profil")

            show_message(
                self.message_label,
                "Le profil n'a pas pu être enregistré.",
                "danger",
            )

        else:
            show_message(
                self.message_label,
                f"Profil enregistré : {len(vProfile['skills'])} compétence(s), "
                f"{len(vProfile['experiences'])} expérience(s), "
                f"{len(vProfile['cv_variants'])} CV.",
            )
            self.star_panel.refresh()
