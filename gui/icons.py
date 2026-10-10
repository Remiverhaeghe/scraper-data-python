"""Chargement des icônes SVG dans la couleur souhaitée"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import ASSETS_DIRECTORY

ICONS_DIRECTORY = ASSETS_DIRECTORY / "icons"

# Rendu en double résolution pour rester net sur les écrans haute densité
PIXEL_RATIO = 2


@lru_cache
def render_icon(pName, pColor, pSize):
    """Dessine une icône Lucide, dont le trait suit currentColor, dans une couleur."""

    vSvg = (ICONS_DIRECTORY / f"{pName}.svg").read_text(encoding="utf-8")
    vRenderer = QSvgRenderer(QByteArray(vSvg.replace("currentColor", pColor).encode()))

    rPixmap = QPixmap(pSize * PIXEL_RATIO, pSize * PIXEL_RATIO)
    rPixmap.fill(Qt.GlobalColor.transparent)

    vPainter = QPainter(rPixmap)
    vRenderer.render(vPainter)
    vPainter.end()

    rPixmap.setDevicePixelRatio(PIXEL_RATIO)

    return rPixmap


def get_icon(pName, pColor, pSize=20, pSelectedColor=None, pCheckedColor=None):
    """Retourne une icône, avec une couleur propre à l'état sélectionné ou coché.

    Un élément de liste sélectionné utilise le mode Selected ; un bouton coché
    utilise l'état On.
    """

    rIcon = QIcon(render_icon(pName, pColor, pSize))

    if pSelectedColor is not None:
        rIcon.addPixmap(render_icon(pName, pSelectedColor, pSize), QIcon.Mode.Selected)

    if pCheckedColor is not None:
        rIcon.addPixmap(
            render_icon(pName, pCheckedColor, pSize),
            QIcon.Mode.Normal,
            QIcon.State.On,
        )

    return rIcon


def stylesheet_path(pName):
    """Retourne le chemin d'une icône utilisable dans une feuille de style Qt."""

    rPath = (ICONS_DIRECTORY / f"{pName}.svg").as_posix()

    return rPath
