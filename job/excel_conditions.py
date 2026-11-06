"""Fonctions conditionnelles d'Excel en français : SI, ET, OU et critères"""

import re

from job.excel_values import (
    DIV0,
    NA,
    Range,
    TEXT_NUMBER_PATTERN,
    VALUE,
    add_all,
    check_number,
    compare,
    fold,
    is_error,
    is_number,
    scalar,
    to_bool,
    type_rank,
)


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


CRITERION_PATTERN = re.compile(r"(<=|>=|<>|<|>|=)?(.*)", re.S)


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
