"""Tests du modèle de tableau des offres"""

import pytest
from PySide6.QtCore import QModelIndex, Qt

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


def test_old_ad_shows_its_online_days():
    """Vérifie l'ancienneté affichée à côté de la date de première vue."""

    vOffer = {"first_seen_at": "2026-08-20T08:00:00", "recurring_days": 60}

    assert format_cell(vOffer, "first_seen_at").endswith("en ligne depuis 60 j")


def test_hybrid_offer_title_and_tooltip(qt_application):
    """Vérifie la mention « double profil » du titre et ses termes en infobulle."""

    vOffer = {"title": "Technicien MES", "hybrid_terms": ["MES", "SQL"]}
    vModel = OffersTableModel()
    vModel.set_offers([vOffer])
    vColumn = [vKey for _, vKey, _ in COLUMNS].index("title")
    vIndex = vModel.index(0, vColumn)

    assert format_cell(vOffer, "title") == "Technicien MES · double profil"
    assert vModel.data(vIndex, Qt.ItemDataRole.ToolTipRole).endswith(
        "informatique : MES, SQL"
    )


@pytest.mark.parametrize(
    "pKey, pOffer, pExpected",
    [
        (
            "salary_net_monthly_min",
            {"estimated_salary": "2 000 €"},
            "≈ 2 000 € (estimé)",
        ),
        ("salary_net_monthly_min", {}, ""),
        ("match_score", {"match_score": 72}, "72 %"),
        ("match_score", {"match_score": None}, ""),
        ("freshness", {"freshness": 80}, "80"),
        (
            "first_seen_at",
            {"first_seen_at": "2026-08-20T08:00:00", "republished": True},
            "20/08/2026 · republiée",
        ),
        (
            "first_seen_at",
            {"first_seen_at": "2026-08-20", "old_at_source_days": 45},
            "20/08/2026 · publiée il y a 45 j",
        ),
        ("first_seen_at", {"first_seen_at": "2026-08-20"}, "20/08/2026"),
        ("company", {"company": "Kent", "company_preferred": True}, "★ Kent"),
        ("company", {"company": "Adecco", "is_agency": True}, "Adecco · intérim"),
        ("company", {"company": "Alten", "is_consulting": True}, "Alten · ESN"),
        ("company", {"company": None, "is_agency": True}, " · intérim"),
        (
            "title",
            {"title": "Technicien", "suspicious_signs": ["paiement"]},
            "⚠ Technicien · annonce douteuse",
        ),
        (
            "title",
            {"title": "Technicien", "like_ignored": True},
            "Technicien · proche d'une offre ignorée",
        ),
        (
            "title",
            {"title": "Technicien", "above_experience": True, "required_years": 5},
            "Technicien · 5 ans demandés",
        ),
        (
            "source_label",
            {"source_label": "Indeed", "source_labels": ["Indeed", "HelloWork"]},
            "Indeed, HelloWork",
        ),
        ("source_label", {"source_label": "Indeed"}, "Indeed"),
        ("application_status", {"application_status": "APPLIED"}, "Postulé"),
        ("city", {"city": None}, ""),
    ],
)
def test_format_cell_mentions(pKey, pOffer, pExpected):
    """Vérifie les mentions ajoutées à une cellule selon les signaux de l'offre."""

    assert format_cell(pOffer, pKey) == pExpected


@pytest.mark.parametrize(
    "pKey, pValue, pExpected",
    [
        ("match_score", 72, 72.0),
        ("match_score", None, -1.0),
        ("global_score", 55, 55.0),
    ],
)
def test_get_sort_value_scores(pKey, pValue, pExpected):
    """Vérifie que les scores absents passent derrière un score nul."""

    assert get_sort_value({pKey: pValue}, pKey) == pExpected


@pytest.mark.parametrize(
    "pKey, pOffer, pTone",
    [
        ("title", {"is_expired": True, "contract": "CDI"}, "muted"),
        ("company", {"company_preferred": True}, "primary"),
        ("match_score", {"match_score": 90}, "success"),
        ("match_score", {"match_score": None}, None),
        ("freshness", {"freshness": 10}, "muted"),
        ("source_label", {"needs_review": True}, "warning"),
        ("source_label", {}, None),
    ],
)
def test_get_cell_color_signals(pKey, pOffer, pTone):
    """Vérifie le grisage d'une offre expirée et les couleurs des scores."""

    vColor = get_cell_color(pOffer, pKey)

    if pTone is None:
        assert vColor is None
    else:
        assert vColor.name() == COLORS[pTone].lower()


def test_title_tooltip_lists_every_signal(qt_application):
    """Vérifie l'infobulle du titre : expiration, double profil et différences."""

    vModel = OffersTableModel()
    vModel.set_offers(
        [
            {
                "title": "Technicien MES",
                "is_expired": True,
                "hybrid_terms": ["MES"],
                "needs_review": True,
                "differences": ["salaire", "ville"],
            },
            {"title": None, "is_expired": True},
        ]
    )
    vColumn = [vKey for _, vKey, _ in COLUMNS].index("title")

    assert vModel.data(vModel.index(0, vColumn), Qt.ItemDataRole.ToolTipRole) == (
        "Technicien MES\nProbablement expirée\nDouble profil, maintenance et "
        "informatique : MES\nÀ valider, différences entre annonces : salaire, ville"
    )
    assert vModel.data(vModel.index(1, vColumn), Qt.ItemDataRole.ToolTipRole) == (
        "\nProbablement expirée"
    )
    assert vModel.data(vModel.index(0, 1), Qt.ItemDataRole.ToolTipRole) is None
    assert vModel.data(vModel.index(1, 0), Qt.ItemDataRole.FontRole) is None
    assert vModel.data(QModelIndex()) is None
    assert vModel.data(
        vModel.index(0, vColumn), Qt.ItemDataRole.ForegroundRole
    ).name() == (COLORS["muted"].lower())
    assert vModel.offer_at(1) == {"title": None, "is_expired": True}
    assert vModel.headerData(0, Qt.Orientation.Vertical) is None
