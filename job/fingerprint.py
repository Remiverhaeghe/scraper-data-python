"""Empreinte d'une offre : titre, entreprise et ville sous une forme comparable

Module sans dépendance au stockage : la migration qui calcule les empreintes
des offres déjà en base peut l'utiliser sans créer d'import circulaire.
"""

import re
import unicodedata

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


def normalize(pText):
    """Met un texte sous une forme comparable : minuscules, sans accents ni ponctuation."""

    vText = unicodedata.normalize("NFKD", str(pText or ""))
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
