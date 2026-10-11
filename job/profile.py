"""Profil du candidat : compétences, expériences et variantes de CV

Le profil est saisi sous forme de texte simple, une ligne par élément, pour
rester facile à modifier sans formulaire complexe :
  - compétences : séparées par des virgules ;
  - expériences : « Poste | compétences | réalisation marquante » ;
  - CV : « Nom du CV | compétences mises en avant ».
"""

import json

from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

PROFILE_KEY = "candidate_profile"

# Champs d'une ligne d'expérience et d'une ligne de CV, dans l'ordre de saisie
EXPERIENCE_FIELDS = ("title", "skills", "achievement")
CV_FIELDS = ("name", "skills")

# Au-delà, une saisie est probablement une erreur de copier-coller.
MAX_TEXT_LENGTH = 20000

EMPTY_PROFILE = {
    "name": "",
    "headline": "",
    "skills": [],
    "experiences": [],
    "cv_variants": [],
}


def split_list(pText):
    """Découpe une liste séparée par des virgules, sans vides ni doublons.

    « Java » et « java » ne comptent qu'une fois : la première écriture est gardée.
    """

    rValues = []
    vSeen = set()

    for vValue in (pText or "").split(","):
        vValue = vValue.strip()

        if vValue and vValue.lower() not in vSeen:
            vSeen.add(vValue.lower())
            rValues.append(vValue)

    return rValues


def parse_lines(pText, pFields):
    """Découpe des lignes « champ | champ | ... » en dictionnaires.

    Le champ nommé skills est découpé en liste ; une ligne vide est ignorée.
    """

    rItems = []

    for vLine in (pText or "").splitlines():
        if not vLine.strip():
            continue

        vParts = [vPart.strip() for vPart in vLine.split("|")]
        vParts += [""] * (len(pFields) - len(vParts))
        vItem = dict(zip(pFields, vParts))

        if "skills" in vItem:
            vItem["skills"] = split_list(vItem["skills"])

        rItems.append(vItem)

    return rItems


def format_lines(pItems, pFields):
    """Remet des éléments du profil sous forme de lignes « champ | champ »."""

    rText = "\n".join(
        " | ".join(
            (
                ", ".join(vItem.get(vField) or [])
                if vField == "skills"
                else vItem.get(vField) or ""
            )
            for vField in pFields
        )
        for vItem in pItems
    )

    return rText


def build_profile(pName, pHeadline, pSkills, pExperiences, pCvVariants):
    """Construit un profil à partir des textes saisis ; lève ValueError si trop long."""

    vTexts = (pName, pHeadline, pSkills, pExperiences, pCvVariants)

    if any(len(vText or "") > MAX_TEXT_LENGTH for vText in vTexts):
        raise ValueError("Profil trop long : un champ dépasse la taille autorisée.")

    rProfile = {
        "name": (pName or "").strip(),
        "headline": (pHeadline or "").strip(),
        "skills": split_list(pSkills),
        "experiences": parse_lines(pExperiences, EXPERIENCE_FIELDS),
        "cv_variants": parse_lines(pCvVariants, CV_FIELDS),
    }

    return rProfile


def profile_to_texts(pProfile):
    """Retourne les textes à afficher dans le formulaire du profil."""

    rTexts = {
        "name": pProfile["name"],
        "headline": pProfile["headline"],
        "skills": ", ".join(pProfile["skills"]),
        "experiences": format_lines(pProfile["experiences"], EXPERIENCE_FIELDS),
        "cv_variants": format_lines(pProfile["cv_variants"], CV_FIELDS),
    }

    return rTexts


def load_profile(pDatabaseFile):
    """Retourne le profil enregistré, ou un profil vide."""

    rProfile = dict(EMPTY_PROFILE)
    vValue = get_setting_values(pDatabaseFile).get(PROFILE_KEY)

    if vValue:
        try:
            rProfile.update(json.loads(vValue))

        except ValueError:
            logger.warning("Profil enregistré illisible : profil vide utilisé")

    return rProfile


def save_profile(pDatabaseFile, pProfile):
    """Enregistre le profil du candidat."""

    save_setting_values(
        pDatabaseFile, {PROFILE_KEY: json.dumps(pProfile, ensure_ascii=False)}
    )

    logger.info(
        "Profil enregistré : %s compétence(s), %s expérience(s), %s CV",
        len(pProfile["skills"]),
        len(pProfile["experiences"]),
        len(pProfile["cv_variants"]),
    )


def is_profile_empty(pProfile):
    """Indique si le profil ne contient encore aucune compétence ni expérience."""

    rEmpty = not pProfile["skills"] and not pProfile["experiences"]

    return rEmpty
