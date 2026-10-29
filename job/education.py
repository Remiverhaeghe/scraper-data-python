"""Niveau de diplôme demandé par les offres, comparé à celui du profil

Le niveau suit le cadre européen des certifications, déjà employé par La bonne
alternance : 3 pour un CAP, 4 pour le Bac, 5 pour un Bac+2 (BTS, DUT), 6 pour un
Bac+3 (licence, BUT), 7 pour un Bac+5 (master, ingénieur). Une annonce qui cite
plusieurs niveaux (« Bac+2 à Bac+5 ») accepte le plus bas.

Comme les compétences, le niveau est repéré une fois puis enregistré : 0 signifie
qu'aucun diplôme n'est cité. Une empreinte des règles relance l'analyse de toutes
les offres quand elles changent.
"""

import hashlib
import json
import math
import re
import time

from storage.database import connect_database
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

EDUCATION_LEVELS = {
    3: "CAP, BEP",
    4: "Bac",
    5: "Bac+2 (BTS, DUT)",
    6: "Bac+3 (licence, BUT)",
    7: "Bac+5 (master, ingénieur)",
}

# Niveau enregistré pour une offre qui ne cite aucun diplôme
NO_LEVEL = 0

# Sigles cherchés en capitales seulement : « cap » et « but » sont aussi des mots
# courants (« garder le cap », « le but du poste »). « Master » seul désigne
# souvent une branche Git ou un Scrum Master : il faut un complément.
LEVEL_PATTERNS = (
    (
        7,
        re.compile(
            r"\bbac\s*\+\s*5\b|\bmaster(?:'?s)?\s+(?:1|2|ii|pro|professionnel|en|de"
            r"|d'|degree|in|of)\b|\bm2\b|\bdipl[oô]m[eé]e?s?\s+d.ing[eé]nieur"
            r"|[eé]coles?\s+d.ing[eé]nieurs?\b",
            re.IGNORECASE,
        ),
    ),
    (
        6,
        re.compile(
            r"\bbac\s*\+\s*3\b|\blicence\s+pro(?:fessionnelle)?\b"
            r"|\bbachelor(?:'?s)?\s+degree\b",
            re.IGNORECASE,
        ),
    ),
    (6, re.compile(r"\bBUT\b")),
    (5, re.compile(r"\bbac\s*\+\s*2\b|\bbts\b|\bdut\b|\bdeust\b", re.IGNORECASE)),
    (
        4,
        re.compile(
            r"\bbac\s*pro\b|\bbaccalaur[eé]at\b"
            r"|\b(?:niveau|titulaire\s+du|dipl[oô]me\s+du)\s+bac\b(?!\s*\+)",
            re.IGNORECASE,
        ),
    ),
    (3, re.compile(r"\bCAP\b|\bBEP\b")),
)

# Libellés structurés des sources (« Bac ou équivalent ») : « bac » seul y suffit.
STRUCTURED_BAC_PATTERN = re.compile(r"\bbac\b(?!\s*\+)", re.IGNORECASE)

TEXT_COLUMNS = ("title", "description", "missions", "requirements")

# Écart avec le diplôme du profil : un niveau de plus se compense souvent par
# l'expérience, deux niveaux bloquent la plupart du temps.
EDUCATION_STATUSES = {
    "ok": ("Accessible avec votre diplôme", "success"),
    "close": ("Un niveau au-dessus du vôtre", "warning"),
    "blocked": ("Diplôme probablement bloquant", "danger"),
}

# Part du score global gardée selon l'écart de diplôme
EDUCATION_SCORE_FACTORS = {"close": 0.9, "blocked": 0.75}

EDUCATION_VERSION_KEY = "education_levels_version"
EDUCATION_VERSION = hashlib.sha256(
    json.dumps(
        [(vLevel, vPattern.pattern) for vLevel, vPattern in LEVEL_PATTERNS]
    ).encode("utf-8")
).hexdigest()[:16]

BATCH_SIZE = 500


def find_levels(pText, pStructured=False):
    """Retourne les niveaux cités dans un texte."""

    rLevels = {
        vLevel for vLevel, vPattern in LEVEL_PATTERNS if vPattern.search(pText or "")
    }

    if pStructured and not rLevels and STRUCTURED_BAC_PATTERN.search(pText or ""):
        rLevels.add(4)

    return rLevels


def read_structured_levels(pEducation):
    """Retourne les niveaux du champ formation d'une source, s'il est renseigné.

    La bonne alternance donne le niveau européen, France Travail des libellés
    (« Bac+2 ou équivalents ») : les deux formes sont lues.
    """

    if not pEducation:
        return set()

    try:
        vData = json.loads(pEducation) if isinstance(pEducation, str) else pEducation

    except ValueError:
        vData = pEducation

    vItems = vData if isinstance(vData, list) else [vData]
    rLevels = set()

    for vItem in vItems:
        if isinstance(vItem, dict) and str(vItem.get("european", "")).isdigit():
            rLevels.add(int(vItem["european"]))
        else:
            vText = (
                " ".join(str(vValue) for vValue in vItem.values())
                if isinstance(vItem, dict)
                else str(vItem)
            )
            rLevels |= find_levels(vText, pStructured=True)

    rLevels = {vLevel for vLevel in rLevels if vLevel in EDUCATION_LEVELS}

    return rLevels


def detect_education_level(pEducation, pText):
    """Retourne le niveau le plus bas accepté par l'offre, ou NO_LEVEL.

    Le champ structuré de la source prime ; à défaut, le texte de l'annonce.
    """

    vLevels = read_structured_levels(pEducation) or find_levels(pText)

    rLevel = min(vLevels) if vLevels else NO_LEVEL

    return rLevel


def read_level(pValue):
    """Retourne un niveau connu, ou None pour une valeur vide, nulle ou inconnue."""

    if pValue is None or (isinstance(pValue, float) and math.isnan(pValue)):
        return None

    try:
        vLevel = int(pValue)

    except (TypeError, ValueError):
        return None

    rLevel = vLevel if vLevel in EDUCATION_LEVELS else None

    return rLevel


def compare_education(pRequired, pMine):
    """Retourne l'écart entre le niveau demandé et celui du profil, ou None."""

    vRequired = read_level(pRequired)
    vMine = read_level(pMine)

    if vRequired is None or vMine is None:
        rStatus = None
    elif vRequired <= vMine:
        rStatus = "ok"
    elif vRequired == vMine + 1:
        rStatus = "close"
    else:
        rStatus = "blocked"

    return rStatus


def describe_education(pOffer):
    """Retourne le libellé du diplôme demandé, son écart et sa tonalité, ou None."""

    vLevel = read_level(pOffer.get("education_level"))

    if vLevel is None:
        return None

    vStatus = pOffer.get("education_status")
    vText, vTone = EDUCATION_STATUSES.get(vStatus, ("", "muted"))

    rDescription = {
        "label": EDUCATION_LEVELS[vLevel],
        "status": vStatus,
        "text": vText,
        "tone": vTone,
    }

    return rDescription


def clear_education_levels(pDatabaseFile):
    """Efface les niveaux repérés, à recalculer avec les nouvelles règles."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute("UPDATE job_offer SET education_level = NULL")
        vConnection.commit()

    finally:
        vConnection.close()


def get_offers_to_analyse(pDatabaseFile, pLimit):
    """Retourne la clé, la formation et le texte des offres encore sans niveau."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rRows = vConnection.execute(
            f"SELECT source, source_id, education, {', '.join(TEXT_COLUMNS)} "  # nosec B608
            "FROM job_offer WHERE education_level IS NULL LIMIT ?",
            (pLimit,),
        ).fetchall()

    finally:
        vConnection.close()

    return rRows


def save_education_levels(pDatabaseFile, pRows):
    """Enregistre les niveaux repérés, donnés par (niveau, source, id)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "UPDATE job_offer SET education_level = ? "
            "WHERE source = ? AND source_id = ?",
            pRows,
        )
        vConnection.commit()

    finally:
        vConnection.close()


def refresh_education_levels(pDatabaseFile, _pNow=None):
    """Repère le diplôme demandé par les offres qui n'en ont pas ; retourne leur nombre.

    La date n'est pas utilisée : la signature est celle des tâches du planificateur.
    """

    vStart = time.perf_counter()

    if get_setting_values(pDatabaseFile).get(EDUCATION_VERSION_KEY) != (
        EDUCATION_VERSION
    ):
        clear_education_levels(pDatabaseFile)
        save_setting_values(pDatabaseFile, {EDUCATION_VERSION_KEY: EDUCATION_VERSION})
        logger.info("Règles des diplômes modifiées : analyse de toutes les offres")

    rCount = 0

    while vRows := get_offers_to_analyse(pDatabaseFile, BATCH_SIZE):
        save_education_levels(
            pDatabaseFile,
            [
                (
                    detect_education_level(
                        vEducation, " ".join(str(vText or "") for vText in vTexts)
                    ),
                    vSource,
                    vSourceId,
                )
                for vSource, vSourceId, vEducation, *vTexts in vRows
            ],
        )
        rCount += len(vRows)

    if rCount:
        logger.info(
            "Diplôme demandé repéré dans %s offre(s) en %.1f s",
            rCount,
            time.perf_counter() - vStart,
        )

    return rCount


def refresh_education_levels_safely(pDatabaseFile):
    """Lance l'analyse en arrière-plan ; une erreur est journalisée sans bloquer."""

    try:
        refresh_education_levels(pDatabaseFile)

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Échec de l'analyse des diplômes demandés")


def format_education(pOffer):
    """Retourne le diplôme demandé suivi de son écart avec le profil, ou un texte vide."""

    vDescription = describe_education(pOffer)

    rText = (
        " · ".join(
            vPart for vPart in (vDescription["label"], vDescription["text"]) if vPart
        )
        if vDescription
        else ""
    )

    return rText


def is_education_blocked(pOffer):
    """Indique si l'offre demande un diplôme nettement au-dessus de celui du profil."""

    rBlocked = pOffer.get("education_status") == "blocked"

    return rBlocked
