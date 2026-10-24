"""Tests du score global des offres"""

from job.global_score import add_global_scores, compute_global_score, rate_distance

SETTINGS = {
    "target_net_salary": 3000,
    "weight_match": 5,
    "weight_distance": 3,
    "weight_salary": 2,
    "weight_freshness": 2,
    "weight_employer": 1,
}


def test_distance_is_rated_from_close_to_twice_the_radius():
    """Vérifie la distance : proche ou télétravail 1, double du rayon 0, inconnue écartée."""

    assert rate_distance({"distance_km": 5}, 30) == 1.0
    assert rate_distance({"distance_km": 60}, 30) == 0.0
    assert rate_distance({"distance_km": 35}, 30) == 0.5
    assert rate_distance({"remote": True}, 30) == 1.0
    assert rate_distance({}, 30) is None


def test_unknown_criteria_are_left_out():
    """Vérifie le calcul sur les seuls critères connus, poids renormalisés."""

    vComplete = {
        "match_score": 80,
        "distance_km": 5,
        "salary_net_monthly_min": 3000,
        "freshness": 50,
        "is_agency": False,
        "is_consulting": True,
    }

    # (0,8×5 + 1×3 + 1×2 + 0,5×2 + 0,6×1) / 13 = 0,8154
    assert compute_global_score(vComplete, SETTINGS, 30) == 82
    assert compute_global_score({"match_score": 80}, SETTINGS) == 80
    assert compute_global_score({}, SETTINGS) is None
    assert (
        compute_global_score({"match_score": 80}, {**SETTINGS, "weight_match": 0})
        is None
    )


def test_scores_are_added_to_each_offer():
    """Vérifie l'ajout du score global à chaque offre."""

    vOffers = [{"match_score": 90}, {"freshness": 40}]

    add_global_scores(vOffers, SETTINGS)

    assert [vOffer["global_score"] for vOffer in vOffers] == [90, 40]
