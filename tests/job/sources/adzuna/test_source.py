"""Tests de la déclaration de la source Adzuna"""

from types import SimpleNamespace

from job.sources.adzuna.source import build_params


def test_build_params_maps_search_criteria():
    """Vérifie la conversion des critères vers les paramètres Adzuna."""

    vJobConfig = SimpleNamespace(
        keyword="développeur python",
        location="Lille",
        max_distance_km=30.4,
        exclude_keywords=["stage", "agent de sécurité", "dentiste"],
    )

    assert build_params(vJobConfig) == {
        "sort_by": "date",
        "what": "développeur python",
        "where": "Lille",
        "distance": 30,
        "what_exclude": "stage dentiste",
    }


def test_build_params_without_criteria():
    """Vérifie que seuls les critères renseignés sont transmis."""

    vJobConfig = SimpleNamespace(
        keyword=None, location=None, max_distance_km=None, exclude_keywords=None
    )

    assert build_params(vJobConfig) == {"sort_by": "date"}
