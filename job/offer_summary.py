"""Résumé d'une annonce en quelques lignes, extrait par règles de sa description

Les annonces suivent souvent le même plan : missions, profil recherché,
avantages. Le début de chaque partie, repérée par son intertitre, suffit à se
faire une idée ; sans intertitre, les deux premières phrases servent de résumé.
"""

import re

from job.fingerprint import normalize
from job.preparation import get_offer_skills
from job.presentation import format_euros
from job.salary_market import get_net_salary

# Partie : début normalisé d'un intertitre qui l'annonce
SECTION_HEADINGS = {
    "Missions": (
        "vos missions",
        "missions",
        "ce que vous ferez",
        "responsabilites",
        "le poste",
        "your role",
        "responsibilities",
        "what you will do",
        "what you ll do",
    ),
    "Profil recherché": (
        "votre profil",
        "profil recherche",
        "profil",
        "competences requises",
        "vous etes",
        "requirements",
        "qualifications",
        "what you bring",
        "what you ll bring",
        "about you",
    ),
    "Avantages": (
        "avantages",
        "nous offrons",
        "ce que nous offrons",
        "pourquoi nous rejoindre",
        "benefits",
        "what we offer",
        "perks",
    ),
}

# Longueur gardée par partie, et longueur maximale d'une ligne d'intertitre
MAX_PART_LENGTH = 220
MAX_HEADING_LENGTH = 40
MAX_SUMMARY_SKILLS = 6

# Valeurs données par les sources qui ne disent rien de l'offre
EMPTY_VALUES = ("not applicable", "non precise")

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Intertitre en ligne : quelques mots suivis de deux-points, après un début de
# texte, une fin de phrase ou des deux-points précédents
INLINE_HEADING_PATTERN = re.compile(
    r"(?:^|(?<=[.!?:])\s*)([A-Za-zÀ-ÿ' ]{4,40}?)\s*:\s", re.MULTILINE
)


def shorten(pText, pLength=MAX_PART_LENGTH):
    """Coupe un texte à la fin du mot précédant pLength caractères."""

    vText = " ".join(str(pText).split())

    rText = vText if len(vText) <= pLength else vText[:pLength].rsplit(" ", 1)[0] + "…"

    return rText


def find_section(pLine):
    """Retourne la partie annoncée par une ligne d'intertitre, ou None."""

    vLine = normalize(pLine)

    if not vLine or len(pLine.strip()) > MAX_HEADING_LENGTH:
        return None

    rSection = next(
        (
            vSection
            for vSection, vHeadings in SECTION_HEADINGS.items()
            if any(vLine.startswith(vHeading) for vHeading in vHeadings)
        ),
        None,
    )

    return rSection


def split_inline_sections(pDescription):
    """Retourne les parties d'une description sur une ligne, où chaque intertitre
    est suivi de deux-points : « … Profil: Vous êtes … ».
    """

    vText = str(pDescription or "")
    vMarkers = []

    for vMatch in INLINE_HEADING_PATTERN.finditer(vText):
        vSection = find_section(vMatch.group(1))

        if vSection:
            vMarkers.append((vMatch.start(), vMatch.end(), vSection))

    rSections = {}

    for vIndex, (_, vEnd, vSection) in enumerate(vMarkers):
        vNext = vMarkers[vIndex + 1][0] if vIndex + 1 < len(vMarkers) else len(vText)
        vPart = vText[vEnd:vNext].strip(" :")

        if vPart and vSection not in rSections:
            rSections[vSection] = vPart

    return rSections


def split_sections(pDescription):
    """Retourne le texte de chaque partie repérée dans la description, intertitres
    sur leur propre ligne ou suivis de deux-points.
    """

    vSections = {}
    vCurrent = None

    for vLine in str(pDescription or "").splitlines():
        vSection = find_section(vLine)

        if vSection:
            vCurrent = vSection
            vSections.setdefault(vCurrent, [])
        elif vCurrent and vLine.strip():
            vSections[vCurrent].append(vLine.strip())

    rSections = {
        vName: " ".join(vLines) for vName, vLines in vSections.items() if vLines
    } or split_inline_sections(pDescription)

    return rSections


def describe_facts(pOffer):
    """Retourne la ligne des faits : contrat, télétravail, salaire, expérience."""

    vSalary = get_net_salary(pOffer)

    rFacts = " · ".join(
        vPart
        for vPart in (
            pOffer.get("contract"),
            "télétravail" if pOffer.get("remote") is True else None,
            f"{format_euros(vSalary)} net/mois" if vSalary else None,
            pOffer.get("experience_level"),
        )
        if vPart and normalize(vPart) not in EMPTY_VALUES
    )

    return rFacts


def build_offer_summary(pOffer):
    """Retourne le résumé de l'annonce : liste de (intitulé, texte), vide sans texte."""

    vSections = split_sections(pOffer.get("description"))

    rSummary = [
        (vName, shorten(vSections[vName]))
        for vName in SECTION_HEADINGS
        if vName in vSections
    ]

    if not rSummary and pOffer.get("description"):
        vSentences = SENTENCE_END.split(" ".join(str(pOffer["description"]).split()))
        rSummary = [("En bref", shorten(" ".join(vSentences[:2])))]

    vSkills = get_offer_skills(pOffer)[:MAX_SUMMARY_SKILLS]

    if vSkills:
        rSummary.append(("Compétences", ", ".join(vSkills)))

    if vFacts := describe_facts(pOffer):
        rSummary.append(("En pratique", vFacts))

    return rSummary
