"""Types de questions de révision : vérification, présentation et correction

Chaque type a ses propres champs et sa propre forme de réponse : l'indice d'un
choix pour un QCM, un texte pour une valeur ou un code à compléter, une liste
d'indices pour un ordre ou une association. Le reste de la révision (tirage,
progression, examen) ne dépend pas du type.
"""

import math
import re

DEFAULT_TYPE = "qcm"

TYPE_FIELDS = {
    "qcm": ("choices", "answer"),
    "numerique": ("value",),
    "ordre": ("items",),
    "association": ("pairs",),
    "saisie": ("code", "accepted"),
}
OPTIONAL_FIELDS = ("code", "unit", "tolerance")
QUESTION_TYPES = tuple(TYPE_FIELDS)

TYPE_LABELS = {
    "qcm": "QCM",
    "numerique": "Calcul",
    "ordre": "Remise en ordre",
    "association": "Association",
    "saisie": "Code à compléter",
}

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


CHECKS = {
    "qcm": check_choices,
    "numerique": check_numeric,
    "ordre": check_order,
    "association": check_pairs,
    "saisie": check_completion,
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


def build_response(pQuestion, pChoice, pText, pIndexes):
    """Retourne, parmi les champs d'un formulaire, la réponse attendue par le type."""

    vType = get_type(pQuestion)

    if vType == "qcm":
        rResponse = pChoice
    elif vType in ("numerique", "saisie"):
        rResponse = pText
    else:
        rResponse = list(pIndexes)

    return rResponse


GRADERS = {
    "qcm": grade_choice,
    "numerique": grade_numeric,
    "ordre": grade_order,
    "association": grade_pairs,
    "saisie": grade_completion,
}


def grade_answer(pQuestion, pResponse):
    """Corrige une réponse ; retourne (juste, réponse donnée, réponse attendue).

    Lève ValueError si la réponse est illisible : elle n'est pas comptée.
    """

    rGrade = GRADERS[get_type(pQuestion)](pQuestion, pResponse)

    return rGrade
