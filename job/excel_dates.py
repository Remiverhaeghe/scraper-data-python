"""Fonctions de date d'Excel en français"""

from datetime import date, timedelta

from job.excel_values import (
    FIRST_SERIAL,
    LAST_SERIAL,
    NUM,
    Range,
    date_to_serial,
    is_error,
    read_date,
    scalar,
    to_integer,
    to_text,
)

# Date du jour de la feuille, comme dans le bac à sable SQL : AUJOURDHUI() est stable
TODAY = "2026-06-30"


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
