"""Purge des offres hors sujet déjà enregistrées, avec aperçu préalable"""

from job.filter import contains_any
from job.profile import split_list
from storage.maintenance import delete_offers, get_purgeable_offers
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# En dessous, un mot trouverait des offres sans rapport : « it » dans « Equity ».
MIN_WORD_LENGTH = 3

# Mots qui écartent une offre dès sa récupération, ajoutés lors d'une purge
EXCLUDED_WORDS_KEY = "excluded_title_words"


def parse_purge_words(pText):
    """Retourne les mots saisis ; lève ValueError si aucun n'est utilisable."""

    rWords = split_list(pText)

    if not rWords:
        raise ValueError(
            "Saisissez au moins un mot, séparé des autres par des virgules."
        )

    vShortWords = [vWord for vWord in rWords if len(vWord) < MIN_WORD_LENGTH]

    if vShortWords:
        raise ValueError(
            f"Mots trop courts ({', '.join(vShortWords)}) : "
            f"{MIN_WORD_LENGTH} caractères au moins."
        )

    return rWords


def find_offers_to_purge(pDatabaseFile, pWords):
    """Retourne les offres dont le titre contient l'un des mots, hors candidatures."""

    rOffers = [
        vOffer
        for vOffer in get_purgeable_offers(pDatabaseFile)
        if contains_any(vOffer["title"], pWords)
    ]

    logger.info(
        "Aperçu de la purge : %s offre(s) pour %s mot(s)", len(rOffers), len(pWords)
    )

    return rOffers


def purge_offers(pDatabaseFile, pWords, pNow):
    """Supprime les offres trouvées par l'aperçu ; retourne leur nombre et la sauvegarde.

    La liste est recalculée ici : une candidature ajoutée depuis l'aperçu protège
    toujours son offre.
    """

    vOffers = find_offers_to_purge(pDatabaseFile, pWords)

    vBackupFile = None

    if vOffers:
        vBackupFile = delete_offers(
            pDatabaseFile,
            [(vOffer["source"], vOffer["source_id"]) for vOffer in vOffers],
            pNow,
        )

    rResult = (len(vOffers), vBackupFile)

    return rResult


def load_excluded_words(pDatabaseFile):
    """Retourne les mots qui écartent une offre dès sa récupération."""

    rWords = [
        vWord
        for vWord in load_json_setting(pDatabaseFile, EXCLUDED_WORDS_KEY, [], list)
        if isinstance(vWord, str)
    ]

    return rWords


def save_excluded_words(pDatabaseFile, pText):
    """Enregistre la liste des mots exclus ; vide, elle est effacée.

    Lève ValueError si un mot est trop court : il écarterait trop d'offres.
    """

    rWords = parse_purge_words(pText) if (pText or "").strip() else []

    save_json_setting(pDatabaseFile, EXCLUDED_WORDS_KEY, rWords)

    logger.info("Mots exclus de toutes les recherches : %s", len(rWords))

    return rWords


def add_excluded_words(pDatabaseFile, pWords):
    """Ajoute des mots à la liste des mots exclus ; retourne la liste complète."""

    rWords = save_excluded_words(
        pDatabaseFile, ", ".join([*load_excluded_words(pDatabaseFile), *pWords])
    )

    return rWords


def drop_excluded_offers(pItems, pWords):
    """Retire des offres récupérées celles dont le titre contient un mot exclu.

    Retourne les offres gardées et le nombre d'offres écartées.
    """

    vExcluded = (
        pItems["title"].map(lambda pTitle: contains_any(pTitle, pWords))
        if pWords and not pItems.empty and "title" in pItems
        else None
    )

    rResult = (
        (pItems, 0)
        if vExcluded is None
        else (pItems[~vExcluded.astype(bool)], int(vExcluded.sum()))
    )

    return rResult
