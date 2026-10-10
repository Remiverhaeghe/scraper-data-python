"""Tests du thème et des icônes"""

from gui.icons import ICONS_DIRECTORY, get_icon
from gui.theme import COLORS, build_stylesheet


def test_stylesheet_has_no_unresolved_variable():
    """Vérifie que toutes les variables de la feuille de style sont remplacées."""

    vStylesheet = build_stylesheet()

    assert "$" not in vStylesheet
    assert COLORS["primary"] in vStylesheet


def test_every_icon_can_be_rendered(qt_application):
    """Vérifie que chaque icône embarquée se dessine sans erreur."""

    for vFile in ICONS_DIRECTORY.glob("*.svg"):
        vIcon = get_icon(vFile.stem, COLORS["primary"], 20, COLORS["surface"])

        assert not vIcon.pixmap(20, 20).isNull(), vFile.name
