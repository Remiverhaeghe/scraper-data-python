"""Pitch de présentation, en version 30 secondes et 2 minutes, construit par règles

Le texte part du profil (accroche, expériences, réalisations) et de l'offre
(compétences couvertes et manquantes) : c'est une trame à dire à voix haute,
à reformuler avec ses propres mots.
"""

# Expériences et compétences citées au plus, pour rester dans le temps imparti
SHORT_SKILLS = 3
SHORT_EXPERIENCES = 2
LONG_EXAMPLES = 2


def end_sentence(pText):
    """Termine une phrase par un point, sans le doubler."""

    vText = pText.strip()

    rText = vText if vText.endswith((".", "!", "?")) else f"{vText}."

    return rText


def lower_first(pText):
    """Met la première lettre en minuscule, pour insérer le texte dans une phrase."""

    rText = pText[:1].lower() + pText[1:]

    return rText


def describe_of(pName):
    """Retourne « de Globex » ou, devant une voyelle ou un h, « d'Acme »."""

    rText = f"d'{pName}" if pName[:1].lower() in "aeiouyhéèêàâîôû" else f"de {pName}"

    return rText


def describe_target(pCompany, pTitle):
    """Retourne « d'Acme sur le poste de Dev », « du poste de Dev » ou « de ce poste »."""

    if pCompany and pTitle:
        rText = f"{describe_of(pCompany)} sur le poste de {pTitle}"
    elif pCompany:
        rText = describe_of(pCompany)
    elif pTitle:
        rText = f"du poste de {pTitle}"
    else:
        rText = "de ce poste"

    return rText


def find_examples(pProfile, pSkills):
    """Retourne les expériences avec une réalisation qui illustrent les compétences."""

    vSkills = {vSkill.lower() for vSkill in pSkills}

    rExamples = [
        vExperience
        for vExperience in pProfile["experiences"]
        if vExperience.get("achievement")
        and vSkills
        & {str(vSkill).lower() for vSkill in vExperience.get("skills") or ()}
    ]

    return rExamples


def build_pitch(pProfile, pMatch, pOffer):
    """Retourne le pitch court (30 secondes) et long (2 minutes) pour une offre."""

    vTitle = pOffer.get("title")
    vCompany = pOffer.get("company")
    vTitles = list(
        dict.fromkeys(
            vExperience["title"]
            for vExperience in pProfile["experiences"]
            if vExperience.get("title")
        )
    )[:SHORT_EXPERIENCES]
    vSkills = pMatch["covered"][:SHORT_SKILLS]

    vShort = []

    if pProfile.get("headline"):
        vShort.append(end_sentence(pProfile["headline"]))

    if vTitles:
        vShort.append(
            "J'ai notamment été "
            + " puis ".join(lower_first(vItem) for vItem in vTitles)
            + "."
        )

    if vSkills:
        vShort.append(
            f"Je pratique {', '.join(vSkills)}, des compétences demandées ici."
        )

    vShort.append(
        "Je souhaite aujourd'hui mettre mon expérience au service "
        f"{describe_target(vCompany, vTitle)}."
    )

    vLong = vShort[:-1]

    for vExperience in find_examples(pProfile, pMatch["covered"])[:LONG_EXAMPLES]:
        vLong.append(
            f"Comme {lower_first(vExperience['title'])}, j'ai par exemple "
            f"{end_sentence(lower_first(vExperience['achievement']))}"
        )

    if pMatch["missing"]:
        vLong.append(
            f"Je progresse aussi sur {pMatch['missing'][0]}, que je travaille "
            "en ce moment."
        )

    vLong += [
        vShort[-1],
        "Qu'attendez-vous en priorité de la personne qui rejoindra l'équipe ?",
    ]

    rPitch = {"short": " ".join(vShort), "long": " ".join(vLong)}

    return rPitch
