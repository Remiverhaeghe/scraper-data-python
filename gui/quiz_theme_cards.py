"""Cartes de la page Révision : thèmes, en-têtes de domaine et rubriques vides"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    FlowLayout,
    create_button,
    create_card,
    create_icon_label,
    create_pill,
)
from job.quiz import DEFAULT_MODE, THEME_STATUSES
from job.quiz_domains import DOMAIN_ICONS
from job.quiz_generation import load_catalog


def create_empty_category(pDomain, pSubdomain, pOnPrepare):
    """Crée la carte d'une rubrique sans question : ses thèmes du catalogue à préparer."""
    rCard, vLayout = create_card(
        "Aucune question dans cette rubrique",
        "Préparez un lot avec votre compte ChatGPT : la demande est copiée, "
        "collez ensuite la réponse dans « Ajouter des questions ».",
    )

    vThemes = [
        vTheme
        for vTheme in load_catalog()
        if pDomain in (None, vTheme["domain"])
        and pSubdomain in (None, vTheme["subdomain"])
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
            lambda _=False, pLabel=vTheme["label"]: (pOnPrepare(pLabel))
        )

        vGrid.addWidget(vLabel, vRow, 0)
        vGrid.addWidget(vButton, vRow, 1)

    vLayout.addLayout(vGrid)

    return rCard


def create_subdomain_badge(pSubdomain, pCount):
    """Crée le badge d'un sous-domaine : icône, nom et nombre de thèmes."""
    rBadge = QFrame()
    rBadge.setObjectName("subdomainBadge")

    vText = QLabel(f"{pSubdomain} · {pCount}")
    vText.setObjectName("subdomainBadgeText")

    vLayout = QHBoxLayout(rBadge)
    vLayout.setContentsMargins(10, 3, 12, 3)
    vLayout.setSpacing(6)
    vLayout.addWidget(
        create_icon_label(DOMAIN_ICONS.get(pSubdomain, "tag"), COLORS["primary"], 14)
    )
    vLayout.addWidget(vText)

    return rBadge


def create_domain_header(pDomain, pSections):
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
        create_icon_label(DOMAIN_ICONS.get(pDomain, "sparkles"), COLORS["primary"], 22)
    )
    vLayout.addLayout(vTexts, 1)

    return rHeader


def create_theme_card(pTheme, pSubdomain, pOnStart, pOnGuide):
    """Crée la carte d'un thème : icône, progression, intérêt et boutons."""
    rCard, vLayout = create_card()

    # Largeur fixée par la grille seule : les colonnes restent égales.
    rCard.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    vIcon = create_icon_label(
        DOMAIN_ICONS.get(pSubdomain, "graduation-cap"), COLORS["primary"], 20
    )
    vIcon.setFixedSize(40, 40)
    vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    vIcon.setStyleSheet(f"background: {COLORS['primary_light']}; border-radius: 10px;")

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
    vStart.clicked.connect(lambda: pOnStart(pTheme["key"], DEFAULT_MODE))

    vButtons = QHBoxLayout()
    vButtons.addWidget(vStart)

    if pTheme["to_review"]:
        vReview = create_button("Erreurs", "history", pIconColor=COLORS["primary"])
        vReview.setToolTip("Revoir les questions ratées")
        vReview.clicked.connect(lambda: pOnStart(pTheme["key"], "review"))
        vButtons.addWidget(vReview)

    if pTheme["guide"]:
        vGuide = create_button("Guide", "file-text", pIconColor=COLORS["primary"])
        vGuide.clicked.connect(lambda: pOnGuide(pTheme["guide"]))
        vButtons.addWidget(vGuide)

    vButtons.addStretch()
    vLayout.addLayout(vButtons)

    return rCard
