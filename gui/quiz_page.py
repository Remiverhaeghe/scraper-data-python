"""Page de révision technique : thèmes, questions à choix multiple et corrections"""

from datetime import datetime
from html import escape

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs import show_text_dialog
from gui.quiz_answer import ClickableSvgWidget, add_answer_widgets, read_response
from gui.quiz_import_panel import QuizImportPanel
from gui.quiz_statistics_card import QuizStatisticsCard
from gui.theme import COLORS
from gui.widgets import (
    FlowLayout,
    clear_layout,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
    create_pill,
    create_scroll_content,
    show_message,
)
from job.quiz import (
    DEFAULT_MODE,
    QUIZ_MODES,
    THEME_STATUSES,
    answer_question,
    build_quiz_overview,
    build_quiz_statistics,
    describe_no_question,
    get_next_review,
    get_review_schedule,
    flag_question,
    load_active_quiz,
    pick_question,
)
from job.interview_revision import start_offer_exam
from job.quiz_domains import (
    DOMAIN_ICONS,
    count_categories,
    filter_guides,
    group_themes,
)
from job.quiz_generation import load_catalog
from job.schema_drawing import render_correction
from job.quiz_exam import (
    EXAM_QUESTION_COUNT,
    answer_exam,
    describe_exam_results,
    describe_exam_summary,
    format_countdown,
    get_exam_question,
    get_remaining_seconds,
    load_exam,
    load_exam_results,
    start_exam,
    stop_exam,
    summarize_exam,
)
from storage.quiz_answers import get_last_answers
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from utils.markdown import render_markdown
from utils.logger import get_logger

logger = get_logger(__name__)

# Largeur minimale d'une carte de thème : le nombre de colonnes en découle, pour
# que la page ne défile jamais horizontalement.
THEME_CARD_WIDTH = 340
MAX_THEME_COLUMNS = 3

# Mode de la page pendant un examen, à côté des modes de révision
EXAM_MODE = "exam"

# Sous cette marge, le minuteur passe à l'orange
TIMER_WARNING_SECONDS = 60

# Hauteur d'affichage des schémas des questions importées
VISUAL_HEIGHT = 280

# Marges de la page et de la carte autour d'un schéma, et largeur minimale :
# un schéma plus large que la place restante est réduit.
VISUAL_MARGINS = 120
MIN_VISUAL_WIDTH = 240
# Hauteur maximale du schéma attendu d'une question à construire
EXPECTED_SCHEMA_HEIGHT = 560


def show_svg(pWidget, pContent, pTooltip, pHeight, pShrinkOnly=False, pMaxWidth=None):
    """Affiche un SVG à une hauteur fixe, en gardant ses proportions.

    pShrinkOnly limite la hauteur sans jamais agrandir un dessin plus petit ;
    pMaxWidth réduit un dessin trop large, pour ne jamais défiler de côté.
    """
    pWidget.load(QByteArray(pContent.encode("utf-8")))
    pWidget.setToolTip(pTooltip)

    # Chaque chargement remet le rendu à zéro : proportions et taille d'origine
    # sont réappliquées, à une hauteur fixe.
    vRenderer = pWidget.renderer()
    vRenderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    vSize = vRenderer.defaultSize()
    vRatio = vSize.width() / max(vSize.height(), 1)
    vHeight = min(pHeight, vSize.height()) if pShrinkOnly else pHeight

    if pMaxWidth and vHeight * vRatio > pMaxWidth:
        vHeight = round(pMaxWidth / vRatio)

    pWidget.setFixedSize(round(vHeight * vRatio), vHeight)


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

        # Catégorie affichée : domaine puis sous-domaine, None pour tout montrer
        self.domain = None
        self.subdomain = None
        self.themes = []

        self.theme_columns = MAX_THEME_COLUMNS

        # Catégories au-dessus des thèmes : un onglet par domaine, puis les
        # sous-domaines en pastilles sur une ligne qui passe à la suivante.
        self.category_buttons = {}
        self.tabs_layout = FlowLayout(4)
        self.chips_layout = FlowLayout()

        self.filter_label = QLabel()
        self.filter_label.setObjectName("cardTitle")

        self.exam_button = create_button(
            "", "timer", "primaryButton", COLORS["on_primary"]
        )
        self.exam_button.setToolTip(
            "Questions tirées au hasard dans la catégorie choisie, notées et "
            "chronométrées"
        )
        self.exam_button.clicked.connect(self.start_exam)

        vHeader = QHBoxLayout()
        vHeader.addWidget(self.filter_label, 1)
        vHeader.addWidget(self.exam_button)

        # Les thèmes sont reconstruits à chaque rafraîchissement dans un conteneur
        # remplacé d'un bloc : domaines et sous-domaines y sont imbriqués.
        self.themes_holder = QVBoxLayout()
        self.themes_holder.setContentsMargins(0, 0, 0, 0)

        vBody = QVBoxLayout()
        vBody.setSpacing(12)
        vTabsBar = QFrame()
        vTabsBar.setObjectName("tabsBar")
        vTabsBar.setLayout(self.tabs_layout)

        vBody.addWidget(vTabsBar)
        vBody.addLayout(self.chips_layout)
        vBody.addLayout(vHeader)
        vBody.addLayout(self.themes_holder)

        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.create_question_card())
        vLayout.addLayout(vBody)

        # Guides pratiques des packs importés, masqués tant qu'il n'y en a pas
        self.guides_card, vGuidesLayout = create_card(
            "Guides pratiques", "Méthodes de diagnostic livrées avec les questions"
        )
        # Plusieurs guides par ligne, sans déborder dans une fenêtre réduite
        self.guides_layout = QGridLayout()
        self.guides_layout.setSpacing(8)
        vGuidesLayout.addLayout(self.guides_layout)
        self.guides_card.hide()

        self.import_panel = QuizImportPanel(pDatabaseFile)
        self.import_panel.questions_changed.connect(self.refresh)
        self.import_panel.questions_cleared.connect(self.forget_question)
        self.statistics_card = QuizStatisticsCard()

        vLayout.addWidget(self.guides_card)
        vLayout.addWidget(self.import_panel)
        vLayout.addWidget(self.statistics_card)
        # Facteur 1 : la place libre d'une page courte va ici, et non aux cartes
        # qui contiennent une zone de texte extensible.
        vLayout.addStretch(1)

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
        self.answer_widgets = []

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
        # Symbole ou schéma à lire pour répondre, montré sous l'énoncé ; pour une
        # question « zone », c'est sur lui que l'on clique.
        self.zone_point = None
        self.question_visual_widget = ClickableSvgWidget()
        self.question_visual_widget.clicked.connect(self.choose_point)
        self.question_visual_widget.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        self.question_visual_widget.setStyleSheet(
            "background: #ffffff; border-radius: 8px;"
        )
        self.question_visual_widget.hide()

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
        self.next_button.clicked.connect(self.go_next)

        self.stop_exam_button = create_button("Abandonner l'examen")
        self.stop_exam_button.clicked.connect(self.close_exam)
        self.stop_exam_button.hide()

        # Compte à rebours de l'examen, sur la durée conseillée d'une minute par
        # question : dépassé, il continue en négatif sans arrêter l'examen.
        self.current_exam = None
        self.timer_label = QLabel()
        self.timer_label.hide()

        self.exam_timer = QTimer(self)
        self.exam_timer.setInterval(1000)
        self.exam_timer.timeout.connect(self.update_exam_timer)

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
        vButtons.addWidget(self.timer_label)
        vButtons.addWidget(self.stop_exam_button)
        vButtons.addWidget(self.flag_button)

        vLayout.addWidget(self.meta_label)
        vLayout.addWidget(self.question_label)
        vLayout.addWidget(self.code_edit)
        vLayout.addWidget(self.question_visual_widget)
        vLayout.addLayout(self.choices_layout)
        vLayout.addWidget(self.verdict_label)
        vLayout.addWidget(self.explanation_label)
        vLayout.addWidget(self.visual_widget)
        vLayout.addWidget(self.references_label)
        vLayout.addLayout(vButtons)

        return self.question_card

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

    def forget_question(self):
        """Referme la question affichée, qui n'existe peut-être plus, et relit tout."""
        self.mode = None
        self.question_card.hide()
        self.refresh()

    def refresh(self):
        """Relit la progression et reconstruit les cartes des thèmes."""
        self.import_panel.refresh_packs_button()

        try:
            vThemes = build_quiz_overview(
                self.database_file, load_active_quiz(self.database_file)
            )
            vStatistics = build_quiz_statistics(
                self.database_file, vThemes, datetime.now()
            )

        except Exception:
            logger.exception("Impossible de charger la révision")

            show_message(
                self.message_label,
                "Les questions n'ont pas pu être chargées.",
                "danger",
            )
            self.message_label.show()
            return

        self.themes = vThemes
        self.statistics_card.show_progress(vThemes, vStatistics)
        self.import_panel.refresh(vThemes)
        self.select_category(self.domain, self.subdomain)

    def refresh_categories(self):
        """Reconstruit les onglets des domaines et les pastilles des sous-domaines.

        Toutes les rubriques du catalogue sont montrées, même sans question.
        """
        clear_layout(self.tabs_layout)
        clear_layout(self.chips_layout)
        self.category_buttons = {}

        vCounts = count_categories(self.themes)

        # Catégorie disparue (dernier thème supprimé) : retour à l'ensemble.
        if (self.domain, self.subdomain) not in vCounts:
            self.domain, self.subdomain = None, None

        for vKey, vCount in vCounts.items():
            vDomain, vSubdomain = vKey

            if vSubdomain is None:
                vButton = create_button(
                    f"{vDomain or 'Tous les thèmes'} ({vCount})",
                    DOMAIN_ICONS.get(vDomain, "graduation-cap"),
                    "tabButton",
                    COLORS["primary"] if vCount else COLORS["muted"],
                )
                vButton.setChecked(vDomain == self.domain)
                self.tabs_layout.addWidget(vButton)

            elif self.domain in (None, vDomain):
                vButton = create_button(
                    f"{vSubdomain} ({vCount})",
                    DOMAIN_ICONS.get(vSubdomain, "tag"),
                    "chipButton",
                    COLORS["primary"] if vCount else COLORS["muted"],
                )
                vButton.setChecked(vKey == (self.domain, self.subdomain))
                vButton.setProperty("empty", not vCount)
                self.chips_layout.addWidget(vButton)

            else:
                continue

            vButton.setCheckable(True)
            vButton.setChecked(
                vKey == (self.domain, self.subdomain)
                or (vSubdomain is None and vDomain == self.domain)
            )
            vButton.clicked.connect(
                lambda _=False, pKey=vKey: self.on_category_clicked(pKey)
            )
            self.category_buttons[vKey] = vButton

    def resizeEvent(self, pEvent):  # pylint: disable=invalid-name
        """Adapte le nombre de colonnes à la largeur, sans défilement horizontal."""
        super().resizeEvent(pEvent)

        vColumns = max(
            1, min(MAX_THEME_COLUMNS, (self.width() - 64) // THEME_CARD_WIDTH)
        )

        if vColumns != self.theme_columns:
            self.theme_columns = vColumns

            if self.themes:
                self.select_category(self.domain, self.subdomain)

    def on_category_clicked(self, pCategory):
        """Filtre sur la catégorie cliquée ; un second clic revient à l'ensemble."""
        vCategory = (
            (None, None)
            if pCategory == (self.domain, self.subdomain) and pCategory[1]
            else pCategory
        )

        self.select_category(*vCategory)

    def select_category(self, pDomain, pSubdomain=None):
        """Affiche les thèmes, guides et l'examen d'une catégorie, ou de toutes."""
        self.domain = pDomain
        self.subdomain = pSubdomain

        self.refresh_categories()
        self.refresh_exam_button()
        self.refresh_guides()
        self.show_themes()

    def select_domain(self, pDomain):
        """Limite l'affichage des thèmes à un domaine, ou les montre tous."""
        self.select_category(pDomain)

    def select_subdomain(self, pSubdomain):
        """Limite l'affichage aux thèmes d'un sous-domaine du domaine choisi."""
        self.select_category(self.domain, pSubdomain)

    def refresh_exam_button(self):
        """Propose de reprendre l'examen en cours, ou d'en commencer un."""
        vExam = load_exam(self.database_file)

        self.exam_button.setText(
            f"Reprendre l'examen ({vExam['index'] + 1} / {len(vExam['ids'])})"
            if vExam and not vExam["finished_at"]
            else f"Mode examen ({EXAM_QUESTION_COUNT} questions)"
        )
        self.filter_label.setText(
            " › ".join(vPart for vPart in (self.domain, self.subdomain) if vPart)
            or "Tous les thèmes"
        )

    def show_themes(self):
        """Affiche les thèmes du domaine choisi, rangés par sous-domaine."""
        clear_layout(self.themes_holder)

        vContainer = QWidget()
        vLayout = QVBoxLayout(vContainer)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(12)

        vGroups = group_themes(self.themes, self.domain, self.subdomain)

        if not vGroups:
            vLayout.addWidget(self.create_empty_category())

        for vDomain, vSections in vGroups:
            vLayout.addWidget(self.create_domain_header(vDomain, vSections))

            for vSubdomain, vThemes in vSections:
                vSubtitle = self.create_subdomain_badge(vSubdomain, len(vThemes))

                vGrid = QGridLayout()
                vGrid.setSpacing(16)

                for vColumn in range(self.theme_columns):
                    vGrid.setColumnStretch(vColumn, 1)

                for vIndex, vTheme in enumerate(vThemes):
                    vGrid.addWidget(
                        self.create_theme_card(vTheme, vSubdomain),
                        *divmod(vIndex, self.theme_columns),
                    )

                vLayout.addWidget(vSubtitle, 0, Qt.AlignmentFlag.AlignLeft)
                vLayout.addLayout(vGrid)

        self.themes_holder.addWidget(vContainer)

    def create_empty_category(self):
        """Crée la carte d'une rubrique sans question : ses thèmes du catalogue à préparer."""
        rCard, vLayout = create_card(
            "Aucune question dans cette rubrique",
            "Préparez un lot avec votre compte ChatGPT : la demande est copiée, "
            "collez ensuite la réponse dans « Ajouter des questions ».",
        )

        vThemes = [
            vTheme
            for vTheme in load_catalog()
            if self.domain in (None, vTheme["domain"])
            and self.subdomain in (None, vTheme["subdomain"])
        ]
        vGrid = QGridLayout()
        vGrid.setSpacing(8)
        vGrid.setColumnStretch(0, 1)

        for vRow, vTheme in enumerate(vThemes):
            vLabel = QLabel(vTheme["label"])
            vLabel.setWordWrap(True)

            vButton = create_button("Préparer", "bot", pIconColor=COLORS["primary"])
            vButton.setToolTip("Copie la demande de questions pour ce thème")
            vButton.clicked.connect(
                lambda _=False, pLabel=vTheme["label"]: (
                    self.import_panel.prepare_priority(pLabel)
                )
            )

            vGrid.addWidget(vLabel, vRow, 0)
            vGrid.addWidget(vButton, vRow, 1)

        vLayout.addLayout(vGrid)

        return rCard

    def create_subdomain_badge(self, pSubdomain, pCount):
        """Crée le badge d'un sous-domaine : icône, nom et nombre de thèmes."""
        rBadge = QFrame()
        rBadge.setObjectName("subdomainBadge")

        vText = QLabel(f"{pSubdomain} · {pCount}")
        vText.setObjectName("subdomainBadgeText")

        vLayout = QHBoxLayout(rBadge)
        vLayout.setContentsMargins(10, 3, 12, 3)
        vLayout.setSpacing(6)
        vLayout.addWidget(
            create_icon_label(
                DOMAIN_ICONS.get(pSubdomain, "tag"), COLORS["primary"], 14
            )
        )
        vLayout.addWidget(vText)

        return rBadge

    def create_domain_header(self, pDomain, pSections):
        """Crée l'en-tête d'un domaine : icône, nom et progression d'ensemble."""
        vThemes = [vTheme for _, vThemes in pSections for vTheme in vThemes]

        vTitle = QLabel(pDomain)
        vTitle.setObjectName("cardTitle")

        vSummary = QLabel(
            f"{len(vThemes)} thème(s) · "
            f"{sum(vTheme['correct'] for vTheme in vThemes)} / "
            f"{sum(vTheme['total'] for vTheme in vThemes)} questions acquises"
        )
        vSummary.setObjectName("cardSubtitle")

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(vSummary)

        rHeader = QWidget()
        vLayout = QHBoxLayout(rHeader)
        vLayout.setContentsMargins(0, 12, 0, 0)
        vLayout.setSpacing(12)
        vLayout.addWidget(
            create_icon_label(
                DOMAIN_ICONS.get(pDomain, "sparkles"), COLORS["primary"], 22
            )
        )
        vLayout.addLayout(vTexts, 1)

        return rHeader

    def create_theme_card(self, pTheme, pSubdomain=None):
        """Crée la carte d'un thème : icône, progression, intérêt et boutons."""
        rCard, vLayout = create_card()

        # Largeur fixée par la grille seule : les colonnes restent égales.
        rCard.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        vIcon = create_icon_label(
            DOMAIN_ICONS.get(pSubdomain, "graduation-cap"), COLORS["primary"], 20
        )
        vIcon.setFixedSize(40, 40)
        vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vIcon.setStyleSheet(
            f"background: {COLORS['primary_light']}; border-radius: 10px;"
        )

        vTitle = QLabel(pTheme["label"])
        vTitle.setObjectName("cardTitle")
        vTitle.setWordWrap(True)

        vCount = QLabel(
            f"{pTheme['total']} questions · {pTheme['correct']} acquise(s)"
            + (f" · {pTheme['to_review']} ratée(s)" if pTheme["to_review"] else "")
        )
        vCount.setObjectName("cardSubtitle")
        vCount.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(vCount)

        vTitleRow = QHBoxLayout()
        vTitleRow.setSpacing(12)
        vTitleRow.addWidget(vIcon, 0, Qt.AlignmentFlag.AlignTop)
        vTitleRow.addLayout(vTexts, 1)

        if pTheme["status"]:
            vStatusIcon, vTone, vText = THEME_STATUSES[pTheme["status"]]
            vStatus = create_icon_label(vStatusIcon, COLORS[vTone], 18)
            vStatus.setToolTip(vText)
            vTitleRow.addWidget(vStatus, 0, Qt.AlignmentFlag.AlignTop)

        vLayout.addLayout(vTitleRow)

        # Pastilles : intérêt pour les offres en bleu, révisions dues en orange.
        vPills = FlowLayout()
        vPills.addWidget(
            create_pill(f"Demandé dans {pTheme['offer_count']} offre(s)", "primary")
            if pTheme["offer_count"]
            else create_pill("Pas encore dans vos offres", "muted")
        )

        if pTheme["due"]:
            vPills.addWidget(
                create_pill(f"{pTheme['due']} à revoir aujourd'hui", "warning")
            )

        vLayout.addLayout(vPills)

        vProgress = QProgressBar()
        vProgress.setTextVisible(False)
        vProgress.setValue(pTheme["score"])

        vScore = QLabel(f"{pTheme['score']} %")
        vScore.setObjectName("cardSubtitle")

        vProgressRow = QHBoxLayout()
        vProgressRow.setSpacing(8)
        vProgressRow.addWidget(vProgress, 1)
        vProgressRow.addWidget(vScore)
        vLayout.addLayout(vProgressRow)

        vStart = create_button("Réviser", pObjectName="primaryButton")
        vStart.setToolTip(
            "Répétition espacée : questions à revoir aujourd'hui, puis nouvelles"
        )
        vStart.clicked.connect(lambda: self.start(pTheme["key"], DEFAULT_MODE))

        vButtons = QHBoxLayout()
        vButtons.addWidget(vStart)

        if pTheme["to_review"]:
            vReview = create_button("Erreurs", "history", pIconColor=COLORS["primary"])
            vReview.setToolTip("Revoir les questions ratées")
            vReview.clicked.connect(lambda: self.start(pTheme["key"], "review"))
            vButtons.addWidget(vReview)

        if pTheme["guide"]:
            vGuide = create_button("Guide", "file-text", pIconColor=COLORS["primary"])
            vGuide.clicked.connect(lambda: self.show_guide(pTheme["guide"]))
            vButtons.addWidget(vGuide)

        vButtons.addStretch()
        vLayout.addLayout(vButtons)

        return rCard

    def get_visual_width(self):
        """Retourne la largeur disponible pour un schéma dans la carte de question."""
        rWidth = max(MIN_VISUAL_WIDTH, self.width() - VISUAL_MARGINS)

        return rWidth

    def load_visual(self, pWidget, pVisual):
        """Affiche un schéma dans pWidget, ou le masque s'il n'y en a pas."""
        vContent = (
            get_quiz_asset(self.database_file, pVisual["asset"]) if pVisual else None
        )

        if vContent:
            show_svg(
                pWidget,
                vContent,
                pVisual["alt"],
                VISUAL_HEIGHT,
                pMaxWidth=self.get_visual_width(),
            )

        pWidget.setVisible(bool(vContent))

    def show_extras(self, pQuestion, pResponse=None):
        """Affiche le schéma et les références d'une question, s'il y en a.

        Pour un schéma à construire, pResponse est redessiné à côté de l'attendu.
        """
        vVisual = pQuestion.get("visual")

        # Un schéma déjà montré avec l'énoncé n'est pas répété sous la correction.
        self.load_visual(
            self.visual_widget,
            vVisual if vVisual and vVisual.get("show") != "question" else None,
        )

        if pQuestion.get("type") == "construction" and pResponse:
            show_svg(
                self.visual_widget,
                render_correction(pQuestion, pResponse),
                "Votre schéma et schéma attendu",
                EXPECTED_SCHEMA_HEIGHT,
                pShrinkOnly=True,
                pMaxWidth=self.get_visual_width(),
            )
            self.visual_widget.show()

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

        vGuides = filter_guides(
            get_quiz_guides(self.database_file),
            self.themes,
            self.domain,
            self.subdomain,
        )

        for vIndex, vGuide in enumerate(vGuides):
            vButton = create_button(
                vGuide["title"], "file-text", pIconColor=COLORS["primary"]
            )
            vButton.clicked.connect(
                lambda _=False, pName=vGuide["name"]: self.show_guide(pName)
            )
            self.guides_layout.addWidget(vButton, *divmod(vIndex, self.theme_columns))

        self.guides_card.setVisible(bool(vGuides))

    def start(self, pThemeKey, pMode):
        """Affiche une nouvelle question du thème, ou signale qu'il n'y en a plus."""
        vQuiz = load_active_quiz(self.database_file)

        self.theme_key = pThemeKey
        self.mode = pMode
        vSchedule = get_review_schedule(self.database_file)
        vQuestion = pick_question(
            vQuiz,
            pThemeKey,
            pMode,
            get_last_answers(self.database_file),
            pSchedule=vSchedule,
        )

        self.display_question(
            vQuestion,
            (
                f"{vQuiz[pThemeKey]['label']} · {vQuestion['level']} · "
                f"{vQuestion['type_label']} · {QUIZ_MODES[pMode]}"
                if vQuestion
                else vQuiz[pThemeKey]["label"]
            ),
            describe_no_question(pMode, get_next_review(vQuiz, pThemeKey, vSchedule)),
        )

    def display_question(self, pQuestion, pMeta, pEmptyText):
        """Affiche une question et ses choix, ou pEmptyText s'il n'y en a pas."""
        self.question = pQuestion
        self.question_card.show()

        # La question s'affiche en haut de la page : on y remonte.
        self.findChild(QScrollArea).verticalScrollBar().setValue(0)
        self.verdict_label.clear()
        self.explanation_label.clear()
        self.visual_widget.hide()
        self.question_visual_widget.hide()
        self.references_label.hide()
        self.next_button.hide()
        self.next_button.setText("Question suivante")
        self.stop_exam_button.setVisible(self.mode == EXAM_MODE)
        self.meta_label.setText(pMeta)

        clear_layout(self.choices_layout)
        self.answer_widgets = []
        self.zone_point = None
        self.question_visual_widget.set_clickable(False)

        for vButton in self.choices_group.buttons():
            self.choices_group.removeButton(vButton)

        if pQuestion is None:
            self.question_label.setText(pEmptyText)
            self.code_edit.hide()
            self.validate_button.hide()
            self.flag_button.hide()
            return

        self.question_label.setText(pQuestion["question"])
        self.code_edit.setPlainText(pQuestion.get("code", ""))
        self.code_edit.setVisible(bool(pQuestion.get("code")))
        self.validate_button.show()
        self.flag_button.setVisible(self.mode != EXAM_MODE)

        vVisual = pQuestion.get("visual")

        if vVisual and vVisual.get("show") == "question":
            self.load_visual(self.question_visual_widget, vVisual)
            self.question_visual_widget.set_clickable(pQuestion["type"] == "zone")

        self.answer_widgets = add_answer_widgets(
            pQuestion, self.choices_layout, self.choices_group, self.validate
        )

    def choose_point(self, pX, pY):
        """Retient le point cliqué sur le schéma d'une question « zone »."""
        self.zone_point = (pX, pY)

    def start_exam(self):
        """Reprend l'examen en cours, ou en commence un sur le domaine choisi."""
        self.begin_exam(
            lambda pQuiz: start_exam(
                self.database_file,
                pQuiz,
                self.domain,
                datetime.now(),
                pSubdomain=self.subdomain,
            )
        )

    def start_offer_exam(self, pOffer):
        """Reprend l'examen en cours, ou commence l'examen blanc d'une offre."""
        self.begin_exam(
            lambda pQuiz: start_offer_exam(
                self.database_file, pQuiz, pOffer, datetime.now()
            )
        )

    def begin_exam(self, pStart):
        """Reprend l'examen en cours ; sinon en commence un avec la fonction donnée."""
        vExam = load_exam(self.database_file)

        if not vExam or vExam["finished_at"]:
            try:
                pStart(load_active_quiz(self.database_file))

            except ValueError as vException:
                show_message(self.message_label, str(vException), "warning")
                self.message_label.show()
                return

        self.mode = EXAM_MODE
        self.show_exam_question()

    def show_exam_question(self):
        """Affiche la question en cours de l'examen, ou son résultat."""
        vQuiz = load_active_quiz(self.database_file)
        vExam = load_exam(self.database_file)

        self.current_exam = vExam

        if vExam and vExam["finished_at"]:
            vSummary = describe_exam_summary(summarize_exam(vQuiz, vExam))

            if vExam.get("offer"):
                vSummary += " " + describe_exam_results(
                    load_exam_results(self.database_file, vExam["offer"])
                )

            self.display_question(None, "Examen terminé", vSummary)
            self.stop_exam_button.setText("Fermer l'examen")
            self.update_exam_timer()
            return

        self.exam_timer.start()

        vQuestion = get_exam_question(vQuiz, vExam)

        self.stop_exam_button.setText("Abandonner l'examen")
        self.update_exam_timer()
        self.display_question(
            vQuestion,
            (
                f"{vExam.get('title') or 'Examen'} · question "
                f"{vQuestion['position']} / {vQuestion['count']} · "
                f"{vQuestion['theme_label']} · {vQuestion['level']}"
                if vQuestion
                else "Examen"
            ),
            "Cette question n'existe plus : passez à la suivante.",
        )

    def update_exam_timer(self):
        """Affiche le temps restant de l'examen en cours, ou masque le minuteur."""
        vExam = self.current_exam

        if self.mode != EXAM_MODE or not vExam or vExam["finished_at"]:
            self.exam_timer.stop()
            self.timer_label.hide()
            return

        vRemaining = get_remaining_seconds(vExam, datetime.now())

        if vRemaining >= TIMER_WARNING_SECONDS:
            vTone = "success"
        elif vRemaining >= 0:
            vTone = "warning"
        else:
            vTone = "danger"

        show_message(self.timer_label, format_countdown(vRemaining), vTone)
        self.timer_label.show()

    def close_exam(self):
        """Abandonne ou referme l'examen, puis revient à la liste des thèmes."""
        stop_exam(self.database_file)

        self.current_exam = None
        self.update_exam_timer()

        self.mode = None
        self.question_card.hide()
        self.refresh()

    def go_next(self):
        """Passe à la question suivante du thème ou de l'examen."""
        if self.mode == EXAM_MODE:
            self.show_exam_question()
        else:
            self.start(self.theme_key, self.mode)

    def validate(self):
        """Corrige la réponse choisie et affiche l'explication."""
        vResponse = read_response(
            self.question, self.answer_widgets, self.choices_group, self.zone_point
        )

        if vResponse is None:
            show_message(self.verdict_label, "Complétez votre réponse.", "warning")
            return

        try:
            if self.mode == EXAM_MODE:
                vResult, vExam = answer_exam(
                    self.database_file,
                    load_active_quiz(self.database_file),
                    vResponse,
                    datetime.now(),
                )

                if vExam["finished_at"]:
                    self.next_button.setText("Voir le résultat")
            else:
                vResult = answer_question(
                    self.database_file,
                    load_active_quiz(self.database_file),
                    self.question["id"],
                    vResponse,
                    datetime.now(),
                )

        except ValueError as vException:
            show_message(self.verdict_label, str(vException), "warning")
            return

        # Question supprimée depuis le début de l'examen : elle est passée.
        if vResult is None:
            self.go_next()
            return

        vTone = "success" if vResult["correct"] else "danger"

        self.verdict_label.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")
        self.verdict_label.setText(
            "Bonne réponse."
            if vResult["correct"]
            else f"Réponse incorrecte. Votre réponse : {vResult['chosen']}. "
            f"Réponse attendue : {vResult['answer']}"
        )
        self.explanation_label.setText(vResult["explanation"])
        self.show_extras(vResult["question"], vResult.get("response"))

        for vWidget in self.answer_widgets:
            vWidget.setEnabled(False)

        self.question_visual_widget.set_clickable(False, pKeepPoint=True)

        self.validate_button.hide()
        self.next_button.show()

        self.refresh()
