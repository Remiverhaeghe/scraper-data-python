"""Tests du score de fraîcheur des offres"""

from datetime import datetime

import pytest

from job.freshness import add_freshness, compute_freshness
from job.presentation import get_score_tone

NOW = datetime(2026, 10, 19, 12, 0)


@pytest.mark.parametrize(
    "pOffer, pExpected",
    [
        ({"published_at": "2026-10-19T08:00:00"}, 100),
        ({"published_at": "2026-10-04T08:00:00"}, 50),
        ({"first_seen_at": "2026-08-01T08:00:00"}, 0),
        ({"published_at": "2026-10-04", "source_labels": ["A", "B", "C"]}, 70),
        ({"published_at": "2026-10-19", "source_labels": ["A", "B"]}, 100),
        ({"published_at": "illisible", "first_seen_at": "2026-10-16"}, 90),
        ({}, 0),
    ],
)
def test_compute_freshness(pOffer, pExpected):
    """Vérifie l'âge, le bonus par source, la limite à 100 et la date de secours."""

    assert compute_freshness(pOffer, NOW) == pExpected


def test_add_freshness_and_tone():
    """Vérifie l'ajout du score à chaque offre et sa couleur."""

    vOffers = [{"published_at": "2026-10-19"}, {}]

    add_freshness(vOffers, NOW)

    assert [vOffer["freshness"] for vOffer in vOffers] == [100, 0]
    assert [get_score_tone(vScore) for vScore in (85, 50, 10)] == [
        "success",
        "warning",
        "muted",
    ]
