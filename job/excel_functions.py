"""Fonctions d'Excel en français : agrégats, conditions, recherches, textes, dates

Chaque fonction reçoit ses arguments déjà calculés : une valeur simple ou une
plage (Range). Les arguments absents gardent la valeur par défaut d'Excel.
"""

import math
import re
from datetime import date, timedelta

from job.excel_values import (
    DATE_FORMAT_PATTERN,
    DIV0,
    FIRST_SERIAL,
    LAST_SERIAL,
    NA,
    NUM,
    REF,
    Range,
    TEXT_NUMBER_PATTERN,
    VALUE,
    add_all,
    check_number,
    compare,
    date_to_serial,
    fold,
    format_date,
    format_fixed,
    is_error,
    is_number,
    read_date,
    round_with,
    scalar,
    serial_to_date,
    to_bool,
    to_integer,
    to_number,
    to_text,
    type_rank,
)

# Date du jour de la feuille, comme dans le bac à sable SQL : AUJOURDHUI() est stable
TODAY = "2026-06-30"

CRITERION_PATTERN = re.compile(r"(<=|>=|<>|<|>|=)?(.*)", re.S)
NUMBER_FORMAT_PATTERN = re.compile(r"0(?:,(0+))?")


def flatten_numbers(pArguments):
    """Retourne les nombres des arguments, ou la première erreur rencontrée.

    Comme dans Excel, une plage ne compte que ses nombres ; une valeur écrite
    directement est convertie (VRAI vaut 1, « 3 » vaut 3).
    """

    rNumbers = []

    for vArgument in pArguments:
        if isinstance(vArgument, Range):
            for vValue in vArgument.values():
                if is_error(vValue):
                    return vValue

                if is_number(vValue):
                    rNumbers.append(vValue)

            continue

        if vArgument is None:
            continue

        vNumber = to_number(vArgument)

        if is_error(vNumber):
            return vNumber

        rNumbers.append(vNumber)

    return rNumbers


def numeric_function(pCompute):
    """Fabrique une fonction d'agrégat : SOMME, MOYENNE, MIN, MAX."""

    def compute(*pArguments):
        vNumbers = flatten_numbers(pArguments)

        if is_error(vNumbers):
            return vNumbers

        rValue = pCompute(vNumbers)

        return rValue

    return compute


def excel_sum(*pArguments):
    """SOMME : total des nombres."""

    return numeric_function(lambda pNumbers: check_number(add_all(pNumbers)))(
        *pArguments
    )


def excel_average(*pArguments):
    """MOYENNE : moyenne des nombres, #DIV/0! sans aucun nombre."""

    return numeric_function(
        lambda pNumbers: (
            check_number(add_all(pNumbers) / len(pNumbers)) if pNumbers else DIV0
        )
    )(*pArguments)


def excel_min(*pArguments):
    """MIN : plus petit nombre, 0 sans aucun nombre."""

    return numeric_function(lambda pNumbers: min(pNumbers) if pNumbers else 0.0)(
        *pArguments
    )


def excel_max(*pArguments):
    """MAX : plus grand nombre, 0 sans aucun nombre."""

    return numeric_function(lambda pNumbers: max(pNumbers) if pNumbers else 0.0)(
        *pArguments
    )


def excel_count(*pArguments):
    """NB : nombres des plages, et valeurs directes convertibles en nombre."""

    rCount = 0.0

    for vArgument in pArguments:
        if isinstance(vArgument, Range):
            rCount += sum(1 for vValue in vArgument.values() if is_number(vValue))

        elif vArgument is not None and not is_error(to_number(vArgument)):
            rCount += 1

    return rCount


def excel_count_values(*pArguments):
    """NBVAL : cellules non vides, erreurs comprises."""

    rCount = 0.0

    for vArgument in pArguments:
        if isinstance(vArgument, Range):
            rCount += sum(1 for vValue in vArgument.values() if vValue is not None)

        elif vArgument is not None:
            rCount += 1

    return rCount


def excel_count_blank(pRange):
    """NB.VIDE : cellules vides ou contenant un texte vide."""

    if not isinstance(pRange, Range):
        return VALUE

    rCount = float(sum(1 for vValue in pRange.values() if vValue in (None, "")))

    return rCount


def excel_if(pCondition, pThen=True, pElse=False):
    """SI : sans troisième argument, FAUX quand la condition est fausse."""

    vCondition = to_bool(pCondition)

    if is_error(vCondition):
        return vCondition

    rValue = pThen if vCondition else pElse

    return rValue


def excel_ifs(*pArguments):
    """SI.CONDITIONS : première condition vraie ; aucune : #N/A."""

    if len(pArguments) % 2:
        return VALUE

    for vIndex in range(0, len(pArguments), 2):
        vCondition = to_bool(pArguments[vIndex])

        if is_error(vCondition):
            return vCondition

        if vCondition:
            return pArguments[vIndex + 1]

    return NA


def logical_function(pAll):
    """Fabrique ET (pAll vrai) ou OU, plages comprises."""

    def compute(*pArguments):
        vValues = []

        for vArgument in pArguments:
            if isinstance(vArgument, Range):
                vValues += [
                    vValue
                    for vValue in vArgument.values()
                    if isinstance(vValue, bool) or is_number(vValue) or is_error(vValue)
                ]

            elif vArgument is not None:
                vValues.append(vArgument)

        vBooleans = []

        for vValue in vValues:
            vBoolean = to_bool(vValue)

            if is_error(vBoolean):
                return vBoolean

            vBooleans.append(vBoolean)

        if not vBooleans:
            return VALUE

        rValue = all(vBooleans) if pAll else any(vBooleans)

        return rValue

    return compute


def excel_not(pValue):
    """NON : inverse une valeur logique."""

    vBoolean = to_bool(pValue)

    rValue = vBoolean if is_error(vBoolean) else not vBoolean

    return rValue


def excel_if_error(pValue, pFallback):
    """SIERREUR : valeur de repli quand la première est une erreur."""

    vValue = scalar(pValue)

    rValue = pFallback if is_error(vValue) else pValue

    return rValue


def wildcard_pattern(pText):
    """Retourne l'expression d'un critère à jokers : * et ?, ~ pour les échapper."""

    vParts = []
    vIndex = 0

    while vIndex < len(pText):
        vChar = pText[vIndex]

        if vChar == "~" and vIndex + 1 < len(pText) and pText[vIndex + 1] in "*?~":
            vParts.append(re.escape(pText[vIndex + 1]))
            vIndex += 2
            continue

        vParts.append({"*": ".*", "?": "."}.get(vChar, re.escape(vChar)))
        vIndex += 1

    rPattern = re.compile("".join(vParts), re.S)

    return rPattern


def text_matches(pValue, pText):
    """Égalité de textes sans casse, avec les jokers d'Excel."""

    rMatch = wildcard_pattern(fold(pText)).fullmatch(fold(pValue)) is not None

    return rMatch


def build_criterion(pCriterion):
    """Retourne (opérateur, valeur) d'un critère comme « >=10 » ou « Tour* »."""

    pCriterion = scalar(pCriterion)

    if not isinstance(pCriterion, str):
        return ("=", 0.0 if pCriterion is None else pCriterion)

    vMatch = CRITERION_PATTERN.fullmatch(pCriterion)
    vOperator = vMatch.group(1) or "="
    vText = vMatch.group(2)
    vNumber = TEXT_NUMBER_PATTERN.fullmatch(vText)

    if vNumber:
        return (vOperator, float(vNumber.group(1).replace(",", ".")))

    if vText.upper() in ("VRAI", "FAUX"):
        return (vOperator, vText.upper() == "VRAI")

    rCriterion = (vOperator, vText)

    return rCriterion


def matches(pValue, pCriterion):
    """Indique si une valeur de plage satisfait un critère de NB.SI ou SOMME.SI."""

    vOperator, vTarget = pCriterion

    if is_error(pValue) or is_error(vTarget):
        return False

    if vTarget == "" and vOperator in ("=", "<>"):
        vBlank = pValue is None or pValue == ""

        return vBlank if vOperator == "=" else not vBlank

    if isinstance(vTarget, str) and vOperator in ("=", "<>"):
        vEqual = isinstance(pValue, str) and text_matches(pValue, vTarget)

        return vEqual if vOperator == "=" else not vEqual

    if pValue is None or type_rank(pValue) != type_rank(vTarget):
        return vOperator == "<>"

    vOrder = compare(pValue, vTarget)

    rMatch = {
        "=": vOrder == 0,
        "<>": vOrder != 0,
        "<": vOrder < 0,
        ">": vOrder > 0,
        "<=": vOrder <= 0,
        ">=": vOrder >= 0,
    }[vOperator]

    return rMatch


def criteria_mask(pPairs):
    """Retourne, cellule par cellule, si tous les critères sont remplis."""

    vFirst = pPairs[0][0]
    rMask = None

    for vRange, vCriterion in pPairs:
        if not isinstance(vRange, Range):
            return VALUE

        if (vRange.height, vRange.width) != (vFirst.height, vFirst.width):
            return VALUE

        vCriterion = build_criterion(vCriterion)
        vMask = [matches(vValue, vCriterion) for vValue in vRange.values()]
        rMask = (
            vMask
            if rMask is None
            else [vLeft and vRight for vLeft, vRight in zip(rMask, vMask)]
        )

    return rMask


def resize(pRange, pModel):
    """Retourne la plage de même taille que pModel, depuis le coin de pRange."""

    rRange = Range(
        pRange.sheet,
        pRange.top,
        pRange.left,
        pRange.top + pModel.height - 1,
        pRange.left + pModel.width - 1,
    )

    return rRange


def pick_numbers(pRange, pMask):
    """Retourne les nombres retenus par le masque, ou la première erreur."""

    rNumbers = []

    for vValue, vKeep in zip(pRange.values(), pMask):
        if not vKeep:
            continue

        if is_error(vValue):
            return vValue

        if is_number(vValue):
            rNumbers.append(vValue)

    return rNumbers


def excel_count_if(pRange, pCriterion):
    """NB.SI : cellules qui répondent au critère."""

    return excel_count_ifs(pRange, pCriterion)


def excel_count_ifs(*pArguments):
    """NB.SI.ENS : cellules qui répondent à tous les critères."""

    if len(pArguments) % 2:
        return VALUE

    vMask = criteria_mask(list(zip(pArguments[::2], pArguments[1::2])))

    rCount = vMask if is_error(vMask) else float(sum(vMask))

    return rCount


def conditional_numbers(pValues, pPairs):
    """Retourne les nombres de pValues retenus par les critères."""

    if not isinstance(pValues, Range) or not isinstance(pPairs[0][0], Range):
        return VALUE

    vMask = criteria_mask(pPairs)

    if is_error(vMask):
        return vMask

    rNumbers = pick_numbers(pValues, vMask)

    return rNumbers


def excel_sum_if(pRange, pCriterion, pSumRange=None):
    """SOMME.SI : total des cellules retenues par le critère."""

    vSumRange = pRange if pSumRange is None else pSumRange

    if isinstance(vSumRange, Range) and isinstance(pRange, Range):
        vSumRange = resize(vSumRange, pRange)

    vNumbers = conditional_numbers(vSumRange, [(pRange, pCriterion)])

    rValue = vNumbers if is_error(vNumbers) else check_number(add_all(vNumbers))

    return rValue


def excel_average_if(pRange, pCriterion, pAverageRange=None):
    """MOYENNE.SI : moyenne des cellules retenues par le critère."""

    vAverageRange = pRange if pAverageRange is None else pAverageRange

    if isinstance(vAverageRange, Range) and isinstance(pRange, Range):
        vAverageRange = resize(vAverageRange, pRange)

    vNumbers = conditional_numbers(vAverageRange, [(pRange, pCriterion)])

    if is_error(vNumbers):
        return vNumbers

    rValue = check_number(add_all(vNumbers) / len(vNumbers)) if vNumbers else DIV0

    return rValue


def excel_sum_ifs(pSumRange, *pArguments):
    """SOMME.SI.ENS : total des cellules retenues par tous les critères."""

    if not pArguments or len(pArguments) % 2:
        return VALUE

    vPairs = list(zip(pArguments[::2], pArguments[1::2]))

    if isinstance(pSumRange, Range) and isinstance(vPairs[0][0], Range):
        if (pSumRange.height, pSumRange.width) != (
            vPairs[0][0].height,
            vPairs[0][0].width,
        ):
            return VALUE

    vNumbers = conditional_numbers(pSumRange, vPairs)

    rValue = vNumbers if is_error(vNumbers) else check_number(add_all(vNumbers))

    return rValue


def excel_sum_product(*pArguments):
    """SOMMEPROD : plages de même taille, ce qui n'est pas un nombre vaut 0."""

    vRanges = [vArgument for vArgument in pArguments if isinstance(vArgument, Range)]

    if len(vRanges) != len(pArguments):
        return VALUE

    if any(
        (vRange.height, vRange.width) != (vRanges[0].height, vRanges[0].width)
        for vRange in vRanges
    ):
        return VALUE

    vProducts = []

    for vValues in zip(*(vRange.values() for vRange in vRanges)):
        vProduct = 1.0

        for vValue in vValues:
            if is_error(vValue):
                return vValue

            vProduct *= vValue if is_number(vValue) else 0.0

        vProducts.append(vProduct)

    rValue = check_number(add_all(vProducts))

    return rValue


def lookup_equal(pValue, pKey, pWildcards):
    """Égalité d'une recherche exacte, jokers permis pour un texte cherché."""

    if pKey is None or is_error(pKey):
        return False

    if isinstance(pValue, str) and isinstance(pKey, str) and pWildcards:
        return text_matches(pKey, pValue)

    rEqual = type_rank(pValue) == type_rank(pKey) and compare(pValue, pKey) == 0

    return rEqual


def find_position(pValue, pKeys, pMode, pWildcards):
    """Retourne l'indice trouvé dans pKeys, ou None.

    pMode 0 : égalité ; 1 : plus grande valeur inférieure ou égale, sur des clés
    triées en ordre croissant ; -1 : plus petite valeur supérieure ou égale, sur
    des clés triées en ordre décroissant (EQUIV) ou quelconque (RECHERCHEX).
    """

    if pMode == 0:
        return next(
            (
                vIndex
                for vIndex, vKey in enumerate(pKeys)
                if lookup_equal(pValue, vKey, pWildcards)
            ),
            None,
        )

    rIndex = None

    for vIndex, vKey in enumerate(pKeys):
        if vKey is None or is_error(vKey) or type_rank(vKey) != type_rank(pValue):
            continue

        vOrder = compare(vKey, pValue)

        if vOrder == 0:
            return vIndex

        if (vOrder < 0) == (pMode == 1):
            rIndex = vIndex

        else:
            break

    return rIndex


def excel_vlookup(pValue, pTable, pColumn, pApproximate=True):
    """RECHERCHEV : approchée par défaut, exacte avec FAUX ou 0."""

    vValue = scalar(pValue)
    vColumn = to_integer(pColumn)
    vApproximate = to_bool(pApproximate)

    for vItem in (vValue, vColumn, vApproximate):
        if is_error(vItem):
            return vItem

    if not isinstance(pTable, Range) or vColumn < 1:
        return VALUE

    if vColumn > pTable.width:
        return REF

    vKeys = [pTable.cell(vRow, 0) for vRow in range(pTable.height)]
    vIndex = find_position(vValue, vKeys, 1 if vApproximate else 0, True)

    rValue = NA if vIndex is None else pTable.cell(vIndex, vColumn - 1)

    return rValue


def line_values(pRange):
    """Retourne les valeurs d'une ligne ou d'une colonne ; None si 2D."""

    if not isinstance(pRange, Range) or (pRange.height > 1 and pRange.width > 1):
        return None

    rValues = pRange.values()

    return rValues


def excel_xlookup(pValue, pLookup, pReturn, pNotFound=None, pMode=0.0):
    """RECHERCHEX : exacte par défaut, valeur de repli au lieu de #N/A."""

    vValue = scalar(pValue)
    vMode = to_integer(pMode)

    for vItem in (vValue, vMode):
        if is_error(vItem):
            return vItem

    vKeys = line_values(pLookup)
    vResults = line_values(pReturn)

    if vKeys is None or vResults is None or len(vKeys) != len(vResults):
        return VALUE

    if vMode not in (-1, 0, 1, 2):
        return VALUE

    vIndex = find_position(vValue, vKeys, 0, vMode == 2)

    if vIndex is None and vMode in (-1, 1):
        vIndex = nearest_position(vValue, vKeys, vMode)

    if vIndex is None:
        return NA if pNotFound is None else pNotFound

    rValue = vResults[vIndex]

    return rValue


def nearest_position(pValue, pKeys, pMode):
    """Retourne l'indice de la valeur voisine : juste en dessous (-1) ou au-dessus (1)."""

    rIndex = None

    for vIndex, vKey in enumerate(pKeys):
        if vKey is None or is_error(vKey) or type_rank(vKey) != type_rank(pValue):
            continue

        vOrder = compare(vKey, pValue)

        if vOrder * pMode <= 0:
            continue

        if rIndex is None or compare(vKey, pKeys[rIndex]) * pMode < 0:
            rIndex = vIndex

    return rIndex


def excel_match(pValue, pRange, pType=1.0):
    """EQUIV : position à partir de 1, exacte avec 0."""

    vValue = scalar(pValue)
    vType = to_integer(pType)

    for vItem in (vValue, vType):
        if is_error(vItem):
            return vItem

    vKeys = line_values(pRange)

    if vKeys is None:
        return NA

    vMode = 0 if vType == 0 else (1 if vType > 0 else -1)
    vIndex = find_position(vValue, vKeys, vMode, True)

    rValue = NA if vIndex is None else float(vIndex + 1)

    return rValue


def excel_index(pRange, pRow, pColumn=None):
    """INDEX : cellule de la plage, ligne et colonne comptées depuis 1."""

    if not isinstance(pRange, Range):
        return VALUE

    vRow = to_integer(pRow)
    vColumn = 1 if pColumn is None else to_integer(pColumn)

    for vItem in (vRow, vColumn):
        if is_error(vItem):
            return vItem

    if pColumn is None and pRange.height == 1:
        vRow, vColumn = 1, vRow

    if vRow < 1 or vColumn < 1:
        return VALUE

    if vRow > pRange.height or vColumn > pRange.width:
        return REF

    vTop = pRange.top + vRow - 1
    vLeft = pRange.left + vColumn - 1

    rRange = Range(pRange.sheet, vTop, vLeft, vTop, vLeft)

    return rRange


def excel_round(pValue, pDigits):
    """ARRONDI : au plus proche, la moitié s'éloignant de zéro."""

    return round_with(pValue, pDigits, 0)


def excel_round_up(pValue, pDigits):
    """ARRONDI.SUP : en s'éloignant de zéro."""

    return round_with(pValue, pDigits, 1)


def excel_round_down(pValue, pDigits):
    """ARRONDI.INF : en se rapprochant de zéro."""

    return round_with(pValue, pDigits, -1)


def excel_int(pValue):
    """ENT : entier inférieur ou égal."""

    vValue = to_number(pValue)

    rValue = vValue if is_error(vValue) else float(math.floor(vValue))

    return rValue


def excel_abs(pValue):
    """ABS : valeur absolue."""

    vValue = to_number(pValue)

    rValue = vValue if is_error(vValue) else abs(vValue)

    return rValue


def excel_mod(pValue, pDivisor):
    """MOD : le reste a le signe du diviseur, comme dans Excel."""

    vValue = to_number(pValue)
    vDivisor = to_number(pDivisor)

    for vItem in (vValue, vDivisor):
        if is_error(vItem):
            return vItem

    if vDivisor == 0:
        return DIV0

    rValue = check_number(vValue - vDivisor * math.floor(vValue / vDivisor))

    return rValue


def text_arguments(pFunction):
    """Fabrique une fonction de texte : arguments convertis, erreurs propagées."""

    def compute(*pArguments):
        vValues = [scalar(vArgument) for vArgument in pArguments]

        for vValue in vValues:
            if is_error(vValue):
                return vValue

        rValue = pFunction(*vValues)

        return rValue

    return compute


def text_count(pValue, pDefault):
    """Retourne un nombre de caractères positif, ou #VALEUR!."""

    vCount = pDefault if pValue is None else to_integer(pValue)

    rCount = VALUE if is_error(vCount) or vCount < 0 else vCount

    return rCount


def left_text(pText, pCount=None):
    """GAUCHE : premiers caractères d'un texte."""

    vCount = text_count(pCount, 1)

    rValue = vCount if is_error(vCount) else to_text(pText)[:vCount]

    return rValue


def right_text(pText, pCount=None):
    """DROITE : derniers caractères d'un texte."""

    vCount = text_count(pCount, 1)
    vText = to_text(pText)

    rValue = (
        vCount if is_error(vCount) else vText[len(vText) - min(vCount, len(vText)) :]
    )

    return rValue


def mid_text(pText, pStart, pCount):
    """STXT : caractères pris au milieu d'un texte."""

    vStart = to_integer(pStart)
    vCount = text_count(pCount, 0)

    for vItem in (vStart, vCount):
        if is_error(vItem):
            return vItem

    if vStart < 1:
        return VALUE

    rValue = to_text(pText)[vStart - 1 : vStart - 1 + vCount]

    return rValue


def find_text(pNeedle, pText, pStart, pIgnoreCase):
    """Position de pNeedle dans pText à partir de 1 ; absent : #VALEUR!."""

    vStart = 1 if pStart is None else to_integer(pStart)

    if is_error(vStart):
        return vStart

    vNeedle = to_text(pNeedle)
    vText = to_text(pText)

    if vStart < 1 or vStart > len(vText) + 1:
        return VALUE

    if pIgnoreCase:
        vNeedle = fold(vNeedle)
        vText = fold(vText)

    vIndex = vText.find(vNeedle, vStart - 1)

    rValue = VALUE if vIndex < 0 else float(vIndex + 1)

    return rValue


def substitute_text(pText, pOld, pNew):
    """SUBSTITUE : remplace chaque occurrence d'un texte."""

    vOld = to_text(pOld)

    rValue = to_text(pText).replace(vOld, to_text(pNew)) if vOld else to_text(pText)

    return rValue


def trim_text(pText):
    """SUPPRESPACE : espaces de début et de fin retirés, une seule entre les mots."""

    rText = " ".join(vWord for vWord in to_text(pText).split(" ") if vWord)

    return rText


def excel_concat(*pArguments):
    """CONCAT : textes bout à bout, plages comprises."""

    vParts = []

    for vArgument in pArguments:
        vValues = vArgument.values() if isinstance(vArgument, Range) else [vArgument]

        for vValue in vValues:
            if is_error(vValue):
                return vValue

            vParts.append(to_text(vValue))

    rText = "".join(vParts)

    return rText


def date_function(pFunction):
    """Fabrique une fonction qui lit une date : ANNEE, MOIS, JOUR…"""

    def compute(pValue, *pArguments):
        vDate = read_date(pValue)

        if is_error(vDate):
            return vDate

        rValue = pFunction(vDate, *pArguments)

        return rValue

    return compute


def build_date(pYear, pMonth, pDay):
    """DATE : mois et jours en trop reportés, années 0 à 1899 décalées de 1900."""

    vParts = [to_integer(vValue) for vValue in (pYear, pMonth, pDay)]

    for vItem in vParts:
        if is_error(vItem):
            return vItem

    vYear, vMonth, vDay = vParts

    if vYear < 1900:
        vYear += 1900

    vYear += (vMonth - 1) // 12
    vMonth = (vMonth - 1) % 12 + 1

    if vYear < 1900 or vYear > 9999:
        return NUM

    vSerial = date_to_serial(date(vYear, vMonth, 1)) + vDay - 1

    rValue = vSerial if FIRST_SERIAL <= vSerial <= LAST_SERIAL else NUM

    return rValue


def add_months(pDate, pMonths, pEndOfMonth):
    """Retourne la date décalée de pMonths mois, ou la fin de ce mois."""

    vIndex = pDate.year * 12 + pDate.month - 1 + pMonths
    vYear, vMonth = divmod(vIndex, 12)
    vMonth += 1

    if vYear < 1900 or vYear > 9999:
        return NUM

    vNext = date(vYear + 1, 1, 1) if vMonth == 12 else date(vYear, vMonth + 1, 1)
    vLastDay = (vNext - timedelta(days=1)).day
    vDay = vLastDay if pEndOfMonth else min(pDate.day, vLastDay)

    vSerial = date_to_serial(date(vYear, vMonth, vDay))

    rValue = vSerial if vSerial >= FIRST_SERIAL else NUM

    return rValue


def month_shift(pEndOfMonth):
    """Fabrique MOIS.DECALER ou FIN.MOIS."""

    def compute(pDate, pMonths):
        vMonths = to_integer(pMonths)

        if is_error(vMonths):
            return vMonths

        rValue = add_months(pDate, vMonths, pEndOfMonth)

        return rValue

    return date_function(compute)


def date_difference(pStart, pEnd, pUnit):
    """DATEDIF : jours (« d »), mois (« m ») ou années (« y ») entiers écoulés."""

    vStart = read_date(pStart)
    vEnd = read_date(pEnd)
    vUnit = scalar(pUnit)

    for vItem in (vStart, vEnd, vUnit):
        if is_error(vItem):
            return vItem

    vUnit = to_text(vUnit).upper()

    if vStart > vEnd or vUnit not in ("D", "M", "Y"):
        return NUM

    if vUnit == "D":
        return float((vEnd - vStart).days)

    vMonths = (vEnd.year - vStart.year) * 12 + vEnd.month - vStart.month

    if vEnd.day < vStart.day:
        vMonths -= 1

    rValue = float(vMonths if vUnit == "M" else vMonths // 12)

    return rValue


def week_day(pDate, pType=None):
    """JOURSEM : type 1 dimanche = 1, type 2 lundi = 1, type 3 lundi = 0."""

    vType = 1 if pType is None else to_integer(pType)

    if is_error(vType):
        return vType

    vWeekday = pDate.weekday()

    if vType == 1:
        return float((vWeekday + 1) % 7 + 1)

    if vType == 2:
        return float(vWeekday + 1)

    rValue = float(vWeekday) if vType == 3 else NUM

    return rValue


def count_weekdays(pStart, pEnd):
    """Compte les jours du lundi au vendredi entre deux dates incluses."""

    vDays = (pEnd - pStart).days + 1
    vWeeks, vRest = divmod(vDays, 7)
    rCount = vWeeks * 5

    for vOffset in range(vRest):
        if (pStart.weekday() + vOffset) % 7 < 5:
            rCount += 1

    return rCount


def excel_workdays(pStart, pEnd, pHolidays=None):
    """NB.JOURS.OUVRES : jours ouvrés entre deux dates, fériés retirés."""

    vStart = read_date(pStart)
    vEnd = read_date(pEnd)

    for vItem in (vStart, vEnd):
        if is_error(vItem):
            return vItem

    vSign = 1

    if vStart > vEnd:
        vStart, vEnd, vSign = vEnd, vStart, -1

    vCount = count_weekdays(vStart, vEnd)
    vHolidays = set()

    if pHolidays is not None:
        vValues = pHolidays.values() if isinstance(pHolidays, Range) else [pHolidays]

        for vValue in vValues:
            if vValue is None:
                continue

            vDate = read_date(vValue)

            if is_error(vDate):
                return vDate

            if vStart <= vDate <= vEnd and vDate.weekday() < 5:
                vHolidays.add(vDate)

    rValue = float(vSign * (vCount - len(vHolidays)))

    return rValue


def format_text(pValue, pFormat):
    """TEXTE : formats de date et formats « 0 », « 0,00 » ; autre : #VALEUR!."""

    vFormat = to_text(pFormat)
    vNumber = to_number(pValue)

    if is_error(vNumber):
        return to_text(pValue) if isinstance(scalar(pValue), str) else vNumber

    vMatch = NUMBER_FORMAT_PATTERN.fullmatch(vFormat)

    if vMatch:
        return format_fixed(vNumber, len(vMatch.group(1) or ""))

    if DATE_FORMAT_PATTERN.search(vFormat):
        vDate = serial_to_date(vNumber)

        return NUM if vDate is None else format_date(vDate, vFormat)

    return VALUE


FUNCTIONS = {
    "SOMME": (1, 255, excel_sum),
    "MOYENNE": (1, 255, excel_average),
    "MIN": (1, 255, excel_min),
    "MAX": (1, 255, excel_max),
    "NB": (1, 255, excel_count),
    "NBVAL": (1, 255, excel_count_values),
    "NB.VIDE": (1, 1, excel_count_blank),
    "SI": (2, 3, excel_if),
    "SI.CONDITIONS": (2, 254, excel_ifs),
    "ET": (1, 255, logical_function(True)),
    "OU": (1, 255, logical_function(False)),
    "NON": (1, 1, excel_not),
    "SIERREUR": (2, 2, excel_if_error),
    "VRAI": (0, 0, lambda: True),
    "FAUX": (0, 0, lambda: False),
    "NB.SI": (2, 2, excel_count_if),
    "NB.SI.ENS": (2, 254, excel_count_ifs),
    "SOMME.SI": (2, 3, excel_sum_if),
    "SOMME.SI.ENS": (3, 255, excel_sum_ifs),
    "MOYENNE.SI": (2, 3, excel_average_if),
    "SOMMEPROD": (1, 255, excel_sum_product),
    "RECHERCHEV": (3, 4, excel_vlookup),
    "RECHERCHEX": (3, 5, excel_xlookup),
    "EQUIV": (2, 3, excel_match),
    "INDEX": (2, 3, excel_index),
    "ARRONDI": (2, 2, excel_round),
    "ARRONDI.SUP": (2, 2, excel_round_up),
    "ARRONDI.INF": (2, 2, excel_round_down),
    "ENT": (1, 1, excel_int),
    "ABS": (1, 1, excel_abs),
    "MOD": (2, 2, excel_mod),
    "CONCAT": (1, 255, excel_concat),
    "CONCATENER": (
        1,
        255,
        text_arguments(lambda *pValues: "".join(map(to_text, pValues))),
    ),
    "GAUCHE": (1, 2, text_arguments(left_text)),
    "DROITE": (1, 2, text_arguments(right_text)),
    "STXT": (3, 3, text_arguments(mid_text)),
    "NBCAR": (1, 1, text_arguments(lambda pText: float(len(to_text(pText))))),
    "MAJUSCULE": (1, 1, text_arguments(lambda pText: to_text(pText).upper())),
    "MINUSCULE": (1, 1, text_arguments(lambda pText: to_text(pText).lower())),
    "SUPPRESPACE": (1, 1, text_arguments(trim_text)),
    "TROUVE": (
        2,
        3,
        text_arguments(
            lambda pNeedle, pText, pStart=None: find_text(pNeedle, pText, pStart, False)
        ),
    ),
    "CHERCHE": (
        2,
        3,
        text_arguments(
            lambda pNeedle, pText, pStart=None: find_text(pNeedle, pText, pStart, True)
        ),
    ),
    "SUBSTITUE": (3, 3, text_arguments(substitute_text)),
    "TEXTE": (2, 2, text_arguments(format_text)),
    "CNUM": (1, 1, text_arguments(to_number)),
    "DATE": (3, 3, text_arguments(build_date)),
    "AUJOURDHUI": (0, 0, lambda: date_to_serial(date.fromisoformat(TODAY))),
    "ANNEE": (1, 1, date_function(lambda pDate: float(pDate.year))),
    "MOIS": (1, 1, date_function(lambda pDate: float(pDate.month))),
    "JOUR": (1, 1, date_function(lambda pDate: float(pDate.day))),
    "JOURSEM": (1, 2, date_function(week_day)),
    "DATEDIF": (3, 3, date_difference),
    "NB.JOURS.OUVRES": (2, 3, excel_workdays),
    "MOIS.DECALER": (2, 2, month_shift(False)),
    "FIN.MOIS": (2, 2, month_shift(True)),
}
