"""Valeurs d'Excel : erreurs, plages, conversions, comparaisons, dates et formats

Les nombres sont des flottants, les dates des numéros de série comme dans
Excel (1 = 01/01/1900, calendrier de 1900), les erreurs des ExcelError qui se
propagent dans les calculs.
"""

import math
import re
from datetime import date, timedelta

# Entiers bornés : les positions et les nombres de caractères restent raisonnables
MAX_INTEGER = 1e15

MONTH_NAMES = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
DAY_NAMES = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

TEXT_NUMBER_PATTERN = re.compile(r" *(-?[0-9]+(?:,[0-9]+)?) *")
DATE_FORMAT_PATTERN = re.compile(r"jjjj|jj|j|mmmm|mm|m|aaaa|aa", re.I)
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

FIRST_SERIAL = 61
LAST_SERIAL = 2958465
EPOCH = date(1899, 12, 30)


class ExcelError:
    """Valeur d'erreur d'Excel (#N/A, #DIV/0!…), qui se propage dans les calculs."""

    __slots__ = ("code",)

    def __init__(self, pCode):
        self.code = pCode

    def __eq__(self, pOther):
        return isinstance(pOther, ExcelError) and pOther.code == self.code

    def __hash__(self):
        return hash(self.code)

    def __repr__(self):
        return self.code


NA = ExcelError("#N/A")
DIV0 = ExcelError("#DIV/0!")
VALUE = ExcelError("#VALEUR!")
REF = ExcelError("#REF!")
NUM = ExcelError("#NOMBRE!")


class Range:
    """Plage rectangulaire d'une feuille, lue cellule par cellule à la demande."""

    __slots__ = ("sheet", "top", "left", "bottom", "right")

    def __init__(self, pSheet, pTop, pLeft, pBottom, pRight):
        self.sheet = pSheet
        self.top = min(pTop, pBottom)
        self.left = min(pLeft, pRight)
        self.bottom = max(pTop, pBottom)
        self.right = max(pLeft, pRight)

    @property
    def height(self):
        """Nombre de lignes de la plage."""

        return self.bottom - self.top + 1

    @property
    def width(self):
        """Nombre de colonnes de la plage."""

        return self.right - self.left + 1

    def cell(self, pRow, pColumn):
        """Retourne la valeur d'une cellule de la plage, comptée depuis 0."""

        rValue = self.sheet.value(self.top + pRow, self.left + pColumn)

        return rValue

    def values(self):
        """Retourne les valeurs ligne par ligne, à plat."""

        rValues = [
            self.sheet.value(vRow, vColumn)
            for vRow in range(self.top, self.bottom + 1)
            for vColumn in range(self.left, self.right + 1)
        ]

        return rValues


def add_all(pNumbers):
    """Additionne de gauche à droite, comme le téléphone : mêmes arrondis."""

    rTotal = 0.0

    for vNumber in pNumbers:
        rTotal += vNumber

    return rTotal


def is_number(pValue):
    """Indique si la valeur est un nombre (un booléen n'en est pas un)."""

    return isinstance(pValue, float)


def is_error(pValue):
    """Indique si la valeur est une erreur d'Excel."""

    return isinstance(pValue, ExcelError)


def round_significant(pValue):
    """Arrondit à 15 chiffres significatifs, la précision d'Excel."""

    rValue = float(f"{pValue:.15g}") if math.isfinite(pValue) else pValue

    return rValue


def scalar(pValue):
    """Ramène une plage d'une cellule à sa valeur ; plus grande : #VALEUR!."""

    if isinstance(pValue, Range):
        if pValue.height == 1 and pValue.width == 1:
            return pValue.cell(0, 0)

        return VALUE

    return pValue


def to_number(pValue):
    """Convertit en nombre : vide = 0, VRAI = 1, texte « 12,5 » accepté."""

    pValue = scalar(pValue)

    if pValue is None:
        return 0.0

    if isinstance(pValue, bool):
        return 1.0 if pValue else 0.0

    if isinstance(pValue, str):
        vMatch = TEXT_NUMBER_PATTERN.fullmatch(pValue)

        return float(vMatch.group(1).replace(",", ".")) if vMatch else VALUE

    rValue = pValue

    return rValue


def to_text(pValue):
    """Convertit en texte : nombres au format standard, VRAI ou FAUX."""

    pValue = scalar(pValue)

    if pValue is None:
        return ""

    if isinstance(pValue, bool):
        return "VRAI" if pValue else "FAUX"

    if is_number(pValue):
        return format_number(pValue)

    rText = pValue

    return rText


def to_bool(pValue):
    """Convertit en booléen : nombre non nul, texte « VRAI » ou « FAUX »."""

    pValue = scalar(pValue)

    if pValue is None:
        return False

    if isinstance(pValue, bool) or is_error(pValue):
        return pValue

    if is_number(pValue):
        return pValue != 0

    vText = pValue.upper()

    rValue = vText == "VRAI" if vText in ("VRAI", "FAUX") else VALUE

    return rValue


def to_integer(pValue):
    """Convertit en entier tronqué, ou retourne l'erreur."""

    vNumber = to_number(pValue)

    if is_error(vNumber):
        return vNumber

    rValue = math.trunc(max(-MAX_INTEGER, min(MAX_INTEGER, vNumber)))

    return rValue


def fold(pText):
    """Retourne le texte sans casse, pour les comparaisons d'Excel."""

    return pText.lower()


def type_rank(pValue):
    """Ordre des types d'Excel : nombres, puis textes, puis booléens."""

    if isinstance(pValue, bool):
        return 2

    rRank = 1 if isinstance(pValue, str) else 0

    return rRank


def compare(pLeft, pRight):
    """Compare deux valeurs à la manière d'Excel : -1, 0 ou 1."""

    if pLeft is None:
        pLeft = blank_like(pRight)

    if pRight is None:
        pRight = blank_like(pLeft)

    vLeftRank = type_rank(pLeft)
    vRightRank = type_rank(pRight)

    if vLeftRank != vRightRank:
        return -1 if vLeftRank < vRightRank else 1

    if vLeftRank == 1:
        pLeft = fold(pLeft)
        pRight = fold(pRight)

    elif vLeftRank == 0:
        pLeft = round_significant(pLeft)
        pRight = round_significant(pRight)

    rOrder = (pLeft > pRight) - (pLeft < pRight)

    return rOrder


def blank_like(pValue):
    """Valeur d'une cellule vide comparée à pValue : 0, "" ou FAUX."""

    if isinstance(pValue, bool):
        return False

    rValue = "" if isinstance(pValue, str) else 0.0

    return rValue


def check_number(pValue):
    """Retourne le nombre, ou #NOMBRE! s'il est infini ou indéfini."""

    rValue = pValue if math.isfinite(pValue) else NUM

    return rValue


def round_with(pValue, pDigits, pMode):
    """Arrondit comme Excel : au plus proche (0), vers le haut (1), vers le bas (-1)."""

    vValue = to_number(pValue)
    vDigits = to_integer(pDigits)

    for vItem in (vValue, vDigits):
        if is_error(vItem):
            return vItem

    if abs(vDigits) > 15:
        vDigits = 15 if vDigits > 0 else -15

    vFactor = 10.0 ** abs(vDigits)
    vScaled = round_significant(
        abs(vValue) * vFactor if vDigits >= 0 else abs(vValue) / vFactor
    )

    if vScaled >= MAX_INTEGER:
        return vValue

    if pMode == 0:
        vRounded = math.floor(vScaled + 0.5)

    elif pMode > 0:
        vRounded = math.ceil(vScaled)

    else:
        vRounded = math.floor(vScaled)

    vResult = vRounded / vFactor if vDigits >= 0 else vRounded * vFactor

    rValue = check_number(math.copysign(vResult, vValue) if vResult else 0.0)

    return rValue


def serial_to_date(pSerial):
    """Retourne la date d'un numéro de série, ou None hors du calendrier géré."""

    vSerial = math.floor(pSerial)

    if vSerial < FIRST_SERIAL or vSerial > LAST_SERIAL:
        return None

    rDate = EPOCH + timedelta(days=vSerial)

    return rDate


def date_to_serial(pDate):
    """Retourne le numéro de série d'une date, à partir du 01/03/1900."""

    rSerial = float((pDate - EPOCH).days)

    return rSerial


def read_date(pValue):
    """Retourne la date d'une valeur, ou l'erreur d'Excel."""

    vNumber = to_number(pValue)

    if is_error(vNumber):
        return vNumber

    vDate = serial_to_date(vNumber)

    rDate = NUM if vDate is None else vDate

    return rDate


def format_date(pDate, pFormat):
    """Applique un format de date : jj, mm, aaaa, mmmm (mois), jjjj (jour)."""

    def replace(pMatch):
        vToken = pMatch.group().lower()

        return {
            "jjjj": DAY_NAMES[pDate.weekday()],
            "jj": f"{pDate.day:02d}",
            "j": str(pDate.day),
            "mmmm": MONTH_NAMES[pDate.month - 1],
            "mm": f"{pDate.month:02d}",
            "m": str(pDate.month),
            "aaaa": f"{pDate.year:04d}",
            "aa": f"{pDate.year % 100:02d}",
        }[vToken]

    rText = DATE_FORMAT_PATTERN.sub(replace, pFormat)

    return rText


def format_fixed(pValue, pDecimals):
    """Écrit un nombre avec pDecimals décimales et la virgule française."""

    if abs(pValue) >= MAX_INTEGER:
        return format_number(pValue)

    vRounded = round_with(pValue, float(pDecimals), 0)

    rText = f"{vRounded:.{pDecimals}f}".replace(".", ",")

    if rText.startswith("-") and not rText.strip("-0,"):
        rText = rText[1:]

    return rText


def format_number(pValue):
    """Écrit un nombre au format standard : dix chiffres significatifs au plus."""

    if pValue == 0:
        return "0"

    if not math.isfinite(pValue):
        return NUM.code

    if 1e-4 <= abs(pValue) < 1e15:
        vRounded = float(f"{pValue:.10g}")

        if vRounded == math.floor(vRounded):
            return str(int(vRounded))

        return repr(vRounded).replace(".", ",")

    vMantissa, vExponent = f"{pValue:.5e}".split("e")
    vMantissa = vMantissa.rstrip("0").rstrip(".").replace(".", ",")

    rText = f"{vMantissa}E{int(vExponent):+03d}"

    return rText


def format_value(pValue, pFormat=""):
    """Écrit une valeur comme dans la cellule : nombre, date, euros, pourcentage."""

    if pValue is None:
        return ""

    if is_error(pValue):
        return pValue.code

    if not is_number(pValue):
        return to_text(pValue)

    if pFormat == "date":
        vDate = serial_to_date(pValue)

        if vDate is not None:
            return f"{vDate.day:02d}/{vDate.month:02d}/{vDate.year:04d}"

    if pFormat == "euro":
        return f"{format_fixed(pValue, 2)} €"

    if pFormat == "percent":
        return f"{format_number(round_with(pValue * 100, 2.0, 0))} %"

    rText = format_number(pValue)

    return rText


def read_literal(pValue):
    """Retourne la valeur d'une cellule livrée en JSON : dates « aaaa-mm-jj » converties."""

    if isinstance(pValue, bool) or pValue is None:
        return pValue

    if isinstance(pValue, (int, float)):
        return float(pValue)

    if DATE_PATTERN.fullmatch(pValue):
        return date_to_serial(date.fromisoformat(pValue))

    rValue = pValue

    return rValue


def same_value(pValue, pExpected):
    """Compare un résultat à l'attendu : nombres à 1e-9 près, textes exacts."""

    if is_number(pValue) and is_number(pExpected):
        return abs(pValue - pExpected) <= 1e-9 * max(1.0, abs(pExpected))

    rSame = type(pValue) is type(pExpected) and pValue == pExpected

    return rSame
