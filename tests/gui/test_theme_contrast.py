"""Tests des contrastes de la palette du bureau, dans les deux thèmes

Même règle que l'audit axe-core du web (WCAG 2 AA) : 4,5 pour un texte courant,
3 pour un grand titre.
"""

import pytest

from gui.theme import THEME_ACCENTS, THEMES

TEXT_RATIO = 4.5
LARGE_TEXT_RATIO = 3.0

# Texte et fond sur lesquels il s'affiche, avec le contraste minimal attendu
PAIRS = [
    ("text", "surface", TEXT_RATIO),
    ("muted", "surface", TEXT_RATIO),
    ("primary", "surface", TEXT_RATIO),
    ("success", "surface", TEXT_RATIO),
    ("warning", "surface", TEXT_RATIO),
    ("danger", "surface", TEXT_RATIO),
    ("success", "success_light", TEXT_RATIO),
    ("warning", "warning_light", TEXT_RATIO),
    ("danger", "danger_light", TEXT_RATIO),
    ("on_primary", "primary", TEXT_RATIO),
    ("on_primary", "primary_dark", TEXT_RATIO),
    ("banner_text", "banner_start", TEXT_RATIO),
    ("banner_text", "banner_end", TEXT_RATIO),
    ("banner_title", "banner_start", LARGE_TEXT_RATIO),
    ("banner_title", "banner_end", LARGE_TEXT_RATIO),
]


def get_luminance(pColor):
    """Retourne la luminance relative d'une couleur #RRGGBB (WCAG)."""

    vChannels = [int(pColor[vIndex : vIndex + 2], 16) / 255 for vIndex in (1, 3, 5)]
    vLinear = [
        vValue / 12.92 if vValue <= 0.03928 else ((vValue + 0.055) / 1.055) ** 2.4
        for vValue in vChannels
    ]

    rLuminance = 0.2126 * vLinear[0] + 0.7152 * vLinear[1] + 0.0722 * vLinear[2]

    return rLuminance


def get_contrast(pFirst, pSecond):
    """Retourne le rapport de contraste entre deux couleurs, de 1 à 21."""

    vLight, vDark = sorted(map(get_luminance, (pFirst, pSecond)), reverse=True)

    rContrast = (vLight + 0.05) / (vDark + 0.05)

    return rContrast


@pytest.mark.parametrize("pTheme", ["light", "dark"])
def test_palette_text_is_readable(pTheme):
    """Vérifie chaque couple texte et fond de la palette, accents compris."""

    vColors = THEMES[pTheme]
    vFaulty = [
        f"{vText} sur {vBackground} : {get_contrast(vColors[vText], vColors[vBackground]):.2f}"
        for vText, vBackground, vMinimum in PAIRS
        if get_contrast(vColors[vText], vColors[vBackground]) < vMinimum
    ]
    vFaulty += [
        f"accent {vName} : {get_contrast(vColor, vBackground):.2f}"
        for vName, (vColor, vBackground) in THEME_ACCENTS[pTheme].items()
        if get_contrast(vColor, vBackground) < TEXT_RATIO
    ]

    assert vFaulty == []


def test_contrast_matches_known_values():
    """Vérifie le calcul sur deux valeurs connues : noir et blanc, blanc et blanc."""

    assert round(get_contrast("#000000", "#FFFFFF"), 1) == 21.0
    assert get_contrast("#FFFFFF", "#FFFFFF") == 1.0
