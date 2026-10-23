"""Tests du modèle de tableau des offres"""

import pytest
from PySide6.QtCore import Qt

from gui.offers_model import (
    COLUMNS,
    SORT_ROLE,
    OffersTableModel,
    format_cell,
    format_status,
    get_cell_color,
    get_sort_value,
)
from gui.theme import COLORS
from job.presentation import format_net_salary

# Séparateur de milliers de format_euros : espace fine insécable
THOUSANDS = "\u202f"

SALARY_COLUMN = [vKey for _, vKey, _ in COLUMNS].index("salary_net_monthly_min")


@pytest.mark.parametrize(
    "pMinimum, pMaximum, pExpected",
    [
        (2000, 2500, f"2{THOUSANDS}000 € – 2{THOUSANDS}500 €"),
        (2000, 2000, f"2{THOUSANDS}000 €"),
        (None, 2500, f"2{THOUSANDS}500 €"),
        (None, None, ""),
    ],
)
def test_format_net_salary(pMinimum, pMaximum, pExpected):
    """Vérifie l'affichage d'une fourchette ou d'un montant unique."""

    vOffer = {"salary_net_monthly_min": pMinimum, "salary_net_monthly_max": pMaximum}

    assert format_net_salary(vOffer) == pExpected


def test_format_status_signals_follow_up():
    """Vérifie qu'une relance à faire est signalée à côté du statut."""

    assert format_status({"application_status": "APPLIED"}) == "Postulé"
    assert format_status({"application_status": "APPLIED", "follow_up_due": True}) == (
        "Postulé · à relancer"
    )
    assert format_status({"application_status": None}) == ""


def test_get_sort_value():
    """Vérifie des valeurs de tri homogènes, les salaires absents en dernier."""

    vKey = "salary_net_monthly_min"

    assert get_sort_value({vKey: 1800}, vKey) == 1800.0
    assert get_sort_value({vKey: None, "salary_net_monthly_max": 2000}, vKey) == 2000
    assert get_sort_value({}, vKey) == -1.0
    assert get_sort_value({"company": "Kent"}, "company") == "kent"
    assert get_sort_value({}, "company") == ""
    assert get_sort_value({"distance_km": 12}, "distance_km") == 12.0
    assert get_sort_value({"distance_km": None}, "distance_km") == float("inf")
    assert format_cell({"distance_km": 12}, "distance_km") == "12 km"
    assert format_cell({"distance_km": None}, "distance_km") == ""


def test_model_exposes_offers(qt_application):
    """Vérifie les données exposées au tableau."""

    vModel = OffersTableModel()
    vModel.set_offers(
        [
            {
                "title": "Développeur Java",
                "salary_net_monthly_min": 2100,
                "salary_net_monthly_max": 2600,
                "is_new": True,
            }
        ]
    )

    vTitle = vModel.index(0, 0)
    vSalary = vModel.index(0, SALARY_COLUMN)

    assert vModel.rowCount() == 1
    assert vModel.columnCount() == len(COLUMNS)
    assert vModel.headerData(0, Qt.Orientation.Horizontal) == "Titre"
    assert vModel.data(vTitle) == "Développeur Java"
    assert vModel.data(vTitle, Qt.ItemDataRole.FontRole).bold()
    assert vModel.data(vSalary) == f"2{THOUSANDS}100 € – 2{THOUSANDS}600 €"
    assert vModel.data(vSalary, SORT_ROLE) == 2100.0


@pytest.mark.parametrize(
    "pKey, pOffer, pTone",
    [
        ("contract", {"contract": "CDI"}, "success"),
        ("application_status", {"application_status": "REJECTED"}, "danger"),
        ("contract", {"contract": None}, None),
        ("title", {"title": "Offre"}, None),
    ],
)
def test_get_cell_color(pKey, pOffer, pTone):
    """Vérifie la couleur du contrat et du suivi, identique aux badges du web."""

    vColor = get_cell_color(pOffer, pKey)

    if pTone is None:
        assert vColor is None
    else:
        assert vColor.name() == COLORS[pTone].lower()
