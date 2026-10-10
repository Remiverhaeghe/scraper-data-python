"""Tests du rendu des graphiques"""

import pytest

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

    vChart.set_series(["10/10"], vChart.series)

    assert vChart.get_maximum([2]) == 400


@pytest.mark.parametrize(
    "pShares",
    [[("Adzuna", 3, "#3B82F6"), ("Jooble", 1, "#F59E0B")], []],
)
def test_pie_chart_renders(qt_application, pShares):
    """Vérifie le dessin du camembert, y compris sans aucune offre."""

    vChart = PieChart()
    vChart.set_shares(pShares)

    assert not render(vChart).isNull()
