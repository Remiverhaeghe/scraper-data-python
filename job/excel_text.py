"""Fonctions de texte d'Excel en français"""

import re

from job.excel_values import (
    DATE_FORMAT_PATTERN,
    NUM,
    Range,
    VALUE,
    fold,
    format_date,
    format_fixed,
    is_error,
    scalar,
    serial_to_date,
    to_integer,
    to_number,
    to_text,
)


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


NUMBER_FORMAT_PATTERN = re.compile(r"0(?:,(0+))?")


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
