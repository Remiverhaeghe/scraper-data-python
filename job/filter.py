"""Filtrage spécifique des offres d'emploi"""

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


def filter_jobs(pJobs, pConfig):
    """Filtre les offres selon la configuration de recherche."""

    vJobs = pJobs.copy()

    if pConfig.keyword:
        vJobs = vJobs[
            vJobs.apply(lambda pJob: matches_keyword(pJob, pConfig.keyword), axis=1)
        ]

    if pConfig.location:
        vJobs = vJobs[
            vJobs.apply(lambda pJob: matches_location(pJob, pConfig.location), axis=1)
        ]

    if pConfig.max_distance_km is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_distance(pJob, pConfig.max_distance_km), axis=1
            )
        ]

    if pConfig.contract:
        vJobs = vJobs[
            vJobs.apply(lambda pJob: _matches_contract(pJob, pConfig.contract), axis=1)
        ]

    if pConfig.min_salary is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_min_salary(pJob, pConfig.min_salary), axis=1
            )
        ]

    if pConfig.max_salary is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_max_salary(pJob, pConfig.max_salary), axis=1
            )
        ]

    if pConfig.remote is not None:
        vJobs = vJobs[vJobs["remote"] == pConfig.remote]

    if pConfig.min_remote_days is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_remote_days(pJob, pConfig.min_remote_days), axis=1
            )
        ]

    if pConfig.metro_required:
        vJobs = vJobs[vJobs.apply(_matches_metro, axis=1)]

    if pConfig.max_metro_distance_km is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_metro_distance(
                    pJob, pConfig.max_metro_distance_km
                ),
                axis=1,
            )
        ]

    if pConfig.education:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_text(pJob["education"], pConfig.education), axis=1
            )
        ]

    if pConfig.skills:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_all_texts(pJob["skills"], pConfig.skills), axis=1
            )
        ]

    if pConfig.missions:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_all_texts(pJob["missions"], pConfig.missions),
                axis=1,
            )
        ]

    vJobs = vJobs.reset_index(drop=True)

    logger.info(
        "Filtrage des offres : %s offre(s) conservée(s) sur %s", len(vJobs), len(pJobs)
    )

    rJobs = vJobs

    return rJobs


def matches_keyword(pJob, pKeyword):
    """Recherche un mot-clé dans les principales informations textuelles
    de l'offre.
    """

    vText = " ".join(
        [
            str(pJob["title"] or ""),
            str(pJob["description"] or ""),
            str(pJob["missions"] or ""),
            str(pJob["requirements"] or ""),
            str(pJob["skills"] or ""),
        ]
    )

    rMatches = pKeyword.lower() in vText.lower()

    return rMatches


def matches_location(pJob, pLocation):
    """Vérifie que la localisation recherchée est présente dans l'offre."""

    vLocation = str(pJob["location"] or "")

    rMatches = pLocation.lower() in vLocation.lower()

    return rMatches


def _matches_distance(pJob, pMaxDistanceKm):
    """Vérifie que l'offre se trouve dans la distance maximale demandée."""

    vDistance = pJob["distance_km"]

    rMatches = (
        vDistance is not None and not pd.isna(vDistance) and vDistance <= pMaxDistanceKm
    )

    return rMatches


def _matches_contract(pJob, pContract):
    """Vérifie le type de contrat."""

    rMatches = pJob["contract"] == pContract.upper()

    return rMatches


def _get_net_salary(pJob, pBound, pFallbackBound):
    """Retourne une borne du salaire net mensuel, ou l'autre borne à défaut."""

    rSalary = pJob[f"salary_net_monthly_{pBound}"]

    if rSalary is None or pd.isna(rSalary):
        rSalary = pJob[f"salary_net_monthly_{pFallbackBound}"]

    return rSalary


def _matches_min_salary(pJob, pMinSalary):
    """Vérifie que le net mensuel maximum de l'offre atteint le minimum recherché."""

    vSalary = _get_net_salary(pJob, "max", "min")

    rMatches = vSalary is not None and not pd.isna(vSalary) and vSalary >= pMinSalary

    return rMatches


def _matches_max_salary(pJob, pMaxSalary):
    """Vérifie que le net mensuel minimum de l'offre ne dépasse pas le maximum."""

    vSalary = _get_net_salary(pJob, "min", "max")

    rMatches = vSalary is not None and not pd.isna(vSalary) and vSalary <= pMaxSalary

    return rMatches


def _matches_remote_days(pJob, pMinRemoteDays):
    """Vérifie le nombre minimum de jours de télétravail."""

    vRemoteDays = pJob["remote_days"]

    rMatches = (
        vRemoteDays is not None
        and not pd.isna(vRemoteDays)
        and vRemoteDays >= pMinRemoteDays
    )

    return rMatches


def _matches_metro(pJob):
    """Vérifie que l'offre dispose d'une station de métro identifiée."""

    vMetro = pJob["nearest_metro"]

    rMatches = vMetro is not None and not pd.isna(vMetro) and bool(vMetro)

    return rMatches


def _matches_metro_distance(pJob, pMaxDistanceKm):
    """Vérifie la distance maximale jusqu'à la station de métro."""

    vMetroDistance = pJob["metro_distance_km"]

    rMatches = (
        vMetroDistance is not None
        and not pd.isna(vMetroDistance)
        and vMetroDistance <= pMaxDistanceKm
    )

    return rMatches


def _matches_text(pText, pExpectedText):
    """Vérifie la présence d'un texte dans une valeur."""

    rMatches = pExpectedText.lower() in str(pText or "").lower()

    return rMatches


def _matches_all_texts(pText, pExpectedTexts):
    """Vérifie que tous les textes recherchés sont présents."""

    vText = str(pText or "").lower()

    vMatches = True

    for vExpectedText in pExpectedTexts:
        if vExpectedText.lower() not in vText:
            vMatches = False
            break

    rMatches = vMatches

    return rMatches


def filter_by_keyword_and_location(pJobs, pKeyword, pLocation):
    """Filtre les offres d'une source dont l'API ne propose pas ces critères."""

    rJobs = pJobs

    if pKeyword and not rJobs.empty:
        rJobs = rJobs[rJobs.apply(lambda pJob: matches_keyword(pJob, pKeyword), axis=1)]

    if pLocation and not rJobs.empty:
        rJobs = rJobs[
            rJobs.apply(lambda pJob: matches_location(pJob, pLocation), axis=1)
        ]

    return rJobs
