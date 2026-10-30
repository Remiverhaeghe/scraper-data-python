"""Bac à sable SQL : base d'atelier en mémoire, dialectes MySQL et SQL Server

Le moteur est SQLite, en mémoire et recréé à chaque requête : rien n'est écrit
sur le disque. Les écritures propres à MySQL ou à SQL Server (LIMIT ou TOP,
IFNULL ou ISNULL, NOW ou GETDATE, DATEDIFF) sont vérifiées puis traduites, pour
qu'une écriture de l'autre dialecte soit signalée comme le ferait le vrai serveur.
"""

import re
import sqlite3
import time
from collections import Counter
from datetime import datetime
from functools import lru_cache

from config import SQL_DATABASE_FILE
from utils.logger import get_logger

logger = get_logger(__name__)

DIALECTS = {"mysql": "MySQL", "sqlserver": "SQL Server"}
DEFAULT_DIALECT = "mysql"

# Date du jour de la base d'exemple : les résultats ne dépendent pas du jour réel
TODAY = "2026-06-30 08:00:00"

MAX_QUERY_LENGTH = 4000
MAX_ROWS = 200
MAX_SECONDS = 2.0
MAX_VALUE_LENGTH = 100_000
MAX_CELL_LENGTH = 200
PROGRESS_STEPS = 10_000

ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
    sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_UPDATE,
    sqlite3.SQLITE_DELETE,
}
WRITE_ACTIONS = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
REFUSED_FUNCTIONS = {"load_extension"}

TOKEN_PATTERN = re.compile(r"'(?:[^']|'')*'|--[^\n]*|/\*.*?(?:\*/|\Z)", re.S)
LITERAL_PATTERN = re.compile(r"\x00(\d+)\x00")
TOP_PATTERN = re.compile(
    r"^\s*SELECT\s+(DISTINCT\s+)?TOP\s*(?:\(\s*(\d+)\s*\)|(\d+))\s", re.I
)

UNITS = {
    "day": "day",
    "dd": "day",
    "d": "day",
    "hour": "hour",
    "hh": "hour",
    "minute": "minute",
    "mi": "minute",
    "n": "minute",
}
UNIT_SECONDS = {"day": 86400, "hour": 3600, "minute": 60}
UNIT_NAMES = "|".join(UNITS) + "|week|wk|month|mm|quarter|year|yy|second|ss"

REFUSED = {
    "mysql": (
        (
            r"\bTOP\s*\(?\s*\d",
            "MySQL n'a pas TOP : ajoutez LIMIT 3 à la fin de la requête.",
        ),
        (
            r"\bGETDATE\s*\(",
            "En MySQL, la date du jour s'obtient avec NOW() ou CURDATE().",
        ),
        (
            r"\bISNULL\s*\([^()]*,",
            "En MySQL, ISNULL(x) teste seulement si x est NULL : pour remplacer une "
            "valeur vide, écrivez IFNULL(valeur, remplacement) ou COALESCE.",
        ),
        (
            r"\bLEN\s*\(",
            "En MySQL, la longueur d'un texte s'obtient avec CHAR_LENGTH().",
        ),
        (
            rf"\bDATEDIFF\s*\(\s*(?:{UNIT_NAMES})\s*,",
            "En MySQL, DATEDIFF(fin, début) compte des jours, sans unité ; pour des "
            "heures, écrivez TIMESTAMPDIFF(HOUR, début, fin).",
        ),
        (
            r"\[",
            "En MySQL, un nom spécial s'écrit entre accents graves (`nom`), "
            "pas entre crochets.",
        ),
        (
            r"\|\|",
            "En MySQL, || est un OU logique : pour coller des textes, "
            "écrivez CONCAT(a, b).",
        ),
    ),
    "sqlserver": (
        (
            r"\bLIMIT\b",
            "SQL Server n'a pas LIMIT : écrivez SELECT TOP 3 … au début de la requête.",
        ),
        (
            r"\b(?:NOW|CURDATE)\s*\(",
            "En SQL Server, la date du jour s'obtient avec GETDATE().",
        ),
        (
            r"\bIFNULL\s*\(",
            "SQL Server n'a pas IFNULL : écrivez ISNULL(valeur, remplacement) "
            "ou COALESCE.",
        ),
        (
            r"\b(?:CHAR_LENGTH|LENGTH)\s*\(",
            "En SQL Server, la longueur d'un texte s'obtient avec LEN().",
        ),
        (
            r"\bTIMESTAMPDIFF\s*\(",
            "SQL Server n'a pas TIMESTAMPDIFF : écrivez DATEDIFF(hour, début, fin).",
        ),
        (
            rf"\bDATEDIFF\s*\((?!\s*(?:{UNIT_NAMES})\s*,)",
            "En SQL Server, DATEDIFF prend d'abord l'unité : "
            "DATEDIFF(day, début, fin).",
        ),
        (
            r"`",
            "En SQL Server, un nom spécial s'écrit entre crochets ([nom]), "
            "pas entre accents graves.",
        ),
        (
            r"\|\|",
            "SQL Server colle les textes avec CONCAT(a, b), pas avec ||.",
        ),
    ),
}

REWRITES = {
    "mysql": (
        (r"\bNOW\s*\(\s*\)", f"'{TODAY}'"),
        (r"\bCURDATE\s*\(\s*\)", f"'{TODAY[:10]}'"),
        (r"\bISNULL\s*\(", "mysql_isnull("),
        (r"\bCHAR_LENGTH\s*\(", "length("),
    ),
    "sqlserver": (
        (r"\bGETDATE\s*\(\s*\)", f"'{TODAY}'"),
        (r"\bISNULL\s*\(", "ifnull("),
        (r"\bLEN\s*\(", "length("),
    ),
}

# Fonctions dont le premier argument est une unité de temps écrite sans guillemets
UNIT_FUNCTIONS = {
    "mysql": ("TIMESTAMPDIFF", "timestamp_diff"),
    "sqlserver": ("DATEDIFF", "boundary_diff"),
}

ERROR_MESSAGES = (
    (r"no such table: (\S+)", "Table inconnue : {0}."),
    (r"no such column: (\S+)", "Colonne inconnue : {0}."),
    (
        r"ambiguous column name: (\S+)",
        "Colonne ambiguë : {0} existe dans plusieurs tables, précisez laquelle "
        "avec son alias (par exemple m.{0}).",
    ),
    (r'near "(.+?)": syntax error', "Erreur de syntaxe près de « {0} »."),
    (r"incomplete input", "Requête incomplète."),
    (
        r"misuse of aggregate(?: function)?:? (\w+)\(\)",
        "{0}() ne peut pas figurer dans WHERE : un filtre sur un regroupement "
        "s'écrit dans HAVING.",
    ),
    (
        r"a GROUP BY clause is required before HAVING",
        "HAVING filtre des groupes : il suit un GROUP BY.",
    ),
    (
        r"wrong number of arguments to function (\w+)\(\)",
        "Mauvais nombre d'arguments pour {0}().",
    ),
    (r"no such function: (\w+)", "Fonction inconnue : {0}."),
    (
        r"not authorized",
        "Seules les requêtes SELECT, INSERT, UPDATE et DELETE sont permises ici.",
    ),
    (r"interrupted", "Requête arrêtée au bout de 2 secondes : vérifiez les jointures."),
    (r"one statement at a time", "Une seule requête à la fois."),
    (r"string or blob too big", "Valeur trop volumineuse."),
    (r"NOT NULL constraint failed: (\S+)", "La colonne {0} est obligatoire."),
    (r"UNIQUE constraint failed: (\S+)", "Valeur déjà utilisée : {0}."),
    (
        r"table (\w+) has (\d+) columns but (\d+) values were supplied",
        "La table {0} a {1} colonnes mais {2} valeurs sont données : "
        "précisez la liste des colonnes.",
    ),
    (r"(\d+) values for (\d+) columns", "{0} valeurs pour {1} colonnes."),
    (
        r"user-defined function raised exception",
        "Date illisible dans un calcul de durée.",
    ),
)


class SqlError(Exception):
    """Requête refusée avant exécution : dialecte, longueur, caractère interdit."""


def split_literals(pQuery):
    """Retourne le code sans commentaires, ses chaînes remplacées par des repères."""

    vLiterals = []

    def replace(pMatch):
        vText = pMatch.group()

        if not vText.startswith("'"):
            return " "

        vLiterals.append(vText)

        return f"\x00{len(vLiterals) - 1}\x00"

    rCode = TOKEN_PATTERN.sub(replace, pQuery)

    return rCode, vLiterals


def rewrite_unit_function(pCode, pName, pTarget):
    """Remplace FONCTION(unité, … par cible('unité', … en vérifiant l'unité."""

    def replace(pMatch):
        vUnit = UNITS.get(pMatch.group(1).lower())

        if vUnit is None:
            raise SqlError(
                f"Unité non simulée : {pMatch.group(1)} ; "
                "utilisez day, hour ou minute."
            )

        return f"{pTarget}('{vUnit}',"

    rCode = re.sub(rf"\b{pName}\s*\(\s*([a-z]+)\s*,", replace, pCode, flags=re.I)

    return rCode


def translate(pQuery, pDialect):
    """Retourne la requête pour SQLite ; lève SqlError si le dialecte la refuse."""

    if pDialect not in DIALECTS:
        raise SqlError(f"Dialecte inconnu : {pDialect}")

    if len(pQuery) > MAX_QUERY_LENGTH:
        raise SqlError(f"Requête trop longue : {MAX_QUERY_LENGTH} caractères au plus.")

    if "\x00" in pQuery:
        raise SqlError("Caractère interdit dans la requête.")

    vCode, vLiterals = split_literals(pQuery)

    if not vCode.strip(" \n\r\t;"):
        raise SqlError("Écrivez une requête.")

    for vPattern, vMessage in REFUSED[pDialect]:
        if re.search(vPattern, vCode, re.I):
            raise SqlError(vMessage)

    vName, vTarget = UNIT_FUNCTIONS[pDialect]
    vCode = rewrite_unit_function(vCode, vName, vTarget)

    for vPattern, vReplacement in REWRITES[pDialect]:
        vCode = re.sub(vPattern, vReplacement, vCode, flags=re.I)

    if pDialect == "sqlserver":
        vCode = move_top(vCode)

    rQuery = LITERAL_PATTERN.sub(lambda pMatch: vLiterals[int(pMatch[1])], vCode)

    return rQuery


def move_top(pCode):
    """Remplace SELECT TOP n du début de la requête par LIMIT n à la fin."""

    vMatch = TOP_PATTERN.match(pCode)

    if vMatch is None:
        if re.search(r"\bTOP\b", pCode, re.I):
            raise SqlError(
                "TOP n'est simulé qu'au début de la requête : SELECT TOP 3 colonnes …"
            )

        return pCode

    vCount = vMatch.group(2) or vMatch.group(3)
    vRest = pCode[vMatch.end() :].rstrip(" \n\r\t;")

    if re.search(r"\bTOP\b", vRest, re.I):
        raise SqlError("TOP n'est simulé qu'au début de la requête principale.")

    rCode = f"SELECT {vMatch.group(1) or ''}{vRest} LIMIT {vCount}"

    return rCode


def parse_moment(pValue):
    """Retourne une date lue au format AAAA-MM-JJ, avec ou sans heure."""

    rMoment = datetime.fromisoformat(str(pValue))

    return rMoment


def mysql_datediff(pEnd, pStart):
    """DATEDIFF de MySQL : jours entre deux dates, heures ignorées."""

    if pEnd is None or pStart is None:
        return None

    rDays = (parse_moment(pEnd).date() - parse_moment(pStart).date()).days

    return rDays


def timestamp_diff(pUnit, pStart, pEnd):
    """TIMESTAMPDIFF de MySQL : nombre d'unités entières écoulées."""

    if pStart is None or pEnd is None:
        return None

    vSeconds = (parse_moment(pEnd) - parse_moment(pStart)).total_seconds()

    rCount = int(vSeconds / UNIT_SECONDS[pUnit])

    return rCount


def boundary_diff(pUnit, pStart, pEnd):
    """DATEDIFF de SQL Server : frontières d'unité franchies, pas unités entières."""

    if pStart is None or pEnd is None:
        return None

    vStart = parse_moment(pStart)
    vEnd = parse_moment(pEnd)

    if pUnit == "day":
        return (vEnd.date() - vStart.date()).days

    vFields = {"second": 0, "microsecond": 0}

    if pUnit == "hour":
        vFields["minute"] = 0

    vSeconds = (vEnd.replace(**vFields) - vStart.replace(**vFields)).total_seconds()

    rCount = int(vSeconds // UNIT_SECONDS[pUnit])

    return rCount


def date_part(pIndex):
    """Retourne une fonction YEAR, MONTH ou DAY lisant une date AAAA-MM-JJ."""

    def read(pValue):
        if pValue is None:
            return None

        return parse_moment(pValue).timetuple()[pIndex]

    return read


@lru_cache(maxsize=1)
def load_script():
    """Retourne le script de création de la base d'exemple."""

    rScript = SQL_DATABASE_FILE.read_text(encoding="utf-8")

    return rScript


def open_database(pDialect):
    """Retourne une base d'exemple neuve, en mémoire, avec les fonctions du dialecte."""

    rConnection = sqlite3.connect(":memory:", isolation_level=None)
    rConnection.executescript(load_script())

    for vName, vIndex in (("YEAR", 0), ("MONTH", 1), ("DAY", 2)):
        rConnection.create_function(vName, 1, date_part(vIndex), deterministic=True)

    if pDialect == "mysql":
        rConnection.create_function("DATEDIFF", 2, mysql_datediff, deterministic=True)
        rConnection.create_function("timestamp_diff", 3, timestamp_diff)
        rConnection.create_function(
            "mysql_isnull", 1, lambda pValue: int(pValue is None), deterministic=True
        )
    else:
        rConnection.create_function("boundary_diff", 3, boundary_diff)

    rConnection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_VALUE_LENGTH)

    return rConnection


def authorize(
    pAction, pArg1, pArg2, pDatabase, pSource
):  # pylint: disable=unused-argument
    """Autorise lectures et écritures de lignes ; refuse ATTACH, PRAGMA, DROP."""

    if pAction not in ALLOWED_ACTIONS:
        return sqlite3.SQLITE_DENY

    if pAction in WRITE_ACTIONS and str(pArg1).lower().startswith("sqlite_"):
        return sqlite3.SQLITE_DENY

    if pAction == sqlite3.SQLITE_FUNCTION and str(pArg2).lower() in REFUSED_FUNCTIONS:
        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def protect(pConnection):
    """Limite la base aux lignes de données et la requête à MAX_SECONDS."""

    vDeadline = time.monotonic() + MAX_SECONDS

    pConnection.set_authorizer(authorize)
    pConnection.set_progress_handler(
        lambda: int(time.monotonic() > vDeadline), PROGRESS_STEPS
    )


def explain_error(pError):
    """Retourne en français le message d'une erreur SQLite."""

    vText = str(pError)

    for vPattern, vMessage in ERROR_MESSAGES:
        vMatch = re.search(vPattern, vText)

        if vMatch:
            return vMessage.format(*vMatch.groups())

    rMessage = f"Erreur SQL : {vText}"

    return rMessage


def fetch(pCursor):
    """Retourne colonnes et lignes d'un curseur, au plus MAX_ROWS lignes."""

    vRows = pCursor.fetchmany(MAX_ROWS + 1)

    rFetched = {
        "columns": [vColumn[0] for vColumn in pCursor.description],
        "rows": [tuple(vRow) for vRow in vRows[:MAX_ROWS]],
        "truncated": len(vRows) > MAX_ROWS,
    }

    return rFetched


def execute(pQuery, pDialect, pCheckQuery=""):
    """Exécute une requête sur une base neuve, puis la requête de contrôle.

    Le résultat contient les colonnes et lignes lues (celles du contrôle pour une
    écriture), le nombre de lignes modifiées et le message d'erreur éventuel.
    """

    rResult = {
        "columns": [],
        "rows": [],
        "truncated": False,
        "changed": None,
        "error": "",
    }

    try:
        vQuery = translate(pQuery, pDialect)

    except SqlError as vError:
        rResult["error"] = str(vError)
        return rResult

    vConnection = open_database(pDialect)

    try:
        protect(vConnection)
        vCursor = vConnection.execute(vQuery)

        if vCursor.description is None:
            rResult["changed"] = max(vCursor.rowcount, 0)
        else:
            rResult.update(fetch(vCursor))

        if pCheckQuery:
            rResult.update(fetch(vConnection.execute(pCheckQuery)))

    except (sqlite3.Error, sqlite3.Warning) as vError:
        rResult["error"] = explain_error(vError)

    finally:
        vConnection.close()

    return rResult


@lru_cache(maxsize=1)
def describe_schema():
    """Retourne les tables de la base d'exemple et leurs colonnes, dans l'ordre."""

    vConnection = open_database(DEFAULT_DIALECT)

    try:
        vTables = [
            vRow[0]
            for vRow in vConnection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid"
            )
        ]
        rSchema = tuple(
            (
                vTable,
                tuple(
                    vRow[1]
                    for vRow in vConnection.execute(
                        "SELECT * FROM pragma_table_info(?)", (vTable,)
                    )
                ),
            )
            for vTable in vTables
        )

    finally:
        vConnection.close()

    return rSchema


def normalize_value(pValue):
    """Arrondit les nombres à 2 décimales pour comparer 3, 3.0 et 2.9999999."""

    if isinstance(pValue, (int, float)):
        return round(float(pValue), 2)

    return pValue


def format_value(pValue):
    """Retourne une valeur affichable : NULL, nombre sans zéros inutiles."""

    if pValue is None:
        return "NULL"

    if isinstance(pValue, float):
        return f"{pValue:.2f}".rstrip("0").rstrip(".")

    vText = str(pValue)

    rText = vText if len(vText) <= MAX_CELL_LENGTH else vText[:MAX_CELL_LENGTH] + "…"

    return rText


def format_row(pRow):
    """Retourne une ligne en texte : valeurs séparées par des barres."""

    rText = "(" + " | ".join(format_value(vValue) for vValue in pRow) + ")"

    return rText


def compare_results(pResult, pExpected, pOrdered):
    """Retourne ce qui diffère du résultat attendu, ou une chaîne vide."""

    vActual = [tuple(map(normalize_value, vRow)) for vRow in pResult["rows"]]
    vExpected = [tuple(map(normalize_value, vRow)) for vRow in pExpected["rows"]]
    vColumns = len(pResult["columns"])
    vExpectedColumns = len(pExpected["columns"])

    if vColumns != vExpectedColumns:
        return f"Votre résultat a {vColumns} colonne(s), il en faut {vExpectedColumns}."

    if vActual == vExpected:
        return ""

    vMissing = Counter(vExpected) - Counter(vActual)
    vExtra = Counter(vActual) - Counter(vExpected)

    if not vMissing and not vExtra:
        return (
            ""
            if not pOrdered
            else "Les bonnes lignes, mais pas dans l'ordre demandé : vérifiez ORDER BY."
        )

    vParts = []

    if len(vActual) != len(vExpected):
        vParts.append(
            f"Votre résultat a {len(vActual)} ligne(s), il en faut {len(vExpected)}."
        )

    if vMissing:
        vParts.append(f"Ligne attendue absente : {format_row(next(iter(vMissing)))}.")

    if vExtra:
        vParts.append(f"Ligne en trop : {format_row(next(iter(vExtra)))}.")

    rMessage = " ".join(vParts)

    return rMessage
