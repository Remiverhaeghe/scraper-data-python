"""Fonctions de recherche d'Excel en français : RECHERCHEV, RECHERCHEX, EQUIV, INDEX"""

from job.excel_conditions import text_matches
from job.excel_values import (
    NA,
    REF,
    Range,
    VALUE,
    compare,
    is_error,
    scalar,
    to_bool,
    to_integer,
    type_rank,
)


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
