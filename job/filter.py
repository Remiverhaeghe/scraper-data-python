"""Filtrage spécifique des offres d'emploi"""

import pandas as pd

from job.fingerprint import normalize
from job.location import find_department
from utils.logger import get_logger

logger = get_logger(__name__)


def keep_matching(pJobs, pPredicate):
    """Conserve les offres pour lesquelles pPredicate est vrai.

    Sur un DataFrame vide, apply(axis=1) renvoie un DataFrame et non une série
    de booléens : l'utiliser comme masque ferait perdre les colonnes.
    """

    rJobs = pJobs if pJobs.empty else pJobs[pJobs.apply(pPredicate, axis=1)]

    return rJobs


def filter_jobs(pJobs, pConfig):
    """Filtre les offres selon la configuration de recherche."""

    # Chaque filtre est journalisé par son effet global en fin de fonction : pour
    # comprendre pourquoi une offre manque, relancer avec moins de critères.
    vJobs = pJobs.copy()

    if pConfig.keyword:
        vJobs = keep_matching(
            vJobs, lambda pJob: matches_keyword(pJob, pConfig.keyword)
        )

    if pConfig.location:
        vJobs = keep_matching(
            vJobs, lambda pJob: matches_location(pJob, pConfig.location)
        )

    if pConfig.max_distance_km is not None:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_distance(pJob, pConfig.max_distance_km)
        )

    if pConfig.contract:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_contract(pJob, pConfig.contract)
        )

    if pConfig.min_salary is not None:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_min_salary(pJob, pConfig.min_salary)
        )

    if pConfig.max_salary is not None:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_max_salary(pJob, pConfig.max_salary)
        )

    if pConfig.remote is not None:
        vJobs = vJobs[vJobs["remote"] == pConfig.remote]

    if pConfig.min_remote_days is not None:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_remote_days(pJob, pConfig.min_remote_days)
        )

    if pConfig.metro_required:
        vJobs = keep_matching(vJobs, _matches_metro)

    if pConfig.max_metro_distance_km is not None:
        vJobs = keep_matching(
            vJobs,
            lambda pJob: _matches_metro_distance(pJob, pConfig.max_metro_distance_km),
        )

    if pConfig.education:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_text(pJob["education"], pConfig.education)
        )

    # Peu de sources renseignent les compétences : elles sont cherchées dans tout
    # le texte de l'offre, comme le mot-clé.
    if pConfig.skills:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_all_texts(get_offer_text(pJob), pConfig.skills)
        )

    if pConfig.exclude_keywords:
        vJobs = keep_matching(
            vJobs,
            lambda pJob: not contains_any(pJob.get("title"), pConfig.exclude_keywords),
        )

    if pConfig.missions:
        vJobs = keep_matching(
            vJobs, lambda pJob: _matches_all_texts(pJob["missions"], pConfig.missions)
        )

    vJobs = vJobs.reset_index(drop=True)

    logger.info(
        "Filtrage des offres : %s offre(s) conservée(s) sur %s", len(vJobs), len(pJobs)
    )

    rJobs = vJobs

    return rJobs


def get_offer_text(pJob):
    """Regroupe les principales informations textuelles d'une offre, en minuscules."""

    rText = " ".join(
        str(pJob.get(vColumn) or "")
        for vColumn in ("title", "description", "missions", "requirements", "skills")
    ).lower()

    return rText


def matches_keyword(pJob, pKeyword):
    """Recherche un mot-clé dans les principales informations textuelles
    de l'offre.
    """

    rMatches = pKeyword.lower() in get_offer_text(pJob)

    return rMatches


def matches_location(pJob, pLocation):
    """Vérifie que la localisation recherchée est présente dans l'offre.

    Par mots entiers, sans tenir compte des accents ni de la ponctuation
    (« Orleans » trouve « Orléans ») ; un département, par numéro ou par nom (« 59 », « Nord »),
    trouve aussi les offres de son code postal ou notées « (59) ».
    """

    vLocation = str(pJob.get("location") or "")
    vSearch = normalize(pLocation)
    vDepartment = find_department(pLocation)

    # Mots entiers : « Nord » ne trouve pas « Nordhausen ».
    rMatches = bool(vSearch) and f" {vSearch} " in (
        f" {normalize(vLocation)} {normalize(pJob.get('city'))} "
    )

    if not rMatches and vDepartment:
        rMatches = str(pJob.get("postal_code") or "").startswith(vDepartment) or (
            f"({vDepartment.lower()})" in vLocation.lower()
        )

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


def contains_any(pText, pWords):
    """Indique si l'un des mots figure dans le texte, sans tenir compte de la casse."""

    vText = str(pText or "").lower()

    rContains = any(vWord.lower() in vText for vWord in pWords)

    return rContains


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

    if pKeyword:
        rJobs = keep_matching(rJobs, lambda pJob: matches_keyword(pJob, pKeyword))

    if pLocation:
        rJobs = keep_matching(rJobs, lambda pJob: matches_location(pJob, pLocation))

    return rJobs
