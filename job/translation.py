"""Traduction hors ligne des descriptions d'offres, avec Argos Translate

Argos est facultatif (requirements-translation.txt, environ 1 Go avec ses
modèles) : sans lui, l'application garde le lien vers Google Traduction. Les
modèles allemand et anglais s'installent par python -m job.translation ; une
description allemande passe automatiquement par l'anglais.
"""

import os
import re
import sys
from functools import lru_cache
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

TARGET_LANGUAGE = "fr"

# Les modèles sont rangés dans data/ du projet : la bibliothèque C++ qui les lit
# échoue sur un chemin accentué comme C:\Users\rémi. Fixé avant tout import
# d'Argos, qui lit ce réglage à son chargement.
MODELS_DIRECTORY = Path(__file__).resolve().parent.parent / "data" / "argos"
os.environ.setdefault("ARGOS_PACKAGES_DIR", str(MODELS_DIRECTORY))

# Modèles installés par la commande : chaque paire est téléchargée une fois.
MODEL_PAIRS = (("de", "en"), ("en", "fr"))

# Mots très fréquents de chaque langue, pour reconnaître celle d'une description
LANGUAGE_WORDS = {
    "en": {
        "the",
        "and",
        "you",
        "with",
        "for",
        "our",
        "are",
        "will",
        "your",
        "we",
        "to",
        "of",
        "in",
        "is",
        "on",
        "experience",
        "team",
    },
    "de": {
        "und",
        "die",
        "der",
        "das",
        "mit",
        "für",
        "sie",
        "wir",
        "ist",
        "du",
        "zu",
        "von",
        "auf",
        "bei",
        "dein",
        "deine",
        "unser",
        "erfahrung",
    },
}

WORD_PATTERN = re.compile(r"[^\W\d_]+")

# Argos traduit phrase par phrase : un paragraphe à la fois garde la mise en page.
PARAGRAPH_SEPARATOR = "\n"


def detect_language(pText):
    """Retourne la langue la plus probable du texte parmi LANGUAGE_WORDS, ou None."""

    vWords = WORD_PATTERN.findall((pText or "").lower())
    vScores = {
        vLanguage: sum(vWord in vCommonWords for vWord in vWords)
        for vLanguage, vCommonWords in LANGUAGE_WORDS.items()
    }
    vBest = max(vScores, key=vScores.get)

    rLanguage = vBest if vScores[vBest] else None

    return rLanguage


def load_argos():
    """Retourne le module de traduction d'Argos, ou None s'il n'est pas installé."""

    try:
        # pylint: disable=import-outside-toplevel
        import argostranslate.translate as rArgos

    except ImportError:
        rArgos = None

    return rArgos


@lru_cache(maxsize=1)
def get_installed_codes():
    """Retourne les codes des langues dont un modèle est installé."""

    vArgos = load_argos()

    rCodes = (
        frozenset(vLanguage.code for vLanguage in vArgos.get_installed_languages())
        if vArgos
        else frozenset()
    )

    return rCodes


def can_translate(pText):
    """Indique si la description peut être traduite sur cet ordinateur."""

    vLanguage = detect_language(pText)

    rPossible = (
        vLanguage is not None
        and {vLanguage, TARGET_LANGUAGE} <= get_installed_codes()
        and (vLanguage == "en" or "en" in get_installed_codes())
    )

    return rPossible


@lru_cache(maxsize=32)
def translate_to_french(pText):
    """Traduit une description en français, paragraphe par paragraphe.

    Lève ValueError avec un message lisible si la traduction est impossible.
    """

    vLanguage = detect_language(pText)

    if not can_translate(pText):
        raise ValueError(
            "Traduction hors ligne indisponible pour ce texte : modèle absent "
            "ou langue non reconnue."
        )

    vArgos = load_argos()

    try:
        vParagraphs = [
            (
                vArgos.translate(vParagraph, vLanguage, TARGET_LANGUAGE)
                if vParagraph.strip()
                else vParagraph
            )
            for vParagraph in pText.split(PARAGRAPH_SEPARATOR)
        ]

    except Exception as vError:
        logger.exception("Traduction hors ligne impossible")
        raise ValueError("La traduction a échoué : voir le journal.") from vError

    # La longueur suffit au diagnostic ; le texte de l'offre n'est pas journalisé.
    logger.info(
        "Description traduite de « %s » en français : %s caractère(s)",
        vLanguage,
        len(pText),
    )

    rText = PARAGRAPH_SEPARATOR.join(vParagraphs)

    return rText


def install_models():
    """Télécharge et installe les modèles de MODEL_PAIRS qui manquent."""

    # pylint: disable=import-outside-toplevel
    import argostranslate.package as vPackages

    vPackages.update_package_index()
    vAvailable = vPackages.get_available_packages()

    for vFrom, vTo in MODEL_PAIRS:
        vPackage = next(
            (
                vCandidate
                for vCandidate in vAvailable
                if vCandidate.from_code == vFrom and vCandidate.to_code == vTo
            ),
            None,
        )

        if vPackage is None:
            print(f"Modèle {vFrom} vers {vTo} introuvable dans l'index d'Argos.")
            continue

        print(f"Téléchargement du modèle {vFrom} vers {vTo}…")
        vPackages.install_from_path(vPackage.download())

    get_installed_codes.cache_clear()
    print("Modèles installés : " + ", ".join(sorted(get_installed_codes())))


if __name__ == "__main__":
    if load_argos() is None:
        print("Argos n'est pas installé : pip install -r requirements-translation.txt")
        sys.exit(1)

    install_models()
