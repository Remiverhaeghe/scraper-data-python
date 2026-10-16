"""Types de questions de révision : vérification, présentation et correction

Chaque type a ses propres champs et sa propre forme de réponse : l'indice d'un
choix pour un QCM, un texte pour une valeur ou un code à compléter, une liste
d'indices pour un ordre ou une association, un point cliqué sur le schéma pour
une zone à désigner. Le reste de la révision (tirage, progression, examen) ne
dépend pas du type.
"""

import json
import math
import re

from job.schema_building import (
    check_construction,
    get_palette_limits,
    grade_construction,
)

DEFAULT_TYPE = "qcm"

TYPE_FIELDS = {
    "qcm": ("choices", "answer"),
    "numerique": ("value",),
    "ordre": ("items",),
    "association": ("pairs",),
    "saisie": ("code", "accepted"),
    "zone": ("zones", "answer"),
    "construction": ("components", "connections"),
}
OPTIONAL_FIELDS = ("code", "unit", "tolerance", "distractors")
QUESTION_TYPES = tuple(TYPE_FIELDS)

TYPE_LABELS = {
    "qcm": "QCM",
    "numerique": "Calcul",
    "ordre": "Remise en ordre",
    "association": "Association",
    "saisie": "Code à compléter",
    "zone": "Zone à désigner",
    "construction": "Schéma à construire",
}

# Taille maximale du schéma envoyé par le navigateur, en caractères JSON
MAX_SCHEMA_LENGTH = 20_000

# Libellé du point cliqué en dehors de toutes les zones d'une question « zone »
OUTSIDE_ZONES = "un endroit sans composant"

# Repère du trou à compléter dans l'extrait d'une question « saisie »
BLANK = "____"

DEFAULT_TOLERANCE = 1.0
MAX_TOLERANCE = 20.0
MAX_UNIT_LENGTH = 10
MAX_TEXT_ANSWER_LENGTH = 200

UNIT_PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "µ": 1e-6,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
}
NUMBER_PATTERN = re.compile(r"([-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*(\S*)")


def get_type(pQuestion):
    """Retourne le type d'une question, QCM par défaut."""

    rType = pQuestion.get("type", DEFAULT_TYPE)

    return rType


def is_text_list(pValue, pMinimum, pMaximum):
    """Indique si une valeur est une liste de textes non vides, de taille bornée."""

    rValid = (
        isinstance(pValue, list)
        and pMinimum <= len(pValue) <= pMaximum
        and all(isinstance(vItem, str) and vItem.strip() for vItem in pValue)
    )

    return rValid


def is_number(pValue):
    """Indique si une valeur est un nombre fini ; bool n'en est pas un."""

    rNumber = (
        isinstance(pValue, (int, float))
        and not isinstance(pValue, bool)
        and math.isfinite(pValue)
    )

    return rNumber


def check_choices(pQuestion):
    """Vérifie un QCM ; retourne le défaut trouvé, ou une chaîne vide."""

    vChoices = pQuestion["choices"]

    if not is_text_list(vChoices, 2, 5):
        return "2 à 5 choix attendus"

    # bool est un int en Python : True ne doit pas passer pour la réponse 1.
    if (
        not isinstance(pQuestion["answer"], int)
        or isinstance(pQuestion["answer"], bool)
        or not 0 <= pQuestion["answer"] < len(vChoices)
    ):
        return "réponse hors des choix"

    return ""


def check_numeric(pQuestion):
    """Vérifie une question de calcul ; retourne le défaut trouvé, ou ""."""

    vUnit = pQuestion.get("unit", "")
    vTolerance = pQuestion.get("tolerance", DEFAULT_TOLERANCE)

    if not is_number(pQuestion["value"]):
        return "valeur numérique attendue"

    if not isinstance(vUnit, str) or len(vUnit) > MAX_UNIT_LENGTH or " " in vUnit:
        return "unité invalide"

    if not is_number(vTolerance) or not 0 <= vTolerance <= MAX_TOLERANCE:
        return f"tolérance attendue entre 0 et {MAX_TOLERANCE:g} %"

    return ""


def check_order(pQuestion):
    """Vérifie une remise en ordre ; retourne le défaut trouvé, ou ""."""

    vItems = pQuestion["items"]

    if not is_text_list(vItems, 3, 8) or len(set(vItems)) != len(vItems):
        return "3 à 8 éléments distincts attendus"

    return ""


def check_pairs(pQuestion):
    """Vérifie une association ; retourne le défaut trouvé, ou ""."""

    vPairs = pQuestion["pairs"]

    if (
        not isinstance(vPairs, list)
        or not 3 <= len(vPairs) <= 6
        or not all(is_text_list(vPair, 2, 2) for vPair in vPairs)
    ):
        return "3 à 6 paires [élément, correspondance] attendues"

    vRights = [vRight for _, vRight in vPairs]

    if len(set(vRights)) != len(vRights):
        return "deux paires ont la même correspondance"

    return ""


def check_completion(pQuestion):
    """Vérifie un code à compléter ; retourne le défaut trouvé, ou ""."""

    if pQuestion["code"].count(BLANK) != 1:
        return f"un seul trou {BLANK} attendu dans le code"

    if not is_text_list(pQuestion["accepted"], 1, 5):
        return "1 à 5 réponses acceptées attendues"

    return ""


def check_zones(pQuestion):
    """Vérifie une zone à désigner ; retourne le défaut trouvé, ou ""."""

    vZones = pQuestion["zones"]

    if (
        not isinstance(vZones, list)
        or not 2 <= len(vZones) <= 8
        or not all(
            isinstance(vZone, dict)
            and isinstance(vZone.get("label"), str)
            and vZone["label"].strip()
            and isinstance(vZone.get("rect"), list)
            and len(vZone["rect"]) == 4
            and all(is_number(vValue) and vValue >= 0 for vValue in vZone["rect"])
            and vZone["rect"][2] > 0
            and vZone["rect"][3] > 0
            for vZone in vZones
        )
    ):
        return "2 à 8 zones {label, rect [x, y, largeur, hauteur]} attendues"

    if (
        not isinstance(pQuestion["answer"], int)
        or isinstance(pQuestion["answer"], bool)
        or not 0 <= pQuestion["answer"] < len(vZones)
    ):
        return "réponse hors des zones"

    return ""


CHECKS = {
    "qcm": check_choices,
    "numerique": check_numeric,
    "ordre": check_order,
    "association": check_pairs,
    "saisie": check_completion,
    "zone": check_zones,
    "construction": check_construction,
}


def check_typed_fields(pQuestion):
    """Vérifie les champs propres au type ; retourne le défaut trouvé, ou ""."""

    vType = get_type(pQuestion)

    if vType not in TYPE_FIELDS:
        return f"type inconnu ({', '.join(QUESTION_TYPES)} attendu)"

    vMissing = [vField for vField in TYPE_FIELDS[vType] if vField not in pQuestion]

    if vMissing:
        return f"{', '.join(vMissing)} manquant"

    rIssue = CHECKS[vType](pQuestion)

    return rIssue


def prepare_question(pQuestion, pRandom):
    """Retourne la question prête à afficher, éléments mélangés selon son type.

    « shuffled » garde l'indice d'origine de chaque élément : choix d'un QCM,
    étapes d'un ordre, correspondances d'une association.
    """

    vType = get_type(pQuestion)

    if vType == "qcm":
        vShuffled = list(enumerate(pQuestion["choices"]))
    elif vType == "ordre":
        vShuffled = list(enumerate(pQuestion["items"]))
    elif vType == "association":
        vShuffled = list(enumerate(vRight for _, vRight in pQuestion["pairs"]))
    elif vType == "construction":
        # Palette : un bouton par type, attendu ou leurre, dans le désordre
        vShuffled = list(get_palette_limits(pQuestion))
    else:
        vShuffled = []

    pRandom.shuffle(vShuffled)

    # Une remise en ordre déjà dans l'ordre n'aurait rien à faire.
    if vType == "ordre" and [vIndex for vIndex, _ in vShuffled] == sorted(
        vIndex for vIndex, _ in vShuffled
    ):
        vShuffled.reverse()

    rQuestion = {
        **pQuestion,
        "type": vType,
        "type_label": TYPE_LABELS[vType],
        "shuffled": vShuffled,
    }

    if vType == "construction":
        rQuestion["palette_limits"] = get_palette_limits(pQuestion)

    return rQuestion


def format_number(pValue):
    """Écrit un nombre à la française, sans zéros inutiles."""

    rText = f"{pValue:.6g}".replace(".", ",")

    return rText


def parse_number(pText, pUnit):
    """Lit une valeur saisie, avec ou sans unité ; lève ValueError si illisible.

    Un préfixe usuel est converti : « 2,3 mA » vaut 0,0023 si l'unité est A.
    """

    vExample = f"par exemple 2,5 {pUnit}".rstrip()
    vMatch = NUMBER_PATTERN.fullmatch(str(pText or "").strip())

    if vMatch is None:
        raise ValueError(f"Nombre attendu, {vExample}.")

    vValue = float(vMatch[1].replace(",", "."))
    vSuffix = vMatch[2]

    if not vSuffix or vSuffix == pUnit:
        return vValue

    if pUnit and vSuffix[1:] == pUnit and vSuffix[0] in UNIT_PREFIXES:
        return vValue * UNIT_PREFIXES[vSuffix[0]]

    raise ValueError(
        f"Unité attendue : {pUnit}, {vExample}."
        if pUnit
        else "Nombre sans unité attendu."
    )


def check_indexes(pResponse, pCount):
    """Vérifie une liste d'indices compris entre 0 et pCount - 1."""

    if (
        not isinstance(pResponse, (list, tuple))
        or len(pResponse) != pCount
        or not all(
            isinstance(vIndex, int) and not isinstance(vIndex, bool)
            for vIndex in pResponse
        )
        or not all(0 <= vIndex < pCount for vIndex in pResponse)
    ):
        raise ValueError("Réponse incomplète.")


def grade_choice(pQuestion, pResponse):
    """Corrige un QCM : pResponse est l'indice d'origine du choix."""

    if (
        not isinstance(pResponse, int)
        or isinstance(pResponse, bool)
        or not 0 <= pResponse < len(pQuestion["choices"])
    ):
        raise ValueError("Question ou réponse inconnue.")

    rGrade = (
        pResponse == pQuestion["answer"],
        pQuestion["choices"][pResponse],
        pQuestion["choices"][pQuestion["answer"]],
    )

    return rGrade


def grade_numeric(pQuestion, pResponse):
    """Corrige un calcul : la valeur saisie doit tomber dans la tolérance."""

    vUnit = pQuestion.get("unit", "")
    vExpected = pQuestion["value"]
    vValue = parse_number(pResponse, vUnit)
    vTolerance = pQuestion.get("tolerance", DEFAULT_TOLERANCE)
    vMargin = max(abs(vExpected) * vTolerance / 100, 1e-12)

    rGrade = (
        abs(vValue - vExpected) <= vMargin,
        str(pResponse).strip(),
        f"{format_number(vExpected)} {vUnit}".rstrip(),
    )

    return rGrade


def grade_order(pQuestion, pResponse):
    """Corrige une remise en ordre : pResponse liste les indices d'origine."""

    vItems = pQuestion["items"]
    check_indexes(pResponse, len(vItems))

    if len(set(pResponse)) != len(vItems):
        raise ValueError("Chaque élément doit avoir sa propre place.")

    rGrade = (
        list(pResponse) == list(range(len(vItems))),
        " → ".join(vItems[vIndex] for vIndex in pResponse),
        " → ".join(vItems),
    )

    return rGrade


def grade_pairs(pQuestion, pResponse):
    """Corrige une association : pResponse donne, pour chaque élément, sa correspondance."""

    vPairs = pQuestion["pairs"]
    check_indexes(pResponse, len(vPairs))

    rGrade = (
        list(pResponse) == list(range(len(vPairs))),
        " ; ".join(
            f"{vLeft} → {vPairs[vIndex][1]}"
            for (vLeft, _), vIndex in zip(vPairs, pResponse)
        ),
        " ; ".join(f"{vLeft} → {vRight}" for vLeft, vRight in vPairs),
    )

    return rGrade


def normalize_code(pText):
    """Retourne un extrait comparable : espaces de début, de fin et répétés ignorés."""

    rText = " ".join(str(pText).split())

    return rText


def grade_completion(pQuestion, pResponse):
    """Corrige un code à compléter ; la casse compte, comme dans un programme."""

    vAnswer = str(pResponse or "").strip()

    if not vAnswer:
        raise ValueError("Saisissez une réponse.")

    vAnswer = vAnswer[:MAX_TEXT_ANSWER_LENGTH]

    rGrade = (
        normalize_code(vAnswer)
        in {normalize_code(vAccepted) for vAccepted in pQuestion["accepted"]},
        vAnswer,
        pQuestion["accepted"][0],
    )

    return rGrade


def find_zone(pZones, pX, pY):
    """Retourne l'indice de la zone qui contient le point, ou None."""

    rIndex = next(
        (
            vIndex
            for vIndex, vZone in enumerate(pZones)
            if vZone["rect"][0] <= pX <= vZone["rect"][0] + vZone["rect"][2]
            and vZone["rect"][1] <= pY <= vZone["rect"][1] + vZone["rect"][3]
        ),
        None,
    )

    return rIndex


def grade_zone(pQuestion, pResponse):
    """Corrige une zone à désigner : pResponse est le point cliqué [x, y]."""

    if (
        not isinstance(pResponse, (list, tuple))
        or len(pResponse) != 2
        or not all(is_number(vValue) for vValue in pResponse)
    ):
        raise ValueError("Cliquez sur le schéma pour répondre.")

    vZones = pQuestion["zones"]
    vIndex = find_zone(vZones, *pResponse)

    rGrade = (
        vIndex == pQuestion["answer"],
        OUTSIDE_ZONES if vIndex is None else vZones[vIndex]["label"],
        vZones[pQuestion["answer"]]["label"],
    )

    return rGrade


def parse_schema(pText):
    """Lit le schéma envoyé en JSON par l'éditeur web ; lève ValueError si illisible."""

    vText = str(pText or "")

    if not vText.strip():
        raise ValueError("Placez au moins un composant.")

    if len(vText) > MAX_SCHEMA_LENGTH:
        raise ValueError("Schéma trop grand.")

    try:
        rSchema = json.loads(vText)

    except ValueError:
        raise ValueError("Schéma illisible.") from None

    return rSchema


def build_response(pQuestion, pChoice, pText, pIndexes, pPoint=None):
    """Retourne, parmi les champs d'un formulaire, la réponse attendue par le type."""

    vType = get_type(pQuestion)

    if vType == "qcm":
        rResponse = pChoice
    elif vType in ("numerique", "saisie"):
        rResponse = pText
    elif vType == "zone":
        rResponse = list(pPoint) if pPoint else None
    elif vType == "construction":
        rResponse = parse_schema(pText)
    else:
        rResponse = list(pIndexes)

    return rResponse


GRADERS = {
    "qcm": grade_choice,
    "numerique": grade_numeric,
    "ordre": grade_order,
    "association": grade_pairs,
    "saisie": grade_completion,
    "zone": grade_zone,
    "construction": grade_construction,
}


def grade_answer(pQuestion, pResponse):
    """Corrige une réponse ; retourne (juste, réponse donnée, réponse attendue).

    Lève ValueError si la réponse est illisible : elle n'est pas comptée.
    """

    rGrade = GRADERS[get_type(pQuestion)](pQuestion, pResponse)

    return rGrade
