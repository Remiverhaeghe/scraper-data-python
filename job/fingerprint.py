"""Empreinte d'une offre : titre, entreprise et ville sous une forme comparable

Module sans dépendance au stockage : la migration qui calcule les empreintes
des offres déjà en base peut l'utiliser sans créer d'import circulaire.
"""

import re
import unicodedata
from functools import lru_cache

# Mentions de genre ajoutées aux titres : « H/F », « F/H », « (m/w/d) »...
GENDER_MARKERS = re.compile(
    r"\(?\b(?:h\s*/\s*f|f\s*/\s*h|m\s*/\s*[wf]\s*/\s*d|[wf]\s*/\s*m\s*/\s*d"
    r"|[hf]\s*/\s*[fh]\s*/\s*x)\b\)?",
    re.IGNORECASE,
)

# Formes juridiques retirées du nom de l'entreprise
LEGAL_FORMS = re.compile(
    r"\b(?:sas|sasu|sa|sarl|eurl|gmbh|ag|inc|ltd|llc|plc|bv|srl)\b\.?", re.IGNORECASE
)

# Mots du début de description comparés pour reconnaître deux annonces jumelles ;
# en dessous du minimum, le texte est trop court pour conclure.
SIGNATURE_WORDS = 20
MIN_SIGNATURE_WORDS = 12

# Textes normalisés gardés : agences, annonces douteuses, marché et doublons
# relisent les mêmes descriptions à chaque affichage.
NORMALIZE_CACHE_SIZE = 50000


def normalize(pText):
    """Met un texte sous une forme comparable : minuscules, sans accents ni ponctuation."""

    rText = normalize_text(str(pText or ""))

    return rText


@lru_cache(maxsize=NORMALIZE_CACHE_SIZE)
def normalize_text(pText):
    """Normalise un texte déjà converti en chaîne ; résultat gardé en cache."""

    vText = unicodedata.normalize("NFKD", pText)
    vText = "".join(vChar for vChar in vText if not unicodedata.combining(vChar))
    vText = GENDER_MARKERS.sub(" ", vText.lower())

    rText = " ".join(re.sub(r"[^a-z0-9]+", " ", vText).split())

    return rText


def normalize_company(pCompany):
    """Met un nom d'entreprise sous une forme comparable, sans sa forme juridique."""

    rCompany = normalize(LEGAL_FORMS.sub(" ", str(pCompany or "")))

    return rCompany


def normalize_city(pLocation):
    """Retourne la ville d'un lieu : « Lille (59) » ou « 59000 Lille, France » donnent « lille »."""

    vCity = re.split(r"[,(]| - ", str(pLocation or ""))[0]

    rCity = normalize(re.sub(r"\d+", " ", vCity))

    return rCity


def build_fingerprint(pOffer):
    """Construit l'empreinte d'une offre, ou None sans titre exploitable."""

    vTitle = normalize(pOffer.get("title"))
    vCompany = normalize_company(pOffer.get("company"))

    rFingerprint = None

    if vTitle:
        rFingerprint = "|".join(
            (vTitle, vCompany, normalize_city(pOffer.get("location")))
        )

    return rFingerprint


def build_description_signature(pDescription):
    """Retourne le début normalisé d'une description, ou None s'il est trop court.

    Deux annonces d'une même offre, publiées par deux sources, commencent par
    les mêmes mots même quand l'une donne l'entreprise et l'autre non.
    """

    vWords = normalize(pDescription).split()[:SIGNATURE_WORDS]

    rSignature = " ".join(vWords) if len(vWords) >= MIN_SIGNATURE_WORDS else None

    return rSignature


def borrow_missing_companies(pOffers):
    """Donne à une annonce sans entreprise celle de sa jumelle, et retourne leur nombre.

    Jumelles : même titre, même ville et même début de description. L'empreinte
    devient alors commune et les deux annonces sont regroupées comme doublons.
    pOffers est une liste de dictionnaires, modifiés sur place.
    """

    vCompanies = {}

    for vOffer in pOffers:
        vKey = build_twin_key(vOffer)

        if vKey and has_company(vOffer):
            vCompanies.setdefault(vKey, vOffer["company"])

    rBorrowed = 0

    for vOffer in pOffers:
        vKey = build_twin_key(vOffer)

        if not has_company(vOffer) and vKey in vCompanies:
            vOffer["company"] = vCompanies[vKey]
            rBorrowed += 1

    return rBorrowed


def has_company(pOffer):
    """Indique si l'entreprise est écrite ; une valeur manquante de pandas ne compte pas."""

    vCompany = pOffer.get("company")

    rHasCompany = isinstance(vCompany, str) and bool(vCompany.strip())

    return rHasCompany


def build_twin_key(pOffer):
    """Retourne la clé qui reconnaît deux annonces d'une même offre, ou None."""

    vSignature = build_description_signature(pOffer.get("description"))
    vTitle = normalize(pOffer.get("title"))

    rKey = (
        (vTitle, normalize_city(pOffer.get("location")), vSignature)
        if vSignature and vTitle
        else None
    )

    return rKey
