"""Langage du simulateur d'automate : un barreau de ladder par ligne

Chaque ligne affecte une expression à une variable :

    moteur = (marche | moteur) & arret
    SET x2 = x1 & bas
    RESET x1 = x2
    t_attente = TON(fin_sortie, 2s)
    lot = CTU(piece, 5, acquit)

« & » met des contacts en série, « | » en parallèle, « ! » donne un contact
à ouverture. Un « ! » devant une parenthèse n'a pas d'équivalent en ladder :
il est refusé. Le programme est dessiné en ladder, en SVG, pour le bureau et
pour le web.
"""

import re
from html import escape

NAME_PATTERN = re.compile(r"[a-z_][a-z0-9_]*")
TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<duration>\d+(?:[.,]\d+)?\s*(?:ms|s)\b)|(?P<number>\d+)"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<symbol>[&|!(),=]))"
)

MAX_LINES = 30
MAX_LINE_LENGTH = 200

# Mots réservés aux instructions, en capitales
KEYWORDS = ("SET", "RESET", "TON", "CTU")


class LadderError(ValueError):
    """Erreur d'écriture d'un programme, avec le numéro de sa ligne."""

    def __init__(self, pLine, pMessage):
        """Garde la ligne fautive pour l'afficher à côté du message."""
        super().__init__(f"Ligne {pLine} : {pMessage}")
        self.line = pLine


def tokenize(pText, pLine):
    """Découpe une ligne en jetons (genre, valeur)."""

    rTokens = []
    vPosition = 0
    vText = pText.rstrip()

    while vPosition < len(vText):
        vMatch = TOKEN_PATTERN.match(vText, vPosition)

        if vMatch is None or vMatch.end() == vPosition:
            raise LadderError(
                pLine, f"caractère inattendu « {vText[vPosition:].strip()[:1]} »"
            )

        vKind = vMatch.lastgroup
        rTokens.append((vKind, vMatch.group(vKind).replace(" ", "")))
        vPosition = vMatch.end()

    return rTokens


class Parser:
    """Analyse d'une ligne par descente récursive : ou, puis et, puis contact."""

    def __init__(self, pTokens, pLine):
        """Prépare la lecture des jetons d'une ligne."""
        self.tokens = pTokens
        self.position = 0
        self.line = pLine

    def peek(self):
        """Retourne le jeton courant, ou None en fin de ligne."""
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self, pValue=None):
        """Consomme le jeton courant, en vérifiant sa valeur si elle est donnée."""
        vToken = self.peek()

        if vToken is None or (pValue is not None and vToken[1] != pValue):
            raise LadderError(
                self.line,
                f"« {pValue} » attendu" if pValue else "ligne incomplète",
            )

        self.position += 1

        return vToken

    def parse_or(self):
        """Branches en parallèle séparées par « | »."""
        vNodes = [self.parse_and()]

        while self.peek() == ("symbol", "|"):
            self.take()
            vNodes.append(self.parse_and())

        return vNodes[0] if len(vNodes) == 1 else ("or", vNodes)

    def parse_and(self):
        """Contacts en série séparés par « & »."""
        vNodes = [self.parse_contact()]

        while self.peek() == ("symbol", "&"):
            self.take()
            vNodes.append(self.parse_contact())

        return vNodes[0] if len(vNodes) == 1 else ("and", vNodes)

    def parse_contact(self):
        """Contact à fermeture, à ouverture (« ! »), ou groupe entre parenthèses."""
        vToken = self.peek()

        if vToken == ("symbol", "!"):
            self.take()
            vNext = self.peek()

            if vNext == ("symbol", "("):
                raise LadderError(
                    self.line,
                    "« ! » devant une parenthèse n'existe pas en ladder : "
                    "inversez chaque contact à la place",
                )

            return ("var", self.parse_name(), True)

        if vToken == ("symbol", "("):
            self.take()
            vNode = self.parse_or()
            self.take(")")

            return vNode

        return ("var", self.parse_name(), False)

    def parse_name(self):
        """Nom de variable en minuscules."""
        vToken = self.take()

        if vToken[0] != "name" or not NAME_PATTERN.fullmatch(vToken[1]):
            raise LadderError(
                self.line,
                f"nom de variable attendu à la place de « {vToken[1]} » "
                "(minuscules, chiffres et _)",
            )

        return vToken[1]

    def parse_number(self):
        """Nombre entier positif."""
        vToken = self.take()

        if vToken[0] != "number" or int(vToken[1]) < 1:
            raise LadderError(self.line, "nombre entier positif attendu")

        return int(vToken[1])

    def parse_duration(self):
        """Durée en secondes (« 2s ») ou millisecondes (« 500ms »)."""
        vToken = self.take()

        if vToken[0] != "duration":
            raise LadderError(self.line, "durée attendue, par exemple 2s ou 500ms")

        vText = vToken[1].replace(",", ".")
        vSeconds = (
            float(vText[:-2]) / 1000 if vText.endswith("ms") else float(vText[:-1])
        )

        if vSeconds <= 0:
            raise LadderError(self.line, "la durée doit être positive")

        return vSeconds

    def parse_rung(self):
        """Barreau complet : instruction éventuelle, cible, « = », partie droite."""
        vKind = "coil"

        if self.peek() in (("name", "SET"), ("name", "RESET")):
            vKind = self.take()[1].lower()

        vTarget = self.parse_name()
        self.take("=")

        vRung = {"kind": vKind, "target": vTarget, "line": self.line}

        if vKind == "coil" and self.peek() in (("name", "TON"), ("name", "CTU")):
            vInstruction = self.take()[1]
            self.take("(")
            vRung["expr"] = self.parse_or()
            self.take(",")

            if vInstruction == "TON":
                vRung.update(kind="ton", preset=self.parse_duration())
            else:
                vRung.update(kind="ctu", preset=self.parse_number(), reset=None)

                if self.peek() == ("symbol", ","):
                    self.take()
                    vRung["reset"] = self.parse_or()

            self.take(")")
        else:
            vRung["expr"] = self.parse_or()

        if self.peek() is not None:
            raise LadderError(
                self.line, f"« {self.peek()[1]} » en trop en fin de ligne"
            )

        return vRung


def parse_program(pText, pInputs):
    """Retourne les barreaux d'un programme ; lève LadderError à la première faute.

    Les lignes vides et les commentaires (« # ») sont ignorés. Une entrée ne peut
    pas être affectée : elle vient de la machine.
    """

    vLines = (pText or "").splitlines()

    if len(vLines) > MAX_LINES * 2:
        raise LadderError(len(vLines), "programme trop long")

    rRungs = []

    for vIndex, vLine in enumerate(vLines, 1):
        vCode = vLine.split("#", 1)[0].strip()

        if not vCode:
            continue

        if len(vCode) > MAX_LINE_LENGTH:
            raise LadderError(vIndex, "ligne trop longue")

        vRung = Parser(tokenize(vCode, vIndex), vIndex).parse_rung()

        if vRung["target"] in pInputs:
            raise LadderError(
                vIndex,
                f"« {vRung['target']} » est une entrée : elle se lit, sans s'écrire",
            )

        rRungs.append(vRung)

    if len(rRungs) > MAX_LINES:
        raise LadderError(len(vLines), f"{MAX_LINES} barreaux au plus")

    return rRungs


def evaluate(pNode, pValues):
    """Évalue une expression de contacts avec les valeurs courantes."""

    vKind = pNode[0]

    if vKind == "var":
        rValue = bool(pValues.get(pNode[1], False)) != pNode[2]
    elif vKind == "and":
        rValue = all(evaluate(vNode, pValues) for vNode in pNode[1])
    else:
        rValue = any(evaluate(vNode, pValues) for vNode in pNode[1])

    return rValue


def collect_names(pRungs):
    """Retourne les variables lues ou écrites par le programme."""

    rNames = set()

    def visit(pNode):
        if pNode is None:
            return

        if pNode[0] == "var":
            rNames.add(pNode[1])
        else:
            for vNode in pNode[1]:
                visit(vNode)

    for vRung in pRungs:
        rNames.add(vRung["target"])
        visit(vRung["expr"])
        visit(vRung.get("reset"))

    return rNames


# Dessin : une cellule par contact, des branches empilées pour le parallèle
CELL_WIDTH = 92
CELL_HEIGHT = 46
RAIL_MARGIN = 14
COIL_WIDTH = 120
INK = "#0f172a"
LIVE = "#16a34a"
MUTED = "#64748b"


def measure(pNode):
    """Retourne la largeur (en cellules) et la hauteur (en branches) d'une expression."""

    if pNode[0] == "var":
        return 1, 1

    vSizes = [measure(vNode) for vNode in pNode[1]]

    if pNode[0] == "and":
        return sum(vSize[0] for vSize in vSizes), max(vSize[1] for vSize in vSizes)

    return max(vSize[0] for vSize in vSizes), sum(vSize[1] for vSize in vSizes)


def draw_node(pNode, pX, pY, pWidth, pValues, pParts):
    """Dessine une expression dans un cadre de pWidth cellules à partir de (pX, pY)."""

    vMiddle = pY + CELL_HEIGHT / 2

    if pNode[0] == "var":
        vLive = evaluate(pNode, pValues) if pValues is not None else False
        vColor = LIVE if vLive else INK
        vLeft = pX + CELL_WIDTH / 2 - 10
        vRight = pX + CELL_WIDTH / 2 + 10
        pParts.append(
            f'<line x1="{pX}" y1="{vMiddle}" x2="{vLeft}" y2="{vMiddle}" stroke="{INK}" stroke-width="2"/>'
            f'<line x1="{vLeft}" y1="{vMiddle - 11}" x2="{vLeft}" y2="{vMiddle + 11}" stroke="{vColor}" stroke-width="3"/>'
            f'<line x1="{vRight}" y1="{vMiddle - 11}" x2="{vRight}" y2="{vMiddle + 11}" stroke="{vColor}" stroke-width="3"/>'
            f'<line x1="{vRight}" y1="{vMiddle}" x2="{pX + pWidth * CELL_WIDTH}" y2="{vMiddle}" stroke="{INK}" stroke-width="2"/>'
            f'<text x="{pX + CELL_WIDTH / 2}" y="{vMiddle - 15}" text-anchor="middle" font-size="12" fill="{vColor}">{escape(pNode[1])}</text>'
        )

        if pNode[2]:
            pParts.append(
                f'<line x1="{vLeft - 3}" y1="{vMiddle + 10}" x2="{vRight + 3}" y2="{vMiddle - 10}" stroke="{vColor}" stroke-width="2"/>'
            )

        return

    if pNode[0] == "and":
        vX = pX

        for vIndex, vChild in enumerate(pNode[1]):
            vChildWidth = measure(vChild)[0]

            # Le dernier contact de la série s'étire jusqu'au bout du cadre.
            if vIndex == len(pNode[1]) - 1:
                vChildWidth = pWidth - (vX - pX) / CELL_WIDTH

            draw_node(vChild, vX, pY, vChildWidth, pValues, pParts)
            vX += vChildWidth * CELL_WIDTH

        return

    vY = pY
    vBottom = pY

    for vChild in pNode[1]:
        draw_node(vChild, pX, vY, pWidth, pValues, pParts)
        vBottom = vY + CELL_HEIGHT / 2
        vY += measure(vChild)[1] * CELL_HEIGHT

    vRightX = pX + pWidth * CELL_WIDTH
    pParts.append(
        f'<line x1="{pX}" y1="{vMiddle}" x2="{pX}" y2="{vBottom}" stroke="{INK}" stroke-width="2"/>'
        f'<line x1="{vRightX}" y1="{vMiddle}" x2="{vRightX}" y2="{vBottom}" stroke="{INK}" stroke-width="2"/>'
    )


def describe_coil(pRung):
    """Retourne le symbole et le texte de la sortie d'un barreau."""

    if pRung["kind"] == "ton":
        rCoil = ("TON", f"{pRung['preset']:g} s")
    elif pRung["kind"] == "ctu":
        rCoil = ("CTU", f"PV {pRung['preset']}")
    elif pRung["kind"] == "set":
        rCoil = ("S", "")
    elif pRung["kind"] == "reset":
        rCoil = ("R", "")
    else:
        rCoil = ("", "")

    return rCoil


def render_svg(pRungs, pValues=None):
    """Retourne le programme dessiné en ladder ; pValues colore les contacts passants."""

    vWidth = max((measure(vRung["expr"])[0] for vRung in pRungs), default=1)
    vTotalWidth = RAIL_MARGIN * 2 + vWidth * CELL_WIDTH + COIL_WIDTH
    vParts = []
    vY = 10

    for vRung in pRungs:
        vHeight = measure(vRung["expr"])[1]
        vMiddle = vY + CELL_HEIGHT / 2
        vX = RAIL_MARGIN
        draw_node(vRung["expr"], vX, vY, vWidth, pValues, vParts)

        vCoilX = vX + vWidth * CELL_WIDTH
        vSymbol, vDetail = describe_coil(vRung)
        vLive = bool(pValues and pValues.get(vRung["target"]))
        vColor = LIVE if vLive else INK
        vParts.append(
            f'<line x1="{vCoilX}" y1="{vMiddle}" x2="{vCoilX + 40}" y2="{vMiddle}" stroke="{INK}" stroke-width="2"/>'
        )

        if vRung["kind"] in ("ton", "ctu"):
            vParts.append(
                f'<rect x="{vCoilX + 40}" y="{vMiddle - 17}" width="58" height="34" rx="4" fill="#ffffff" stroke="{vColor}" stroke-width="2"/>'
                f'<text x="{vCoilX + 69}" y="{vMiddle - 2}" text-anchor="middle" font-size="11" font-weight="bold" fill="{vColor}">{vSymbol}</text>'
                f'<text x="{vCoilX + 69}" y="{vMiddle + 11}" text-anchor="middle" font-size="10" fill="{MUTED}">{escape(vDetail)}</text>'
            )
        else:
            vParts.append(
                f'<path d="M{vCoilX + 52},{vMiddle - 12} q-10,12 0,24 M{vCoilX + 76},{vMiddle - 12} q10,12 0,24" fill="none" stroke="{vColor}" stroke-width="3"/>'
                f'<text x="{vCoilX + 64}" y="{vMiddle + 4}" text-anchor="middle" font-size="11" font-weight="bold" fill="{vColor}">{vSymbol}</text>'
            )

        vParts.append(
            f'<text x="{vCoilX + 64}" y="{vMiddle - 18}" text-anchor="middle" font-size="12" fill="{vColor}">{escape(vRung["target"])}</text>'
            f'<text x="2" y="{vY + 9}" font-size="9" fill="{MUTED}">{vRung["line"]}</text>'
        )
        vY += vHeight * CELL_HEIGHT + 12

    vTotalHeight = max(vY, 40)
    vParts.insert(
        0,
        f'<line x1="{RAIL_MARGIN}" y1="4" x2="{RAIL_MARGIN}" y2="{vTotalHeight - 4}" stroke="{INK}" stroke-width="3"/>'
        f'<line x1="{vTotalWidth - 6}" y1="4" x2="{vTotalWidth - 6}" y2="{vTotalHeight - 4}" stroke="{INK}" stroke-width="3"/>',
    )

    rSvg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vTotalWidth}" height="{vTotalHeight}" '
        f'viewBox="0 0 {vTotalWidth} {vTotalHeight}" font-family="Arial, sans-serif" '
        f'role="img" aria-label="Programme en ladder">'
        f'<rect width="{vTotalWidth}" height="{vTotalHeight}" fill="#ffffff"/>'
        + "".join(vParts)
        + "</svg>"
    )

    return rSvg
