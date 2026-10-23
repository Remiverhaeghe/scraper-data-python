"""Tests de l'expérience demandée comparée à celle du candidat"""

import pytest

from job.experience_fit import (
    describe_experience_fit,
    mark_experience_fit,
    read_required_years,
)


@pytest.mark.parametrize(
    ("pLevel", "pExpected"),
    [
        ("5 ans", 5),
        ("Senior", 5),
        ("Mid-Senior Level", 5),
        ("Confirmé", 3),
        ("Débutant", 0),
        ("Entry Level", 0),
        ("Not Applicable", None),
        (None, None),
    ],
)
def test_required_years_are_read_from_the_level(pLevel, pExpected):
    """Vérifie les années lues dans le niveau donné par la source ou l'annonce."""

    assert read_required_years(pLevel) == pExpected


def test_offers_above_experience_are_marked():
    """Vérifie le repérage : une année de marge, rien sans expérience renseignée."""

    vOffers = [
        {"experience_level": "Senior"},
        {"experience_level": "4 ans"},
        {"experience_level": None},
    ]

    mark_experience_fit(vOffers, 3)

    assert [vOffer["above_experience"] for vOffer in vOffers] == [True, False, False]
    assert describe_experience_fit(vOffers[0], 3) == (
        "demande environ 5 ans, au-dessus de vos 3 ans"
    )
    assert (
        describe_experience_fit(vOffers[1], 3) == "à votre portée (3 ans d'expérience)"
    )
    assert describe_experience_fit(vOffers[0], 0) == ""
