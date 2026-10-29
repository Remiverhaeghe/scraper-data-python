"""Score global d'une offre : correspondance, distance, salaire, fraîcheur et employeur

Chaque critère vaut de 0 à 1 et pèse selon les Paramètres. Un critère inconnu
(salaire non annoncé, lieu non placé) est écarté plutôt que compté à zéro : le
score se calcule sur les critères connus, poids renormalisés. Un diplôme demandé
au-dessus de celui du profil réduit ensuite le score, sans l'annuler.
"""

from job.education import EDUCATION_SCORE_FACTORS
from job.salary_market import get_net_salary

# Réglage de chaque poids : (clé dans les Paramètres, critère)
WEIGHT_SETTINGS = {
    "weight_match": "match",
    "weight_distance": "distance",
    "weight_salary": "salary",
    "weight_freshness": "freshness",
    "weight_employer": "employer",
}

# Au-delà de ce rayon par défaut, une offre ne vaut plus rien pour la distance.
DEFAULT_DISTANCE_KM = 50
CLOSE_DISTANCE_KM = 10

# Valeur d'un employeur pour le candidat : intermédiaire ou non
EMPLOYER_VALUES = {"agency": 0.4, "consulting": 0.6, "final": 1.0}


def rate_distance(pOffer, pRadiusKm):
    """Retourne 1 pour une offre proche ou en télétravail, 0 au double du rayon."""

    if pOffer.get("remote") is True:
        return 1.0

    vDistance = pOffer.get("distance_km")

    if vDistance is None:
        return None

    vLimit = 2 * (pRadiusKm or DEFAULT_DISTANCE_KM)

    rRate = max(0.0, min(1.0, (vLimit - vDistance) / (vLimit - CLOSE_DISTANCE_KM)))

    return rRate


def rate_salary(pOffer, pTarget):
    """Retourne la part du salaire visé atteinte par l'offre, plafonnée à 1."""

    vSalary = get_net_salary(pOffer)

    if not pTarget or vSalary is None:
        return None

    rRate = min(1.0, vSalary / pTarget)

    return rRate


def rate_employer(pOffer):
    """Retourne la valeur du type d'employeur, s'il a été repéré."""

    if pOffer.get("is_agency"):
        rRate = EMPLOYER_VALUES["agency"]
    elif pOffer.get("is_consulting"):
        rRate = EMPLOYER_VALUES["consulting"]
    elif "is_agency" in pOffer:
        rRate = EMPLOYER_VALUES["final"]
    else:
        rRate = None

    return rRate


def compute_global_score(pOffer, pSettings, pRadiusKm=None):
    """Retourne le score global de 0 à 100, ou None sans aucun critère connu."""

    vRates = {
        "match": (
            None if pOffer.get("match_score") is None else pOffer["match_score"] / 100
        ),
        "distance": rate_distance(pOffer, pRadiusKm),
        "salary": rate_salary(pOffer, pSettings.get("target_net_salary")),
        "freshness": (
            None if pOffer.get("freshness") is None else pOffer["freshness"] / 100
        ),
        "employer": rate_employer(pOffer),
    }
    vWeights = {
        vCriterion: pSettings.get(vSetting, 0) or 0
        for vSetting, vCriterion in WEIGHT_SETTINGS.items()
    }
    vKnown = [
        (vRate, vWeights[vCriterion])
        for vCriterion, vRate in vRates.items()
        if vRate is not None and vWeights[vCriterion]
    ]
    vTotal = sum(vWeight for _, vWeight in vKnown)

    rScore = (
        round(
            100
            * sum(vRate * vWeight for vRate, vWeight in vKnown)
            / vTotal
            * EDUCATION_SCORE_FACTORS.get(pOffer.get("education_status"), 1)
        )
        if vTotal
        else None
    )

    return rScore


def add_global_scores(pOffers, pSettings, pRadiusKm=None):
    """Ajoute global_score à chaque offre, après les autres critères."""

    for vOffer in pOffers:
        vOffer["global_score"] = compute_global_score(vOffer, pSettings, pRadiusKm)
