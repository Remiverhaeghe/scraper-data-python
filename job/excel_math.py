"""Fonctions numériques d'Excel en français : agrégats et arrondis"""

import math

from job.excel_values import (
    DIV0,
    Range,
    VALUE,
    add_all,
    check_number,
    is_error,
    is_number,
    round_with,
    to_number,
)


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
