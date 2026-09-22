# ============================================================================
# Filtrage spécifique des offres d'emploi
# ============================================================================


import pandas as pd

from utils.logger import get_logger


logger = get_logger(__name__)


def filter_jobs(pJobs, pConfig):
    """
    Filtre les offres selon la configuration de recherche.

    :param pJobs: DataFrame contenant les offres à filtrer.
    :param pConfig: Configuration des filtres.
    :return: DataFrame contenant les offres correspondant aux critères.
    """

    vJobs = pJobs.copy()

    if pConfig.keyword:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_keyword(
                    pJob,
                    pConfig.keyword
                ),
                axis=1
            )
        ]

    if pConfig.location:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_location(
                    pJob,
                    pConfig.location
                ),
                axis=1
            )
        ]

    if pConfig.max_distance_km is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_distance(
                    pJob,
                    pConfig.max_distance_km
                ),
                axis=1
            )
        ]

    if pConfig.contract:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_contract(
                    pJob,
                    pConfig.contract
                ),
                axis=1
            )
        ]

    if pConfig.min_salary is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_min_salary(
                    pJob,
                    pConfig.min_salary
                ),
                axis=1
            )
        ]

    if pConfig.max_salary is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_max_salary(
                    pJob,
                    pConfig.max_salary
                ),
                axis=1
            )
        ]

    if pConfig.remote is not None:
        vJobs = vJobs[
            vJobs["remote"] == pConfig.remote
        ]

    if pConfig.min_remote_days is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_remote_days(
                    pJob,
                    pConfig.min_remote_days
                ),
                axis=1
            )
        ]

    if pConfig.metro_required:
        vJobs = vJobs[
            vJobs.apply(
                _matches_metro,
                axis=1
            )
        ]

    if pConfig.max_metro_distance_km is not None:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_metro_distance(
                    pJob,
                    pConfig.max_metro_distance_km
                ),
                axis=1
            )
        ]

    if pConfig.education:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_text(
                    pJob["education"],
                    pConfig.education
                ),
                axis=1
            )
        ]

    if pConfig.skills:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_all_texts(
                    pJob["skills"],
                    pConfig.skills
                ),
                axis=1
            )
        ]

    if pConfig.missions:
        vJobs = vJobs[
            vJobs.apply(
                lambda pJob: _matches_all_texts(
                    pJob["missions"],
                    pConfig.missions
                ),
                axis=1
            )
        ]

    vJobs = vJobs.reset_index(
        drop=True
    )

    logger.info(
        "Filtrage des offres : %s offre(s) conservée(s) sur %s",
        len(vJobs),
        len(pJobs)
    )

    rJobs = vJobs

    return rJobs


def _matches_keyword(pJob, pKeyword):
    """
    Recherche un mot-clé dans les principales informations textuelles
    de l'offre.
    """

    vText = " ".join([
        str(pJob["title"] or ""),
        str(pJob["description"] or ""),
        str(pJob["missions"] or ""),
        str(pJob["requirements"] or ""),
        str(pJob["skills"] or "")
    ])

    rMatches = pKeyword.lower() in vText.lower()

    return rMatches


def _matches_location(pJob, pLocation):
    """
    Vérifie que la localisation recherchée est présente dans l'offre.
    """

    vLocation = str(
        pJob["location"] or ""
    )

    rMatches = pLocation.lower() in vLocation.lower()

    return rMatches


def _matches_distance(pJob, pMaxDistanceKm):
    """
    Vérifie que l'offre se trouve dans la distance maximale demandée.
    """

    vDistance = pJob["distance_km"]

    rMatches = (
        vDistance is not None
        and not pd.isna(vDistance)
        and vDistance <= pMaxDistanceKm
    )

    return rMatches


def _matches_contract(pJob, pContract):
    """
    Vérifie le type de contrat.
    """

    vContract = str(
        pJob["contract"] or ""
    )

    rMatches = vContract.lower() == pContract.lower()

    return rMatches


def _matches_min_salary(pJob, pMinSalary):
    """
    Vérifie que le salaire maximum de l'offre atteint le minimum recherché.
    """

    vSalaryMax = pJob["salary_max"]

    rMatches = (
        vSalaryMax is not None
        and not pd.isna(vSalaryMax)
        and vSalaryMax >= pMinSalary
    )

    return rMatches


def _matches_max_salary(pJob, pMaxSalary):
    """
    Vérifie que le salaire minimum de l'offre ne dépasse pas le maximum recherché.
    """

    vSalaryMin = pJob["salary_min"]

    rMatches = (
        vSalaryMin is not None
        and not pd.isna(vSalaryMin)
        and vSalaryMin <= pMaxSalary
    )

    return rMatches


def _matches_remote_days(pJob, pMinRemoteDays):
    """
    Vérifie le nombre minimum de jours de télétravail.
    """

    vRemoteDays = pJob["remote_days"]

    rMatches = (
        vRemoteDays is not None
        and not pd.isna(vRemoteDays)
        and vRemoteDays >= pMinRemoteDays
    )

    return rMatches


def _matches_metro(pJob):
    """
    Vérifie que l'offre dispose d'une station de métro identifiée.
    """

    vMetro = pJob["nearest_metro"]

    rMatches = (
        vMetro is not None
        and not pd.isna(vMetro)
        and bool(vMetro)
    )

    return rMatches


def _matches_metro_distance(pJob, pMaxDistanceKm):
    """
    Vérifie la distance maximale jusqu'à la station de métro.
    """

    vMetroDistance = pJob["metro_distance_km"]

    rMatches = (
        vMetroDistance is not None
        and not pd.isna(vMetroDistance)
        and vMetroDistance <= pMaxDistanceKm
    )

    return rMatches


def _matches_text(pText, pExpectedText):
    """
    Vérifie la présence d'un texte dans une valeur.
    """

    rMatches = (
        pExpectedText.lower()
        in str(pText or "").lower()
    )

    return rMatches


def _matches_all_texts(pText, pExpectedTexts):
    """
    Vérifie que tous les textes recherchés sont présents.
    """

    vText = str(
        pText or ""
    ).lower()

    vMatches = True

    for vExpectedText in pExpectedTexts:
        if vExpectedText.lower() not in vText:
            vMatches = False
            break

    rMatches = vMatches

    return rMatches