"""Page de révision technique : thèmes, questions à choix multiple et corrections"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.dialogs import show_text_dialog
from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.assistant import CHATGPT_URL
from job.quiz import (
    QUIZ_MODES,
    answer_question,
    build_quiz_overview,
    build_quiz_statistics,
    flag_question,
    load_active_quiz,
    pick_question,
)
from job.quiz_domains import group_themes
from job.quiz_import import (
    GENERATION_COUNTS,
    GENERATION_LEVELS,
    IMPORT_EXTENSIONS,
    build_generation_prompt,
    describe_quiz_import,
    export_quiz_pack,
    import_questions,
    import_questions_file,
)
from job.presentation import CHART_PALETTE
from storage.quiz_answers import get_last_answers
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from utils.markdown import render_markdown
from utils.logger import get_logger

logger = get_logger(__name__)

THEME_COLUMNS = 3

# Hauteur d'affichage des schémas des questions importées
VISUAL_HEIGHT = 280


class QuizPage(QWidget):
    """Propose des questions par thème et suit la progression."""

    def __init__(self, pDatabaseFile):
        """Construit la carte de question, masquée, puis la liste des thèmes."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.theme_key = None
        self.mode = None
        self.question = None

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Révision",
            "QCM techniques pour préparer les entretiens, thèmes conseillés selon "
            "vos offres",
            pIcon="graduation-cap",
        )

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.hide()

        # Pastilles de domaine : une seule cochée, « Tous » par défaut
        self.domain = None
        self.domain_group = QButtonGroup(self)
        self.domain_layout = QHBoxLayout()
        self.domain_layout.setSpacing(8)

        # Les thèmes sont reconstruits à chaque rafraîchissement dans un conteneur
        # remplacé d'un bloc : domaines et sous-domaines y sont imbriqués.
        self.themes_holder = QVBoxLayout()
        self.themes_holder.setContentsMargins(0, 0, 0, 0)

        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.create_question_card())
        vLayout.addLayout(self.domain_layout)
        vLayout.addLayout(self.themes_holder)

        # Guides pratiques des packs importés, masqués tant qu'il n'y en a pas
        self.guides_card, vGuidesLayout = create_card(
            "Guides pratiques", "Méthodes de diagnostic livrées avec les questions"
        )
        # Plusieurs guides par ligne, sans déborder dans une fenêtre réduite
        self.guides_layout = QGridLayout()
        self.guides_layout.setSpacing(8)
        vGuidesLayout.addLayout(self.guides_layout)
        self.guides_card.hide()

        vLayout.addWidget(self.guides_card)
        vLayout.addWidget(self.create_import_card())
        vLayout.addWidget(self.create_statistics_card())
        vLayout.addStretch()

    def create_question_card(self):
        """Construit la carte de la question, de ses choix et de sa correction."""
        self.question_card, vLayout = create_card()
        self.question_card.hide()

        self.meta_label = QLabel()
        self.meta_label.setObjectName("cardSubtitle")

        self.question_label = QLabel()
        self.question_label.setObjectName("cardTitle")
        self.question_label.setWordWrap(True)

        self.code_edit = QPlainTextEdit()
        self.code_edit.setReadOnly(True)
        self.code_edit.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.code_edit.setMaximumHeight(160)

        self.choices_group = QButtonGroup(self)

        self.choices_layout = QVBoxLayout()
        self.choices_layout.setSpacing(8)

        self.verdict_label = QLabel()
        self.verdict_label.setWordWrap(True)

        self.explanation_label = QLabel()
        self.explanation_label.setWordWrap(True)

        # Schéma et références des questions importées, montrés avec la correction
        self.visual_widget = QSvgWidget()
        # Schémas dessinés en sombre sur blanc : fond blanc, même en thème sombre.
        self.visual_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.visual_widget.setStyleSheet("background: #ffffff; border-radius: 8px;")
        self.visual_widget.hide()

        self.references_label = QLabel()
        self.references_label.setTextFormat(Qt.TextFormat.RichText)
        self.references_label.setOpenExternalLinks(True)
        self.references_label.setWordWrap(True)
        self.references_label.hide()

        self.validate_button = create_button("Valider", pObjectName="primaryButton")
        self.validate_button.clicked.connect(self.validate)

        self.next_button = create_button(
            "Question suivante", "arrow-right", pIconColor=COLORS["primary"]
        )
        self.next_button.clicked.connect(lambda: self.start(self.theme_key, self.mode))

        # Une question importée peut être fausse : elle sort des tirages.
        self.flag_button = create_button(
            "Question douteuse", "circle-alert", pIconColor=COLORS["warning"]
        )
        self.flag_button.setToolTip("Retire cette question des prochains tirages")
        self.flag_button.clicked.connect(self.flag_current_question)

        vButtons = QHBoxLayout()
        vButtons.addWidget(self.validate_button)
        vButtons.addWidget(self.next_button)
        vButtons.addStretch()
        vButtons.addWidget(self.flag_button)

        vLayout.addWidget(self.meta_label)
        vLayout.addWidget(self.question_label)
        vLayout.addWidget(self.code_edit)
        vLayout.addLayout(self.choices_layout)
        vLayout.addWidget(self.verdict_label)
        vLayout.addWidget(self.explanation_label)
        vLayout.addWidget(self.visual_widget)
        vLayout.addWidget(self.references_label)
        vLayout.addLayout(vButtons)

        return self.question_card

    def create_import_card(self):
        """Construit la génération de questions avec ChatGPT et leur import."""
        self.theme_combo = QComboBox()
        self.theme_combo.setEditable(True)
        self.theme_combo.setToolTip("Thème existant ou nouveau, par exemple Kafka")

        self.level_combo = QComboBox()

        for vLevel, vLabel in GENERATION_LEVELS.items():
            self.level_combo.addItem(vLabel, vLevel)

        self.count_combo = QComboBox()

        for vCount in GENERATION_COUNTS:
            self.count_combo.addItem(f"{vCount} questions", vCount)

        vGenerateButton = create_button(
            "Générer avec ChatGPT", "bot", "primaryButton", COLORS["on_primary"]
        )
        vGenerateButton.setToolTip(
            "Copie une demande au format attendu et ouvre ChatGPT"
        )
        vGenerateButton.clicked.connect(self.copy_generation_prompt)

        vOptions = QHBoxLayout()
        vOptions.addWidget(self.theme_combo, 2)
        vOptions.addWidget(self.level_combo, 1)
        vOptions.addWidget(self.count_combo, 1)
        vOptions.addWidget(vGenerateButton)

        self.import_edit = QPlainTextEdit()
        self.import_edit.setPlaceholderText(
            "Collez ici la réponse de ChatGPT (JSON), puis importez"
        )
        self.import_edit.setMaximumHeight(110)

        vPasteButton = create_button(
            "Importer le texte collé", "download", pIconColor=COLORS["primary"]
        )
        vPasteButton.clicked.connect(self.import_pasted_questions)

        vFileButton = create_button(
            "Importer un fichier…", "upload", pIconColor=COLORS["primary"]
        )
        vFileButton.setToolTip("Fichier .json, ou archive .zip de fichiers .json")
        vFileButton.clicked.connect(self.choose_questions_file)

        vExportButton = create_button(
            "Exporter mes questions…", "download", pIconColor=COLORS["primary"]
        )
        vExportButton.setToolTip(
            "Pack .zip des questions importées, schémas et guides, réimportable"
        )
        vExportButton.clicked.connect(self.choose_export_file)

        self.import_message = QLabel()
        self.import_message.setObjectName("cardSubtitle")
        self.import_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vPasteButton)
        vActions.addWidget(vFileButton)
        vActions.addWidget(vExportButton)
        vActions.addWidget(self.import_message, 1)

        vCard, vLayout = create_card(
            "Ajouter des questions",
            "Générées avec votre compte ChatGPT, puis vérifiées une à une à "
            "l'import : une question incomplète ou en double est écartée.",
        )
        vLayout.addLayout(vOptions)
        vLayout.addWidget(self.import_edit)
        vLayout.addLayout(vActions)

        return vCard

    def copy_generation_prompt(self):
        """Copie la demande de questions pour ChatGPT puis ouvre le site."""
        vTheme = self.theme_combo.currentText().strip()

        if not vTheme:
            self.import_message.setText("Choisissez ou saisissez un thème.")
            return

        QApplication.clipboard().setText(
            build_generation_prompt(
                load_active_quiz(self.database_file),
                vTheme,
                self.level_combo.currentData(),
                self.count_combo.currentData(),
            )
        )
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        self.import_message.setText(
            "Demande copiée : collez-la dans ChatGPT, puis sa réponse ci-dessus."
        )

    def import_pasted_questions(self):
        """Importe les questions collées dans la zone de texte."""
        self.run_import(
            lambda: import_questions(
                self.database_file,
                self.theme_combo.currentText(),
                self.import_edit.toPlainText(),
                datetime.now(),
            )
        )

    def choose_questions_file(self):
        """Demande le fichier de questions à importer."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer des questions",
            str(Path.home()),
            "Questions ("
            + " ".join(f"*{vExtension}" for vExtension in IMPORT_EXTENSIONS)
            + ")",
        )

        if vPath:
            self.run_import(
                lambda: import_questions_file(
                    self.database_file,
                    self.theme_combo.currentText(),
                    vPath,
                    Path(vPath).read_bytes(),
                    datetime.now(),
                )
            )

    def choose_export_file(self):
        """Demande où enregistrer le pack de questions, puis l'écrit."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter mes questions",
            str(Path.home() / f"questions-revision-{datetime.now():%Y%m%d}.zip"),
            "Archive (*.zip)",
        )

        if vPath:
            self.export_questions(vPath)

    def export_questions(self, pPath):
        """Écrit les questions importées dans un pack réimportable."""
        try:
            vCount = export_quiz_pack(self.database_file, pPath)

        except ValueError as vException:
            self.import_message.setText(str(vException))

        except Exception:
            logger.exception("Échec de l'export des questions de révision")

            self.import_message.setText("L'export a échoué. Voir les journaux.")

        else:
            self.import_message.setText(
                f"{vCount} question(s) exportée(s) : {Path(pPath).name}"
            )

    def run_import(self, pImport):
        """Lance un import, affiche son bilan et met à jour les thèmes."""
        try:
            vReport = pImport()

        except ValueError as vException:
            self.import_message.setText(str(vException))
            return

        except Exception:
            logger.exception("Échec de l'import de questions de révision")

            self.import_message.setText("L'import a échoué. Voir les journaux.")
            return

        self.import_message.setText(describe_quiz_import(vReport))

        if vReport["added"]:
            self.import_edit.clear()

        self.refresh()

    def flag_current_question(self):
        """Retire la question affichée des tirages, après confirmation."""
        if (
            QMessageBox.question(
                self,
                "Question douteuse",
                "Cette question ne sera plus proposée. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        flag_question(self.database_file, self.question["id"])

        self.refresh()
        self.start(self.theme_key, self.mode)

    def create_statistics_card(self):
        """Construit les chiffres de la révision et le graphique des derniers jours."""
        self.statistic_cards = {
            "acquired": StatisticCard("Questions acquises", "circle-check", "green"),
            "answers": StatisticCard("Réponses données", "graduation-cap", "blue"),
            "rate": StatisticCard("Bonnes réponses", "sparkles", "purple"),
            "streak": StatisticCard("Jours de révision d'affilée", "calendar", "amber"),
        }

        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.statistic_cards.values():
            vCards.addWidget(vCard, 1)

        self.statistics_chart = BarChart()

        vCard, vLayout = create_card(
            "Mes statistiques", "Progression globale et réponses des 14 derniers jours"
        )
        vLayout.addLayout(vCards)
        vLayout.addWidget(self.statistics_chart)

        return vCard

    def show_statistics(self, pStatistics):
        """Affiche les chiffres de la révision et le graphique des derniers jours."""
        vCards = self.statistic_cards

        vCards["acquired"].set_value(
            f"{pStatistics['acquired']} / {pStatistics['total']}"
        )
        vCards["answers"].set_value(str(pStatistics["answers"]))
        vCards["rate"].set_value(
            "-" if pStatistics["rate"] is None else f"{pStatistics['rate']} %"
        )
        vCards["streak"].set_value(str(pStatistics["streak"]))

        self.statistics_chart.set_series(
            [f"{vDay:%d/%m}" for vDay, _, _ in pStatistics["days"]],
            [
                (
                    "Réponses",
                    CHART_PALETTE[0],
                    [vCount for _, vCount, _ in pStatistics["days"]],
                ),
                (
                    "Bonnes réponses",
                    CHART_PALETTE[1],
                    [vCorrect for _, _, vCorrect in pStatistics["days"]],
                ),
            ],
            pAxes=("Jour", "Réponses par jour"),
            pEmptyText="Aucune réponse ces 14 derniers jours",
        )

    def refresh(self):
        """Relit la progression et reconstruit les cartes des thèmes."""
        try:
            vThemes = build_quiz_overview(
                self.database_file, load_active_quiz(self.database_file)
            )
            self.show_statistics(
                build_quiz_statistics(self.database_file, vThemes, datetime.now())
            )

        except Exception:
            logger.exception("Impossible de charger la révision")

            self.message_label.setText("Les questions n'ont pas pu être chargées.")
            self.message_label.show()
            return

        self.refresh_guides()

        vCurrent = self.theme_combo.currentText()
        self.theme_combo.clear()
        self.theme_combo.addItems(sorted(vTheme["label"] for vTheme in vThemes))
        self.theme_combo.setCurrentText(vCurrent)

        self.themes = vThemes
        self.refresh_domains()
        self.show_themes()

    def refresh_domains(self):
        """Propose une pastille par domaine qui contient des thèmes."""
        clear_layout(self.domain_layout)

        for vButton in self.domain_group.buttons():
            self.domain_group.removeButton(vButton)

        vDomains = [vDomain for vDomain, _ in group_themes(self.themes)]

        if self.domain not in vDomains:
            self.domain = None

        for vDomain in [None, *vDomains]:
            vButton = create_button(
                vDomain or "Tous les domaines", pObjectName="segmentButton"
            )
            vButton.setCheckable(True)
            vButton.setChecked(vDomain == self.domain)
            vButton.clicked.connect(
                lambda _=False, pDomain=vDomain: self.select_domain(pDomain)
            )
            self.domain_group.addButton(vButton)
            self.domain_layout.addWidget(vButton)

        self.domain_layout.addStretch()

    def select_domain(self, pDomain):
        """Limite l'affichage des thèmes à un domaine, ou les montre tous."""
        self.domain = pDomain
        self.show_themes()

    def show_themes(self):
        """Affiche les thèmes du domaine choisi, rangés par sous-domaine."""
        clear_layout(self.themes_holder)

        vContainer = QWidget()
        vLayout = QVBoxLayout(vContainer)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(12)

        for vDomain, vSections in group_themes(self.themes, self.domain):
            vTitle = QLabel(vDomain)
            vTitle.setObjectName("cardTitle")
            vLayout.addWidget(vTitle)

            for vSubdomain, vThemes in vSections:
                vSubtitle = QLabel(vSubdomain)
                vSubtitle.setObjectName("fieldLabel")

                vGrid = QGridLayout()
                vGrid.setSpacing(16)

                for vColumn in range(THEME_COLUMNS):
                    vGrid.setColumnStretch(vColumn, 1)

                for vIndex, vTheme in enumerate(vThemes):
                    vGrid.addWidget(
                        self.create_theme_card(vTheme), *divmod(vIndex, THEME_COLUMNS)
                    )

                vLayout.addWidget(vSubtitle)
                vLayout.addLayout(vGrid)

        self.themes_holder.addWidget(vContainer)

    def create_theme_card(self, pTheme):
        """Crée la carte d'un thème : progression, intérêt et boutons."""
        rCard, vLayout = create_card(pTheme["label"])

        # Largeur fixée par la grille seule : les colonnes restent égales.
        rCard.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        vParts = [f"{pTheme['correct']} / {pTheme['total']} acquises"]

        if pTheme["to_review"]:
            vParts.append(f"{pTheme['to_review']} à revoir")

        vParts.append(
            f"demandé dans {pTheme['offer_count']} offre(s)"
            if pTheme["offer_count"]
            else "pas encore demandé dans vos offres"
        )

        vInfo = QLabel(" · ".join(vParts))
        vInfo.setObjectName("cardSubtitle")
        vInfo.setWordWrap(True)

        vProgress = QProgressBar()
        vProgress.setTextVisible(False)
        vProgress.setValue(pTheme["score"])

        vStart = create_button("Réviser", pObjectName="primaryButton")
        vStart.clicked.connect(lambda: self.start(pTheme["key"], "discover"))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vStart)

        if pTheme["to_review"]:
            vReview = create_button("Revoir les erreurs")
            vReview.clicked.connect(lambda: self.start(pTheme["key"], "review"))
            vButtons.addWidget(vReview)

        if pTheme["guide"]:
            vGuide = create_button("Guide", "file-text", pIconColor=COLORS["primary"])
            vGuide.clicked.connect(lambda: self.show_guide(pTheme["guide"]))
            vButtons.addWidget(vGuide)

        vButtons.addStretch()

        vLayout.addWidget(vInfo)
        vLayout.addWidget(vProgress)
        vLayout.addLayout(vButtons)

        return rCard

    def show_extras(self, pQuestion):
        """Affiche le schéma et les références d'une question, s'il y en a."""
        vVisual = pQuestion.get("visual")
        vContent = (
            get_quiz_asset(self.database_file, vVisual["asset"]) if vVisual else None
        )

        if vContent:
            self.visual_widget.load(QByteArray(vContent.encode("utf-8")))
            self.visual_widget.setToolTip(vVisual["alt"])

            # Chaque chargement remet le rendu à zéro : proportions et taille
            # d'origine sont réappliquées, à une hauteur fixe.
            vRenderer = self.visual_widget.renderer()
            vRenderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            vSize = vRenderer.defaultSize()
            self.visual_widget.setFixedSize(
                round(VISUAL_HEIGHT * vSize.width() / max(vSize.height(), 1)),
                VISUAL_HEIGHT,
            )

        self.visual_widget.setVisible(bool(vContent))

        vLinks = [
            f'<a href="{escape(vReference["url"])}">{escape(vReference["title"])}</a>'
            for vReference in pQuestion.get("references", [])
        ]

        self.references_label.setText("Pour aller plus loin : " + " · ".join(vLinks))
        self.references_label.setVisible(bool(vLinks))

    def show_guide(self, pName):
        """Ouvre un guide pratique, mis en forme."""
        vGuide = get_quiz_guide(self.database_file, pName)

        if vGuide:
            show_text_dialog(
                self, vGuide["title"], pHtml=render_markdown(vGuide["content"])
            )

    def refresh_guides(self):
        """Liste les guides pratiques importés avec les questions."""
        clear_layout(self.guides_layout)

        vGuides = get_quiz_guides(self.database_file)

        for vIndex, vGuide in enumerate(vGuides):
            vButton = create_button(
                vGuide["title"], "file-text", pIconColor=COLORS["primary"]
            )
            vButton.clicked.connect(
                lambda _=False, pName=vGuide["name"]: self.show_guide(pName)
            )
            self.guides_layout.addWidget(vButton, *divmod(vIndex, THEME_COLUMNS))

        self.guides_card.setVisible(bool(vGuides))

    def start(self, pThemeKey, pMode):
        """Affiche une nouvelle question du thème, ou signale qu'il n'y en a plus."""
        vQuiz = load_active_quiz(self.database_file)

        self.theme_key = pThemeKey
        self.mode = pMode
        self.question = pick_question(
            vQuiz, pThemeKey, pMode, get_last_answers(self.database_file)
        )

        self.question_card.show()

        # La question s'affiche en haut de la page : on y remonte.
        self.findChild(QScrollArea).verticalScrollBar().setValue(0)
        self.verdict_label.clear()
        self.explanation_label.clear()
        self.visual_widget.hide()
        self.references_label.hide()
        self.next_button.hide()

        clear_layout(self.choices_layout)

        for vButton in self.choices_group.buttons():
            self.choices_group.removeButton(vButton)

        if self.question is None:
            self.meta_label.setText(vQuiz[pThemeKey]["label"])
            self.question_label.setText("Aucune question ratée à revoir dans ce thème.")
            self.code_edit.hide()
            self.validate_button.hide()
            self.flag_button.hide()
            return

        self.meta_label.setText(
            f"{vQuiz[pThemeKey]['label']} · {self.question['level']} · "
            f"{QUIZ_MODES[pMode]}"
        )
        self.question_label.setText(self.question["question"])
        self.code_edit.setPlainText(self.question.get("code", ""))
        self.code_edit.setVisible(bool(self.question.get("code")))
        self.validate_button.show()
        self.flag_button.show()

        # L'identifiant du bouton est l'indice d'origine du choix, avant mélange.
        for vIndex, vChoice in self.question["shuffled"]:
            vButton = QRadioButton(vChoice)
            self.choices_group.addButton(vButton, vIndex)
            self.choices_layout.addWidget(vButton)

    def validate(self):
        """Corrige la réponse choisie et affiche l'explication."""
        vChoice = self.choices_group.checkedId()

        if vChoice < 0:
            self.verdict_label.setText("Choisissez une réponse.")
            return

        vResult = answer_question(
            self.database_file,
            load_active_quiz(self.database_file),
            self.question["id"],
            vChoice,
            datetime.now(),
        )

        vTone = "success" if vResult["correct"] else "danger"

        self.verdict_label.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")
        self.verdict_label.setText(
            "Bonne réponse."
            if vResult["correct"]
            else f"Réponse incorrecte. Réponse attendue : {vResult['answer']}"
        )
        self.explanation_label.setText(vResult["explanation"])
        self.show_extras(vResult["question"])

        for vButton in self.choices_group.buttons():
            vButton.setEnabled(False)

        self.validate_button.hide()
        self.next_button.show()

        self.refresh()
