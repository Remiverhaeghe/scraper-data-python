"""Tests des graphiques, icônes et fonctions d'affichage"""

import re
from pathlib import Path

import pytest

from job.cosmetics import ACCENTS
from web.rendering import (
    build_bar_chart,
    build_pie,
    format_euros,
    render_icon,
    safe_url,
)
import web.rendering as web_rendering


def test_format_euros():
    """Vérifie le format français des montants."""

    assert format_euros(2187.6) == "2\u202f188 €"
    assert format_euros(None) == ""


@pytest.mark.parametrize(
    "pUrl, pExpected",
    [
        ("https://example.com/job", "https://example.com/job"),
        ("javascript:alert(1)", "#"),
        ("JaVaScRiPt:alert(1)", "#"),
        (None, "#"),
    ],
)
def test_safe_url(pUrl, pExpected):
    """Vérifie que seules les URL http et https sont conservées."""

    assert safe_url(pUrl) == pExpected


@pytest.mark.parametrize("pName", ["../logo", "inconnue", "House", "house.svg"])
def test_render_icon_rejects_unknown_names(pName):
    """Vérifie qu'un nom hors du dossier d'icônes ne produit rien."""

    assert render_icon(pName) == ""


def test_render_icon_sets_size():
    """Vérifie l'insertion d'une icône à la taille demandée."""

    vIcon = render_icon("house", 20)

    assert vIcon.startswith('<svg aria-hidden="true"')
    assert 'width="20"' in vIcon
    assert render_icon("trash-2", 16).startswith("<svg")


def test_build_bar_chart_uses_a_common_scale():
    """Vérifie que les séries partagent la même échelle, sans barre nulle."""

    vChart = build_bar_chart(
        ["09/10", "10/10"],
        [("Offres", "#3B82F6", [0, 40]), ("Candidatures", "#F59E0B", [10, 4])],
    )

    assert [vBar["height"] for vBar in vChart["series"][0]["bars"]] == [2, 100]
    assert [vBar["height"] for vBar in vChart["series"][1]["bars"]] == [25, 10]


def test_build_pie_builds_conic_gradient():
    """Vérifie les segments du camembert et leur couleur."""

    vPie = build_pie(
        [
            {"label": "Adzuna", "count": 3, "percent": 75},
            {"label": "Jooble", "count": 1, "percent": 25},
        ]
    )

    assert vPie["total"] == 4
    assert vPie["gradient"] == (
        "conic-gradient(#3B82F6 0.00% 75.00%, #F59E0B 75.00% 100.00%)"
    )
    assert build_pie([])["gradient"] == ""


def test_build_bar_chart_with_independent_scales():
    """Vérifie qu'une série de faibles valeurs garde des barres visibles."""

    vChart = build_bar_chart(
        ["09/10", "10/10"],
        [("Offres", "#3B82F6", [0, 500]), ("Relances", "#8B5CF6", [1, 2])],
        pIndependentScales=True,
    )

    assert [vBar["height"] for vBar in vChart["series"][1]["bars"]] == [50, 100]
    assert vChart["scale"] == [
        {"value": 500, "color": "#3B82F6"},
        {"value": 2, "color": "#8B5CF6"},
    ]


@pytest.mark.parametrize("pValues, pEmptyText", [([0, 0], "Vide"), ([1, 0], "")])
def test_build_bar_chart_empty_state_and_axes(pValues, pEmptyText):
    """Vérifie le texte d'état vide et les libellés d'axes transmis au gabarit."""

    vChart = build_bar_chart(
        ["a", "b"],
        [("Offres", "#000", pValues)],
        pAxes=("Jour", "Nombre"),
        pEmptyText="Vide",
    )

    assert vChart["empty_text"] == pEmptyText
    assert (vChart["x_axis"], vChart["y_axis"]) == ("Jour", "Nombre")


def test_build_bar_chart_with_colors_per_bar_and_full_width():
    """Vérifie une couleur par barre et l'occupation de toute la largeur."""

    vChart = build_bar_chart(
        ["Titre", "Salaire"],
        [("Remplissage", ["var(--success)", "var(--danger)"], [97, 11])],
        pFillWidth=True,
    )

    assert [vBar["color"] for vBar in vChart["series"][0]["bars"]] == [
        "var(--success)",
        "var(--danger)",
    ]
    assert vChart["fill"] is True


@pytest.mark.parametrize(
    "pStatusCode, pTone", [(200, "success"), (400, "warning"), (500, "danger")]
)
def test_get_message_tone(pStatusCode, pTone):
    """Vérifie la couleur d'un message selon le résultat de la requête."""

    assert web_rendering.get_message_tone(pStatusCode) == pTone


def test_accent_rules_of_the_stylesheet_match_the_catalogue():
    """Vérifie que la feuille de style porte les teintes de chaque accent, en clair et en sombre."""

    vCss = "".join(
        vFile.read_text(encoding="utf-8")
        for vFile in sorted(Path("web/static/css").glob("*.css"))
    )

    for vId, (_, _, vLight, vDark) in ACCENTS.items():
        for vSelector, vColors in (
            (f':root[data-accent="{vId}"] {{', vLight),
            (f':root[data-accent="{vId}"][data-theme="dark"] {{', vDark),
        ):
            if vColors:
                vRule = vCss[
                    vCss.index(vSelector) : vCss.index("}", vCss.index(vSelector))
                ]

                assert f"--primary: {vColors['primary'].lower()};" in vRule, vSelector


def test_stylesheet_imports_every_part_in_order():
    """Vérifie que style.css importe chaque partie de css/ et qu'aucune n'est oubliée."""

    vText = Path("web/static/style.css").read_text(encoding="utf-8")
    vImported = re.findall(r'@import url\("css/([^"]+)"\);', vText)
    vParts = sorted(vFile.name for vFile in Path("web/static/css").glob("*.css"))

    assert vImported == vParts
