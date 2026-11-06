"""Formules Excel en français : lecture, recopie, calcul sur une petite feuille

Les noms de fonctions, le point-virgule entre arguments et la virgule décimale
sont ceux d'Excel en français. Le registre des fonctions est dans
job/excel_functions.py, les conversions et les formats dans job/excel_values.py.
"""

import math
import re

from job.excel_functions import FUNCTIONS
from job.excel_values import (
    DIV0,
    ExcelError,
    NUM,
    REF,
    Range,
    check_number,
    compare,
    is_error,
    read_literal,
    scalar,
    to_number,
    to_text,
)

MAX_FORMULA_LENGTH = 500
MAX_NESTING = 30
MAX_RANGE_CELLS = 10_000
MAX_COLUMN = 702
MAX_ROW = 9999

# Nom anglais vers nom français, pour corriger l'erreur la plus fréquente
ENGLISH_NAMES = {
    "SUM": "SOMME",
    "AVERAGE": "MOYENNE",
    "COUNT": "NB",
    "COUNTA": "NBVAL",
    "COUNTBLANK": "NB.VIDE",
    "IF": "SI",
    "IFS": "SI.CONDITIONS",
    "AND": "ET",
    "OR": "OU",
    "NOT": "NON",
    "IFERROR": "SIERREUR",
    "COUNTIF": "NB.SI",
    "COUNTIFS": "NB.SI.ENS",
    "SUMIF": "SOMME.SI",
    "SUMIFS": "SOMME.SI.ENS",
    "AVERAGEIF": "MOYENNE.SI",
    "SUMPRODUCT": "SOMMEPROD",
    "VLOOKUP": "RECHERCHEV",
    "XLOOKUP": "RECHERCHEX",
    "MATCH": "EQUIV",
    "ROUND": "ARRONDI",
    "ROUNDUP": "ARRONDI.SUP",
    "ROUNDDOWN": "ARRONDI.INF",
    "INT": "ENT",
    "LEFT": "GAUCHE",
    "RIGHT": "DROITE",
    "MID": "STXT",
    "LEN": "NBCAR",
    "UPPER": "MAJUSCULE",
    "LOWER": "MINUSCULE",
    "TRIM": "SUPPRESPACE",
    "FIND": "TROUVE",
    "SEARCH": "CHERCHE",
    "SUBSTITUTE": "SUBSTITUE",
    "CONCATENATE": "CONCATENER",
    "TEXT": "TEXTE",
    "VALUE": "CNUM",
    "TODAY": "AUJOURDHUI",
    "YEAR": "ANNEE",
    "MONTH": "MOIS",
    "DAY": "JOUR",
    "WEEKDAY": "JOURSEM",
    "NETWORKDAYS": "NB.JOURS.OUVRES",
    "EOMONTH": "FIN.MOIS",
    "EDATE": "MOIS.DECALER",
    "TRUE": "VRAI",
    "FALSE": "FAUX",
}
TOKEN_PATTERN = re.compile(
    r"(?P<space>[ \t\r\n]+)"
    r'|(?P<string>"(?:[^"]|"")*")'
    r"|(?P<error>#(?:N/A|REF!|DIV/0!|VALEUR!|NOM\?|NOMBRE!|NUL!))"
    r"|(?P<number>[0-9]+(?:,[0-9]+)?)"
    r"|(?P<columns>\$?[A-Z]{1,2}:\$?[A-Z]{1,2}(?![A-Z0-9.(]))"
    r"|(?P<function>[A-Z][A-Z0-9.]*(?=[ \t\r\n]*\())"
    r"|(?P<ref>\$?[A-Z]{1,2}\$?[0-9]{1,4}(?![A-Z0-9.(]))"
    r"|(?P<name>[A-Z_][A-Z0-9_.]*)"
    r"|(?P<operator><>|<=|>=|[-+*/^&=<>%():;,])",
    re.I | re.A,
)
REF_PATTERN = re.compile(r"(\$?)([A-Z]{1,2})(\$?)([0-9]+)", re.I | re.A)
COLUMN_PATTERN = re.compile(r"(\$?)([A-Z]{1,2})", re.I | re.A)
COMPARISONS = ("=", "<>", "<", ">", "<=", ">=")


class FormulaError(Exception):
    """Formule illisible : le message est destiné à l'utilisateur."""


def column_number(pLetters):
    """Retourne le numéro d'une colonne : A = 1, Z = 26, AA = 27."""

    rNumber = 0

    for vLetter in pLetters.upper():
        rNumber = rNumber * 26 + ord(vLetter) - 64

    return rNumber


def column_letters(pNumber):
    """Retourne les lettres d'une colonne : 1 = A, 27 = AA."""

    rLetters = ""

    while pNumber > 0:
        pNumber, vRest = divmod(pNumber - 1, 26)
        rLetters = chr(65 + vRest) + rLetters

    return rLetters


def parse_cell(pName):
    """Retourne (ligne, colonne) d'une adresse comme « D2 » ou « $D$2 »."""

    vMatch = REF_PATTERN.fullmatch(pName.strip())

    if vMatch is None:
        raise ValueError(f"Adresse de cellule illisible : {pName}")

    rCell = (int(vMatch.group(4)), column_number(vMatch.group(2)))

    return rCell


def cell_name(pRow, pColumn):
    """Retourne l'adresse d'une cellule : (2, 4) donne « D2 »."""

    rName = f"{column_letters(pColumn)}{pRow}"

    return rName


def tokenize(pText):
    """Découpe une formule sans son « = » : liste de (genre, texte)."""

    rTokens = []
    vPosition = 0

    while vPosition < len(pText):
        vMatch = TOKEN_PATTERN.match(pText, vPosition)

        if vMatch is None:
            if pText[vPosition] == '"':
                raise FormulaError("Texte non fermé : il manque un guillemet.")

            raise FormulaError(f"Caractère inattendu : {pText[vPosition]}")

        vKind = vMatch.lastgroup
        vText = vMatch.group()
        vPosition = vMatch.end()

        if vKind != "string":
            vText = re.sub(r"[a-z]+", lambda pPart: pPart.group().upper(), vText)

        rTokens.append((vKind, vText))

    return rTokens


def shift_ref(pText, pRows, pColumns):
    """Décale une référence relative ; « #REF! » si elle sort de la feuille."""

    vMatch = REF_PATTERN.fullmatch(pText)
    vColumn = column_number(vMatch.group(2))
    vRow = int(vMatch.group(4))

    if not vMatch.group(1):
        vColumn += pColumns

    if not vMatch.group(3):
        vRow += pRows

    if vColumn < 1 or vRow < 1 or vColumn > MAX_COLUMN or vRow > MAX_ROW:
        return "#REF!"

    rText = f"{vMatch.group(1)}{column_letters(vColumn)}{vMatch.group(3)}{vRow}"

    return rText


def shift_columns(pText, pColumns):
    """Décale une plage de colonnes entières comme « B:C »."""

    vParts = []

    for vMatch in COLUMN_PATTERN.finditer(pText):
        vColumn = column_number(vMatch.group(2))

        if not vMatch.group(1):
            vColumn += pColumns

        if vColumn < 1 or vColumn > MAX_COLUMN:
            return "#REF!"

        vParts.append(f"{vMatch.group(1)}{column_letters(vColumn)}")

    rText = ":".join(vParts)

    return rText


def shift_formula(pFormula, pRows, pColumns):
    """Recopie une formule de pRows lignes et pColumns colonnes, $ respectés."""

    vParts = []

    for vKind, vText in tokenize(pFormula[1:]):
        if vKind == "ref":
            vText = shift_ref(vText, pRows, pColumns)

        elif vKind == "columns":
            vText = shift_columns(vText, pColumns)

        vParts.append(vText)

    rFormula = "=" + "".join(vParts)

    return rFormula


class Parser:
    """Analyse descendante : comparaisons, &, + -, * /, ^, signe, %, éléments."""

    def __init__(self, pTokens):
        self.tokens = [vToken for vToken in pTokens if vToken[0] != "space"]
        self.position = 0
        self.depth = 0

    def peek(self):
        """Retourne le jeton courant, ou (None, "") en fin de formule."""

        rToken = (
            self.tokens[self.position]
            if self.position < len(self.tokens)
            else (None, "")
        )

        return rToken

    def take(self):
        """Retourne le jeton courant et passe au suivant."""

        rToken = self.peek()
        self.position += 1

        return rToken

    def expect(self, pText):
        """Consomme un opérateur attendu, sinon lève FormulaError."""

        vKind, vText = self.take()

        if vKind == "operator" and vText == pText:
            return

        if vKind is None:
            raise FormulaError(
                "Formule incomplète : il manque une parenthèse fermante."
                if pText == ")"
                else "Formule incomplète."
            )

        raise unexpected_error(vKind, vText)

    def parse(self):
        """Retourne l'arbre de la formule entière."""

        if not self.tokens:
            raise FormulaError("La formule est vide.")

        rNode = self.comparison()
        vKind, vText = self.peek()

        if vKind is not None:
            if vText == ")":
                raise FormulaError("Parenthèse fermante en trop.")

            raise unexpected_error(vKind, vText)

        return rNode

    def binary(self, pOperators, pNext):
        """Lit une suite d'opérations de même priorité, associées à gauche."""

        rNode = pNext()

        while self.peek()[0] == "operator" and self.peek()[1] in pOperators:
            vOperator = self.take()[1]
            rNode = ("binary", vOperator, rNode, pNext())

        return rNode

    def comparison(self):
        """Lit les comparaisons, de priorité la plus faible."""

        return self.binary(COMPARISONS, self.concatenation)

    def concatenation(self):
        """Lit les concaténations avec &."""

        return self.binary(("&",), self.additive)

    def additive(self):
        """Lit les additions et les soustractions."""

        return self.binary(("+", "-"), self.multiplicative)

    def multiplicative(self):
        """Lit les multiplications et les divisions."""

        return self.binary(("*", "/"), self.power)

    def power(self):
        """Lit les puissances, associées à gauche comme dans Excel."""

        return self.binary(("^",), self.unary)

    def unary(self):
        """Lit un signe + ou - : prioritaire sur ^, donc -2^2 vaut 4."""

        if self.peek()[0] == "operator" and self.peek()[1] in ("+", "-"):
            vOperator = self.take()[1]
            self.enter()
            rNode = ("unary", vOperator, self.unary())
            self.depth -= 1

            return rNode

        rNode = self.percent()

        return rNode

    def percent(self):
        """Lit un élément suivi d'un ou plusieurs %."""

        rNode = self.primary()

        while self.peek() == ("operator", "%"):
            self.take()
            rNode = ("percent", rNode)

        return rNode

    def enter(self):
        """Compte un niveau d'imbrication ; lève FormulaError au-delà du plafond."""

        self.depth += 1

        if self.depth > MAX_NESTING:
            raise FormulaError("Formule trop imbriquée.")

    def primary(self):
        """Lit un nombre, un texte, une référence, une plage, un appel ou ( … )."""

        vKind, vText = self.take()

        if vKind is None:
            raise FormulaError("Formule incomplète.")

        if vKind == "number":
            return ("value", float(vText.replace(",", ".")))

        if vKind == "string":
            return ("value", vText[1:-1].replace('""', '"'))

        if vKind == "error":
            return ("value", ExcelError(vText))

        if vKind == "ref":
            return self.reference(vText)

        if vKind == "columns":
            vFirst, vLast = vText.replace("$", "").split(":")

            return ("columns", column_number(vFirst), column_number(vLast))

        if vKind == "function":
            return self.call(vText)

        if vKind == "name":
            if vText in ("VRAI", "FAUX"):
                return ("value", vText == "VRAI")

            raise FormulaError(describe_unknown_name(vText))

        if vText == "(":
            self.enter()
            rNode = self.comparison()
            self.expect(")")
            self.depth -= 1

            return rNode

        raise unexpected_error(vKind, vText)

    def reference(self, pText):
        """Lit une cellule, ou une plage si elle est suivie de « : »."""

        vRow, vColumn = parse_cell(pText)

        if self.peek() != ("operator", ":"):
            return ("range", vRow, vColumn, vRow, vColumn)

        self.take()
        vKind, vText = self.take()

        if vKind != "ref":
            raise FormulaError("Plage illisible : écrivez-la comme A2:A10.")

        vLastRow, vLastColumn = parse_cell(vText)
        rNode = ("range", vRow, vColumn, vLastRow, vLastColumn)

        return rNode

    def call(self, pName):
        """Lit un appel de fonction et vérifie le nombre d'arguments."""

        if pName not in FUNCTIONS:
            raise FormulaError(describe_unknown_function(pName))

        self.take()
        self.enter()
        vArguments = []

        if self.peek() == ("operator", ")"):
            self.take()

        else:
            while True:
                if self.peek()[0] == "operator" and self.peek()[1] in (";", ")"):
                    vArguments.append(("value", None))

                else:
                    vArguments.append(self.comparison())

                vKind, vText = self.take()

                if vKind == "operator" and vText == ";":
                    continue

                if vKind == "operator" and vText == ")":
                    break

                if vKind is None:
                    raise FormulaError(
                        "Formule incomplète : il manque une parenthèse fermante."
                    )

                raise unexpected_error(vKind, vText)

        self.depth -= 1
        vMinimum, vMaximum, _ = FUNCTIONS[pName]

        if not vMinimum <= len(vArguments) <= vMaximum:
            raise FormulaError(describe_arity(pName, vMinimum, vMaximum))

        rNode = ("call", pName, vArguments)

        return rNode


def unexpected_error(pKind, pText):
    """Retourne l'erreur d'un jeton mal placé, avec la cause probable."""

    if pKind == "operator" and pText == ",":
        return FormulaError(
            "Les arguments se séparent par un point-virgule (;) dans Excel en "
            "français, la virgule sert aux décimales."
        )

    rError = FormulaError(f"Élément inattendu : {pText}")

    return rError


def describe_unknown_function(pName):
    """Retourne le message d'une fonction inconnue, avec son nom français."""

    vFrench = ENGLISH_NAMES.get(pName)

    rMessage = (
        f"Fonction inconnue : {pName}. En français, elle s'écrit {vFrench}."
        if vFrench
        else f"Fonction inconnue : {pName}."
    )

    return rMessage


def describe_unknown_name(pName):
    """Retourne le message d'un nom inconnu : texte sans guillemets, en général."""

    vFrench = ENGLISH_NAMES.get(pName)

    rMessage = (
        f"Nom inconnu : {pName}. En français, il s'écrit {vFrench}."
        if vFrench
        else f"Nom inconnu : {pName}. Un texte s'écrit entre guillemets."
    )

    return rMessage


def describe_arity(pName, pMinimum, pMaximum):
    """Retourne le message d'un nombre d'arguments incorrect."""

    if pMinimum == pMaximum:
        return f"{pName} attend {pMinimum} argument(s)."

    rMessage = f"{pName} attend de {pMinimum} à {pMaximum} arguments."

    return rMessage


def parse_formula(pFormula):
    """Retourne l'arbre d'une formule qui commence par « = »."""

    if len(pFormula) > MAX_FORMULA_LENGTH:
        raise FormulaError(f"La formule dépasse {MAX_FORMULA_LENGTH} caractères.")

    if not pFormula.startswith("="):
        raise FormulaError("Une formule commence par le signe =.")

    rNode = Parser(tokenize(pFormula[1:])).parse()

    return rNode


def collect(pNode, pFunctions):
    """Ajoute à pFunctions les fonctions appelées ; retourne le nombre de références."""

    if pNode[0] in ("range", "columns"):
        return 1

    if pNode[0] == "call":
        pFunctions.add(pNode[1])
        vChildren = pNode[2]

    else:
        vChildren = [vItem for vItem in pNode[1:] if isinstance(vItem, tuple)]

    rCount = sum(collect(vChild, pFunctions) for vChild in vChildren)

    return rCount


def apply_power(pBase, pExponent):
    """Retourne pBase ^ pExponent avec les erreurs d'Excel."""

    if pBase == 0 and pExponent == 0:
        return NUM

    if pBase == 0 and pExponent < 0:
        return DIV0

    if pBase < 0 and pExponent != math.floor(pExponent):
        return NUM

    try:
        rValue = check_number(math.pow(pBase, pExponent))

    except OverflowError:
        rValue = NUM

    return rValue


def apply_binary(pOperator, pLeft, pRight):
    """Applique un opérateur à deux valeurs déjà calculées."""

    pLeft = scalar(pLeft)
    pRight = scalar(pRight)

    for vValue in (pLeft, pRight):
        if is_error(vValue):
            return vValue

    if pOperator in COMPARISONS:
        vOrder = compare(pLeft, pRight)

        return {
            "=": vOrder == 0,
            "<>": vOrder != 0,
            "<": vOrder < 0,
            ">": vOrder > 0,
            "<=": vOrder <= 0,
            ">=": vOrder >= 0,
        }[pOperator]

    if pOperator == "&":
        return to_text(pLeft) + to_text(pRight)

    vLeft = to_number(pLeft)
    vRight = to_number(pRight)

    for vValue in (vLeft, vRight):
        if is_error(vValue):
            return vValue

    if pOperator == "+":
        return check_number(vLeft + vRight)

    if pOperator == "-":
        return check_number(vLeft - vRight)

    if pOperator == "*":
        return check_number(vLeft * vRight)

    if pOperator == "/":
        return DIV0 if vRight == 0 else check_number(vLeft / vRight)

    rValue = apply_power(vLeft, vRight)

    return rValue


def evaluate(pNode, pSheet):
    """Calcule un nœud de l'arbre : valeur simple ou plage."""

    vKind = pNode[0]

    if vKind == "value":
        return pNode[1]

    if vKind == "range":
        return pSheet.range(*pNode[1:])

    if vKind == "columns":
        return pSheet.range(1, pNode[1], pSheet.last_row, pNode[2])

    if vKind == "unary":
        vValue = to_number(evaluate(pNode[2], pSheet))

        if is_error(vValue) or pNode[1] == "+":
            return vValue

        return -vValue

    if vKind == "percent":
        vValue = to_number(evaluate(pNode[1], pSheet))

        return vValue if is_error(vValue) else vValue / 100

    if vKind == "binary":
        return apply_binary(
            pNode[1], evaluate(pNode[2], pSheet), evaluate(pNode[3], pSheet)
        )

    vArguments = [evaluate(vArgument, pSheet) for vArgument in pNode[2]]

    rValue = FUNCTIONS[pNode[1]][2](*vArguments)

    return rValue


class Sheet:
    """Feuille de calcul : valeurs livrées, formules calculées à la demande."""

    def __init__(self, pRows, pFormulas=None):
        self.cells = {}

        for vRowIndex, vRow in enumerate(pRows, start=1):
            for vColumnIndex, vValue in enumerate(vRow, start=1):
                if vValue is not None and vValue != "":
                    self.cells[(vRowIndex, vColumnIndex)] = read_literal(vValue)

        for vName, vFormula in (pFormulas or {}).items():
            self.cells[parse_cell(vName)] = vFormula

        self.last_row = max((vRow for vRow, _ in self.cells), default=1)
        self.trees = {}
        self.results = {}
        self.pending = set()
        self.circular = False

    def range(self, pTop, pLeft, pBottom, pRight):
        """Retourne une plage, ou #REF! si elle est trop grande."""

        if (abs(pBottom - pTop) + 1) * (abs(pRight - pLeft) + 1) > MAX_RANGE_CELLS:
            return REF

        rRange = Range(self, pTop, pLeft, pBottom, pRight)

        return rRange

    def value(self, pRow, pColumn):
        """Retourne la valeur d'une cellule ; une formule est calculée une fois."""

        vKey = (pRow, pColumn)
        vRaw = self.cells.get(vKey)

        if not (isinstance(vRaw, str) and vRaw.startswith("=")):
            return vRaw

        if vKey in self.results:
            return self.results[vKey]

        if vKey in self.pending:
            self.circular = True

            return REF

        self.pending.add(vKey)

        try:
            if vRaw not in self.trees:
                self.trees[vRaw] = parse_formula(vRaw)

            rValue = finish(evaluate(self.trees[vRaw], self))

        except FormulaError:
            rValue = REF

        finally:
            self.pending.discard(vKey)

        self.results[vKey] = rValue

        return rValue


def finish(pValue):
    """Valeur finale d'une formule : une cellule vide référencée vaut 0."""

    vValue = scalar(pValue)

    rValue = 0.0 if vValue is None else vValue

    return rValue
