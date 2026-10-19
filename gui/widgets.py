"""Composants graphiques partagés entre les pages"""

from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.icons import get_icon
from gui.theme import ACCENTS, COLORS

# Même retrait que le padding horizontal des champs dans theme.qss
SPIN_BOX_TEXT_MARGIN = 10


def create_page_header(pLayout, pTitle, pSubtitle, pActions=(), pIcon=None):
    """Ajoute le titre, son icône, le sous-titre et les boutons d'action d'une page."""

    vTitle = QLabel(pTitle)
    vTitle.setObjectName("pageTitle")

    vTitleRow = QHBoxLayout()
    vTitleRow.setSpacing(12)

    if pIcon is not None:
        vIcon = create_icon_label(pIcon, COLORS["primary"], 22)
        vIcon.setObjectName("pageIcon")
        vIcon.setFixedSize(40, 40)
        vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vTitleRow.addWidget(vIcon)

    vTitleRow.addWidget(vTitle)
    vTitleRow.addStretch()

    vSubtitle = QLabel(pSubtitle)
    vSubtitle.setObjectName("pageSubtitle")
    vSubtitle.setWordWrap(True)

    vTexts = QVBoxLayout()
    vTexts.setSpacing(4)
    vTexts.addLayout(vTitleRow)
    vTexts.addWidget(vSubtitle)

    vHeader = QHBoxLayout()
    vHeader.addLayout(vTexts, 1)

    for vAction in pActions:
        vHeader.addWidget(vAction, 0, Qt.AlignmentFlag.AlignVCenter)

    pLayout.addLayout(vHeader)
    pLayout.addSpacing(18)


def create_button(pText, pIcon=None, pObjectName=None, pIconColor=None):
    """Crée un bouton, éventuellement avec une icône et un style nommé."""

    rButton = QPushButton(pText)
    rButton.setCursor(Qt.CursorShape.PointingHandCursor)

    if pObjectName is not None:
        rButton.setObjectName(pObjectName)

    if pIcon is not None:
        rButton.setIcon(get_icon(pIcon, pIconColor or COLORS["text"], 18))
        rButton.setIconSize(QSize(18, 18))

    return rButton


class CardHeader(QWidget):
    """En-tête cliquable d'une carte : icône, titre et chevron pour la replier."""

    clicked = Signal()

    def __init__(self, pTitle, pIcon=None, pActions=()):
        """Construit l'en-tête ; le titre reste un QLabel « cardTitle » modifiable.

        pActions place des éléments entre le titre et le chevron : un clic sur
        un bouton déclenche son action, pas le repli de la carte.
        """
        super().__init__()

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.title_label = QLabel(pTitle)
        self.title_label.setObjectName("cardTitle")

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("collapsibleToggle")
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.clicked.connect(self.clicked.emit)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(8)

        if pIcon:
            vLayout.addWidget(create_icon_label(pIcon, COLORS["primary"], 20))

        vLayout.addWidget(self.title_label)
        vLayout.addStretch(1)

        for vAction in pActions:
            vLayout.addWidget(vAction)

        vLayout.addWidget(self.toggle_button)

    def set_open(self, pOpen):
        """Oriente le chevron selon que la carte est ouverte ou repliée."""
        self.toggle_button.setIcon(
            get_icon("chevron-up" if pOpen else "chevron-down", COLORS["muted"], 18)
        )
        self.toggle_button.setToolTip("Réduire" if pOpen else "Afficher")

    def mouseReleaseEvent(self, pEvent):  # pylint: disable=invalid-name
        """Replie ou ouvre la carte d'un clic sur son en-tête."""
        if pEvent.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

        super().mouseReleaseEvent(pEvent)


def create_card(pTitle=None, pSubtitle=None, pIcon=None, pKey=None, pActions=()):
    """Crée une carte blanche et retourne la carte et le layout de son contenu.

    Une carte titrée se replie d'un clic sur son en-tête ; l'état est mémorisé
    d'une ouverture à l'autre (QSettings), sous pKey ou à défaut sous le titre.
    """

    vCard = QFrame()
    vCard.setObjectName("card")

    vLayout = QVBoxLayout(vCard)
    vLayout.setContentsMargins(20, 18, 20, 18)
    vLayout.setSpacing(10)

    if pTitle is None:
        if pSubtitle is not None:
            vLayout.addWidget(create_subtitle(pSubtitle))

        rCard = (vCard, vLayout)

        return rCard

    vHeader = CardHeader(pTitle, pIcon, pActions)
    vLayout.addWidget(vHeader)

    if pSubtitle is not None:
        vLayout.addWidget(create_subtitle(pSubtitle))

    vContent = QWidget()
    vContentLayout = QVBoxLayout(vContent)
    vContentLayout.setContentsMargins(0, 0, 0, 0)
    vContentLayout.setSpacing(10)
    vLayout.addWidget(vContent, 1)

    vSettingKey = f"collapsed/{pKey or pTitle}"

    def set_open(pOpen):
        """Affiche ou replie le contenu de la carte."""
        vContent.setHidden(not pOpen)
        vHeader.set_open(pOpen)

    def toggle():
        """Inverse l'état du contenu et le mémorise."""
        set_open(vContent.isHidden())
        QSettings().setValue(vSettingKey, vContent.isHidden())

    vHeader.clicked.connect(toggle)
    set_open(not QSettings().value(vSettingKey, False, type=bool))

    rCard = (vCard, vContentLayout)

    return rCard


def create_subtitle(pText):
    """Crée le sous-titre d'une carte, qui passe à la ligne s'il est long."""

    rSubtitle = QLabel(pText)
    rSubtitle.setObjectName("cardSubtitle")
    # Retour à la ligne : un long sous-titre ne force pas la largeur de la carte.
    rSubtitle.setWordWrap(True)

    return rSubtitle


def add_tile_group(pLayout, pRow, pTitle, pIcon, pTiles, pColumns):
    """Ajoute à une grille un titre de groupe et ses tuiles ; retourne la ligne suivante."""

    vHeader = QWidget()
    vHeaderLayout = QHBoxLayout(vHeader)
    vHeaderLayout.setContentsMargins(0, 0, 0, 0)
    vHeaderLayout.setSpacing(8)
    vHeaderLayout.addWidget(create_icon_label(pIcon, COLORS["primary"], 18))

    vTitle = QLabel(pTitle)
    vTitle.setObjectName("tileGroup")
    vHeaderLayout.addWidget(vTitle, 1)

    pLayout.addWidget(vHeader, pRow, 0, 1, pColumns)

    for vIndex, vTile in enumerate(pTiles):
        pLayout.addWidget(vTile, pRow + 1 + vIndex // pColumns, vIndex % pColumns)

    rRow = pRow + 1 + (len(pTiles) + pColumns - 1) // pColumns

    return rRow


def create_pill(pText, pTone):
    """Crée une pastille de texte colorée : primary, warning, success ou muted."""

    rPill = QLabel(pText)
    rPill.setObjectName("pill")
    rPill.setProperty("tone", pTone)

    return rPill


def create_icon_label(pIcon, pColor, pSize=20):
    """Crée un libellé affichant uniquement une icône."""

    rLabel = QLabel()
    rLabel.setPixmap(get_icon(pIcon, pColor, pSize).pixmap(pSize, pSize))

    return rLabel


def create_scroll_content(pPage):
    """Place une zone défilante dans la page et retourne le contenu à remplir."""

    rContent = QWidget()

    # Sans possibilité de rétrécir, le contenu garde sa taille idéale : la page
    # défile sur un petit écran au lieu d'écraser les cartes et leurs textes.
    rContent.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    vScrollArea = QScrollArea()
    vScrollArea.setWidgetResizable(True)
    vScrollArea.setWidget(rContent)

    vLayout = QVBoxLayout(pPage)
    vLayout.setContentsMargins(0, 0, 0, 0)
    vLayout.addWidget(vScrollArea)

    return rContent


def clear_layout(pLayout):
    """Retire et détruit les widgets d'une mise en page avant de la remplir à nouveau."""

    while pLayout.count():
        vWidget = pLayout.takeAt(0).widget()

        # Masqué tout de suite : la destruction n'a lieu qu'au tour suivant de la
        # boucle d'événements, et l'ancien contenu resterait affiché d'ici là.
        if vWidget is not None:
            vWidget.hide()
            vWidget.deleteLater()


def align_spin_box(pSpinBox):
    """Décale le texte d'un champ numérique comme celui des autres champs."""

    # La marge gauche de la feuille de style n'atteint pas le champ interne.
    pSpinBox.lineEdit().setTextMargins(SPIN_BOX_TEXT_MARGIN, 0, 0, 0)

    return pSpinBox


class StatisticCard(QFrame):
    """Affiche une valeur chiffrée sur fond coloré, avec son icône et son libellé."""

    clicked = Signal()

    def __init__(self, pLabel, pIcon, pAccent, pClickable=False):
        """Construit la carte avec une valeur vide."""
        super().__init__()

        if pClickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        vColor, vBackground = ACCENTS[pAccent]

        self.setObjectName("statisticCard")
        self.setStyleSheet(
            f"QFrame#statisticCard {{ background: {vBackground}; border-radius: 12px; }}"
            f"QLabel#statisticValue {{ color: {vColor}; }}"
        )

        vIcon = create_icon_label(pIcon, vColor, 22)
        vIcon.setFixedSize(44, 44)
        vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vIcon.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 10px;")

        self.value_label = QLabel("-")
        self.value_label.setObjectName("statisticValue")

        self.label = QLabel(pLabel)
        self.label.setObjectName("statisticLabel")
        self.label.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(0)
        vTexts.addWidget(self.value_label)
        vTexts.addWidget(self.label)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(18, 16, 18, 16)
        vLayout.setSpacing(14)
        vLayout.addWidget(vIcon)
        vLayout.addLayout(vTexts, 1)

    def set_value(self, pValue):
        """Met à jour la valeur affichée."""
        self.value_label.setText(str(pValue))

    def set_label(self, pLabel):
        """Met à jour le libellé, lorsqu'il dépend d'un réglage."""
        self.label.setText(pLabel)

    def mouseReleaseEvent(self, pEvent):
        """Émet clicked lorsque la carte est cliquée."""
        super().mouseReleaseEvent(pEvent)

        # Un bouton relâché hors de la carte annule le clic, comme pour un vrai bouton.
        if self.rect().contains(pEvent.position().toPoint()):
            self.clicked.emit()


def show_message(pLabel, pText, pTone="success"):
    """Affiche un message coloré selon sa nature : success, warning ou danger.

    Vert pour une réussite, orange pour une saisie à corriger, rouge pour une
    erreur ; None garde le style de l'étiquette, pour une simple information.
    Un texte vide efface le message.
    """

    pLabel.setText(pText)
    pLabel.setStyleSheet(
        f"color: {COLORS[pTone]}; font-weight: 600;" if pText and pTone else ""
    )


class TileButton(QFrame):
    """Tuile cliquable d'une liste : icône colorée, titre, détail et badge à droite.

    Une tuile réussie passe en vert ; la tuile sélectionnée est encadrée.
    """

    clicked = Signal()

    def __init__(self, pTitle, pDetail, pIcon, pAccent="blue", pBadge=""):
        """Construit la tuile, non sélectionnée et non réussie."""
        super().__init__()

        self.setObjectName("tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(pTitle)
        self.checked = False
        self.done = False
        self.icon_name = pIcon
        self.accent = pAccent

        self.icon_label = QLabel()
        self.icon_label.setObjectName("tileIcon")
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(pTitle)
        self.title_label.setObjectName("tileTitle")
        self.title_label.setWordWrap(True)

        self.detail_label = QLabel(pDetail)
        self.detail_label.setObjectName("tileDetail")
        self.detail_label.setWordWrap(True)

        self.badge_label = QLabel(pBadge)
        self.badge_label.setObjectName("tileBadge")

        vText = QVBoxLayout()
        vText.setSpacing(2)
        vText.addWidget(self.title_label)
        vText.addWidget(self.detail_label)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(12, 10, 12, 10)
        vLayout.setSpacing(12)
        vLayout.addWidget(self.icon_label)
        vLayout.addLayout(vText, 1)
        vLayout.addWidget(self.badge_label, 0, Qt.AlignmentFlag.AlignTop)

        self.update_style()

    def setChecked(self, pChecked):  # pylint: disable=invalid-name
        """Sélectionne ou désélectionne la tuile, comme un bouton à cocher."""
        self.checked = pChecked
        self.update_style()

    def isChecked(self):  # pylint: disable=invalid-name
        """Indique si la tuile est sélectionnée."""
        rChecked = self.checked

        return rChecked

    def set_done(self, pDone):
        """Marque la tuile comme réussie : fond et icône verts."""
        self.done = pDone
        self.update_style()

    def update_style(self):
        """Applique les couleurs selon l'état : réussie, sélectionnée ou neutre."""
        vColor, vBackground = (
            (COLORS["success"], COLORS["success_light"])
            if self.done
            else ACCENTS[self.accent]
        )

        self.icon_label.setPixmap(
            get_icon(
                "circle-check" if self.done else self.icon_name, vColor, 20
            ).pixmap(20, 20)
        )
        self.icon_label.setStyleSheet(
            f"background: {vBackground}; border-radius: 10px;"
        )
        self.setProperty("done", self.done)
        self.setProperty("checked", self.checked)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, pEvent):  # pylint: disable=invalid-name
        """Émet clicked au relâchement du bouton gauche sur la tuile."""
        if pEvent.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            pEvent.position().toPoint()
        ):
            self.clicked.emit()

        super().mouseReleaseEvent(pEvent)

    def keyPressEvent(self, pEvent):  # pylint: disable=invalid-name
        """Ouvre la tuile au clavier, avec Entrée ou Espace."""
        if pEvent.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(pEvent)


class FlowLayout(QLayout):
    """Range les éléments en ligne et passe à la ligne suivante faute de place.

    Repris de l'exemple « Flow Layout » de la documentation Qt : pastilles et
    filtres s'adaptent à la largeur au lieu d'élargir la page.
    """

    def __init__(self, pSpacing=6):
        """Crée une mise en page vide, avec l'espacement donné entre éléments."""
        super().__init__()

        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(pSpacing)

    def addItem(self, pItem):  # pylint: disable=invalid-name
        """Ajoute un élément à la fin."""
        self.items.append(pItem)

    def count(self):
        """Retourne le nombre d'éléments."""
        rCount = len(self.items)

        return rCount

    def itemAt(self, pIndex):  # pylint: disable=invalid-name
        """Retourne l'élément à cette position, ou None."""
        rItem = self.items[pIndex] if 0 <= pIndex < len(self.items) else None

        return rItem

    def takeAt(self, pIndex):  # pylint: disable=invalid-name
        """Retire et retourne l'élément à cette position, ou None."""
        rItem = self.items.pop(pIndex) if 0 <= pIndex < len(self.items) else None

        return rItem

    def expandingDirections(self):  # pylint: disable=invalid-name
        """Ne réclame aucune place supplémentaire."""
        rDirections = Qt.Orientation(0)

        return rDirections

    def hasHeightForWidth(self):  # pylint: disable=invalid-name
        """Indique que la hauteur dépend de la largeur disponible."""
        return True

    def heightForWidth(self, pWidth):  # pylint: disable=invalid-name
        """Retourne la hauteur nécessaire pour cette largeur."""
        rHeight = self.arrange(QRect(0, 0, pWidth, 0), pApply=False)

        return rHeight

    def setGeometry(self, pRect):  # pylint: disable=invalid-name
        """Place les éléments dans le rectangle donné."""
        super().setGeometry(pRect)
        self.arrange(pRect, pApply=True)

    def sizeHint(self):  # pylint: disable=invalid-name
        """Retourne la taille souhaitée : celle du plus grand élément."""
        rSize = self.minimumSize()

        return rSize

    def minimumSize(self):  # pylint: disable=invalid-name
        """Retourne la taille minimale : un seul élément par ligne suffit."""
        vSize = QSize()

        for vItem in self.items:
            vSize = vSize.expandedTo(vItem.minimumSize())

        vMargins = self.contentsMargins()
        rSize = vSize + QSize(
            vMargins.left() + vMargins.right(), vMargins.top() + vMargins.bottom()
        )

        return rSize

    def arrange(self, pRect, pApply):
        """Calcule la position des éléments ligne par ligne et retourne la hauteur."""
        vMargins = self.contentsMargins()
        vArea = pRect.adjusted(
            vMargins.left(), vMargins.top(), -vMargins.right(), -vMargins.bottom()
        )
        vX, vY = vArea.x(), vArea.y()
        vLineHeight = 0

        for vItem in self.items:
            vSize = vItem.sizeHint()
            vNextX = vX + vSize.width() + self.spacing()

            if vNextX - self.spacing() > vArea.right() + 1 and vLineHeight:
                vX = vArea.x()
                vY += vLineHeight + self.spacing()
                vNextX = vX + vSize.width() + self.spacing()
                vLineHeight = 0

            if pApply:
                vItem.setGeometry(QRect(QPoint(vX, vY), vSize))

            vX = vNextX
            vLineHeight = max(vLineHeight, vSize.height())

        rHeight = vY + vLineHeight - pRect.y() + vMargins.bottom()

        return rHeight
