"""Tests du rendu des graphiques"""

import pytest
from PySide6.QtCore import qInstallMessageHandler

from gui.chart import BarChart, PieChart


def render(pWidget):
    """Dessine le widget dans une image, comme à l'affichage."""

    pWidget.resize(420, 220)

    rImage = pWidget.grab().toImage()

    return rImage


@pytest.mark.parametrize(
    "pSeries, pIndependentScales",
    [
        ([("Offres", "#3B82F6", [0, 4, 12])], False),
        (
            [
                ("Offres", "#3B82F6", [0, 400, 12]),
                ("Candidatures", "#F59E0B", [1, 0, 2]),
                ("Relances", "#8B5CF6", [0, 0, 1]),
            ],
            True,
        ),
        ([("Offres", "#3B82F6", [0, 0, 0])], False),
    ],
)
def test_bar_chart_renders(qt_application, pSeries, pIndependentScales):
    """Vérifie le dessin d'une ou plusieurs séries, valeurs nulles comprises."""

    vChart = BarChart()
    vChart.set_series(["08/10", "09/10", "10/10"], pSeries, pIndependentScales)

    assert not render(vChart).isNull()


def test_bar_chart_independent_scales(qt_application):
    """Vérifie l'échelle propre à chaque série."""

    vChart = BarChart()
    vChart.set_series(
        ["10/10"],
        [("Offres", "#3B82F6", [400]), ("Relances", "#8B5CF6", [2])],
        pIndependentScales=True,
    )

    assert vChart.get_maximum([2]) == 2
    assert vChart.get_scale() == [(400, "#3B82F6"), (2, "#8B5CF6")]

    vChart.set_series(["10/10"], vChart.series)

    assert vChart.get_maximum([2]) == 400
    assert [vValue for vValue, _ in vChart.get_scale()] == [400]


def test_bar_chart_caps_scale_above_an_outlier(qt_application):
    """Vérifie qu'un pic isolé n'écrase pas les autres barres."""

    vChart = BarChart()
    vChart.set_series(
        ["15/10", "16/10", "17/10"],
        [("Offres", "#3B82F6", [1736, 40, 12])],
        pIndependentScales=True,
    )

    assert vChart.get_maximum([1736, 40, 12]) == 60
    assert vChart.get_maximum([50, 40, 12]) == 50
    assert vChart.get_scale() == [(60, "#3B82F6")]
    assert not render(vChart).isNull()


@pytest.mark.parametrize(
    "pShares",
    [[("Adzuna", 3, "#3B82F6"), ("Jooble", 1, "#F59E0B")], []],
)
def test_pie_chart_renders(qt_application, pShares):
    """Vérifie le dessin du camembert, y compris sans aucune offre."""

    vChart = PieChart()
    vChart.set_shares(pShares)

    assert not render(vChart).isNull()


def test_pie_chart_renders_without_qt_warning(qt_application):
    """Vérifie que le titre central ne provoque aucun avertissement de police."""

    vMessages = []

    vPrevious = qInstallMessageHandler(
        lambda pType, pContext, pMessage: vMessages.append(pMessage)
    )

    try:
        vChart = PieChart()
        vChart.setStyleSheet("font-size: 13px;")
        vChart.set_shares([("Adzuna", 3, "#3B82F6")])
        render(vChart)

    finally:
        qInstallMessageHandler(vPrevious)

    assert not [vMessage for vMessage in vMessages if "setPointSizeF" in vMessage]


@pytest.mark.parametrize("pValues, pEmpty", [([0, 0], True), ([0, 3], False)])
def test_bar_chart_empty_state_and_axes(qt_application, pValues, pEmpty):
    """Vérifie l'état vide et le dessin avec les libellés d'axes."""

    vChart = BarChart()
    vChart.resize(400, 220)
    vChart.set_series(
        ["10/10", "11/10"],
        [("Offres", "#3b82f6", pValues)],
        pAxes=("Jour", "Nombre par jour"),
        pEmptyText="Aucune activité",
    )

    assert vChart.is_empty() is pEmpty
    assert not vChart.grab().isNull()


def test_bar_chart_accepts_colors_per_bar_and_full_width(qt_application):
    """Vérifie le dessin avec une couleur par barre sur toute la largeur."""

    vChart = BarChart()
    vChart.resize(600, 200)
    vChart.set_series(
        ["Titre", "Salaire"],
        [("Remplissage", ["#16A34A", "#DC2626"], [97, 11])],
        pAxes=("Champ", "%"),
        pFillWidth=True,
    )

    assert vChart.fill_width
    assert not vChart.grab().isNull()
