"""Dessin SVG d'un schéma construit : composants sur la grille et fils entre bornes

Chaque case de la grille réserve à gauche un couloir vertical pour les fils, puis
le symbole, puis son libellé à droite. Entre deux lignes de cases, un couloir
horizontal accueille les fils : ils ne traversent ni symbole ni libellé.
"""

from html import escape

from job.schema_building import (
    find_wrong_wires,
    get_answer_labels,
    get_instance_id,
    get_labels,
    match_answer,
)
from job.schema_library import COMPONENTS, HEIGHT, WIDTH

# Taille de la grille des éditeurs, au bureau comme sur le web
GRID_COLUMNS = 4
GRID_ROWS = 6
CELL_WIDTH = 240
CELL_HEIGHT = 150
# Au moins la sortie d'un fil et son décalage le plus grand, pour ne rien couper
MARGIN = 36
# Place du symbole dans sa case, après le couloir vertical des fils
SYMBOL_OFFSET = 24
CORRIDOR_OFFSET = 8
LABEL_GAP = 12
LABEL_WIDTH = 17
LABEL_LINE_HEIGHT = 14
WIRE_COLOR = "#2563eb"
# Fil d'une réponse absent du schéma attendu
WRONG_WIRE_COLOR = "#dc2626"
# Place des titres au-dessus des deux schémas de la correction
HEADING_HEIGHT = 30
COLUMN_GAP = 30
# Distance entre une borne et le couloir où le fil change de direction
WIRE_EXIT = 14
# Décalage entre fils voisins, pour qu'ils ne se superposent pas
LANE_STEP = 5
LANE_COUNT = 4
# Écart vertical en deçà duquel deux bornes face à face se relient par un coude
FACING_LIMIT = 80


def get_origin(pX, pY):
    """Retourne le coin haut gauche du symbole d'un composant placé en (pX, pY)."""

    rOrigin = (MARGIN + pX * CELL_WIDTH + SYMBOL_OFFSET, MARGIN + pY * CELL_HEIGHT)

    return rOrigin


def get_port_position(pType, pPort, pOrigin):
    """Retourne la position absolue d'une borne d'un composant."""

    vX, vY = dict(COMPONENTS[pType].ports)[pPort]

    rPosition = (pOrigin[0] + vX, pOrigin[1] + vY)

    return rPosition


def get_exit(pPortY):
    """Retourne le sens de sortie d'une borne : -1 vers le haut, 1 vers le bas."""

    rDirection = -1 if pPortY < HEIGHT / 2 else 1

    return rDirection


def route_wire(pStart, pEnd, pCorridorX, pLane=0):
    """Retourne le tracé d'un fil : sortie de borne, couloirs, arrivée.

    pStart et pEnd sont des couples (position de la borne, sens de sortie).
    Deux bornes face à face dans la même colonne sont reliées tout droit ;
    pLane décale légèrement le fil pour le distinguer de ses voisins.
    """

    ((vX1, vY1), vStartExit), ((vX2, vY2), vEndExit) = pStart, pEnd

    vFacing = vStartExit != vEndExit and (vY2 - vY1) * vStartExit > 0

    if vFacing and vX1 == vX2:
        return f"M{vX1:g},{vY1:g} V{vY2:g}"

    # Bornes proches et face à face : un coude à mi-hauteur, sans passer au couloir.
    if vFacing and abs(vY2 - vY1) <= FACING_LIMIT:
        vMiddle = (vY1 + vY2) / 2 + vStartExit * pLane * LANE_STEP / 2

        return f"M{vX1:g},{vY1:g} V{vMiddle:g} H{vX2:g} V{vY2:g}"

    vShift = WIRE_EXIT + pLane * LANE_STEP
    vCorridor = pCorridorX + pLane * LANE_STEP

    rPath = (
        f"M{vX1:g},{vY1:g} V{vY1 + vStartExit * vShift:g} H{vCorridor:g} "
        f"V{vY2 + vEndExit * vShift:g} H{vX2:g} V{vY2:g}"
    )

    return rPath


def draw_wire(pEndA, pEndB, pLane=0, pWrong=False):
    """Retourne le fil entre deux bornes, et les points qui marquent ses extrémités.

    Chaque extrémité est un triplet (type, borne, origine du symbole). Le fil
    emprunte le couloir de la colonne la plus à droite des deux : il passe entre
    les colonnes sans longer les symboles de la première.
    """

    vStart = get_port_position(*pEndA)
    vEnd = get_port_position(*pEndB)
    vPath = route_wire(
        (vStart, get_exit(vStart[1] - pEndA[2][1])),
        (vEnd, get_exit(vEnd[1] - pEndB[2][1])),
        max(pEndA[2][0], pEndB[2][0]) - SYMBOL_OFFSET + CORRIDOR_OFFSET,
        pLane,
    )

    vColor = WRONG_WIRE_COLOR if pWrong else WIRE_COLOR
    vDash = ' stroke-dasharray="7 4"' if pWrong else ""

    rSvg = (
        f'<path d="{vPath}" fill="none" stroke="{vColor}" stroke-width="2.5"'
        f"{vDash}/>"
        + "".join(
            f'<circle cx="{vX:g}" cy="{vY:g}" r="3.5" fill="{vColor}"/>'
            for vX, vY in (vStart, vEnd)
        )
    )

    return rSvg


def wrap_label(pText):
    """Coupe un libellé en lignes courtes, mot par mot."""

    rLines = [""]

    for vWord in pText.split():
        if rLines[-1] and len(rLines[-1]) + len(vWord) + 1 > LABEL_WIDTH:
            rLines.append(vWord)
        else:
            rLines[-1] = f"{rLines[-1]} {vWord}".strip()

    return rLines


def draw_label(pLabel, pOrigin):
    """Retourne le nom d'un composant, à droite de son symbole."""

    vLines = wrap_label(pLabel)
    vX = pOrigin[0] + WIDTH + LABEL_GAP
    vTop = pOrigin[1] + HEIGHT / 2 - (len(vLines) - 1) * LABEL_LINE_HEIGHT / 2

    rSvg = "".join(
        f'<text x="{vX:g}" y="{vTop + vIndex * LABEL_LINE_HEIGHT + 4:g}" '
        f'font-size="12" fill="#334155">{escape(vLine)}</text>'
        for vIndex, vLine in enumerate(vLines)
    )

    return rSvg


def draw_schema(pInstances, pConnections, pWrong=frozenset()):
    """Retourne (largeur, hauteur, contenu SVG) d'un schéma, sans son cadre.

    pInstances associe à chaque identifiant (type, case (x, y), nom) ; les fils
    dont l'indice est dans pWrong sont dessinés en rouge pointillé.
    """

    vOrigins = {
        vId: get_origin(*vPosition) for vId, (_, vPosition, _) in pInstances.items()
    }
    vColumns = max(vX for _, (vX, _), _ in pInstances.values()) + 1
    vRows = max(vY for _, (_, vY), _ in pInstances.values()) + 1

    vParts = [
        draw_wire(
            (pInstances[vIdA][0], vPortA, vOrigins[vIdA]),
            (pInstances[vIdB][0], vPortB, vOrigins[vIdB]),
            vIndex % LANE_COUNT,
            vIndex in pWrong,
        )
        for vIndex, (vIdA, vPortA, vIdB, vPortB) in enumerate(pConnections)
        if vIdA in vOrigins and vIdB in vOrigins
    ]

    for vId, (vType, _, vLabel) in pInstances.items():
        vX, vY = vOrigins[vId]
        vParts.append(
            f'<g transform="translate({vX:g},{vY:g})">{COMPONENTS[vType].drawing}</g>'
            + draw_label(vLabel, (vX, vY))
        )

    rSchema = (
        2 * MARGIN + vColumns * CELL_WIDTH,
        2 * MARGIN + vRows * CELL_HEIGHT,
        "".join(vParts),
    )

    return rSchema


def wrap_svg(pWidth, pHeight, pContent, pTitle):
    """Entoure un contenu dessiné d'un SVG autonome sur fond blanc."""

    rSvg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{pWidth}" '
        f'height="{pHeight}" viewBox="0 0 {pWidth} {pHeight}" role="img" '
        f'font-family="Arial, sans-serif"><title>{escape(pTitle)}</title>'
        f'<rect width="{pWidth}" height="{pHeight}" fill="#ffffff"/>'
        f"{pContent}</svg>"
    )

    return rSvg


def get_expected_instances(pQuestion):
    """Retourne les composants attendus : (type, case, nom) par identifiant."""

    vLabels = get_labels(pQuestion["components"])

    rInstances = {
        get_instance_id(vItem): (
            vItem["type"],
            (vItem["x"], vItem["y"]),
            vLabels[get_instance_id(vItem)],
        )
        for vItem in pQuestion["components"]
    }

    return rInstances


def render_schema(pInstances, pConnections, pTitle):
    """Retourne le SVG d'un schéma : (type, case, nom) par identifiant."""

    vWidth, vHeight, vContent = draw_schema(pInstances, pConnections)

    rSvg = wrap_svg(vWidth, vHeight, vContent, pTitle)

    return rSvg


def render_expected(pQuestion):
    """Retourne le SVG du schéma attendu d'une question à construire."""

    rSvg = render_schema(
        get_expected_instances(pQuestion), pQuestion["connections"], "Schéma attendu"
    )

    return rSvg


def render_correction(pQuestion, pResponse):
    """Retourne côte à côte le schéma construit et le schéma attendu.

    Chaque composant construit porte le nom de son équivalent attendu ; les fils
    absents du schéma attendu sont en rouge pointillé.
    """

    vMatch = match_answer(pQuestion, pResponse)
    vLabels = get_answer_labels(pQuestion, vMatch)
    vAnswer = draw_schema(
        {
            vId: (vType, vMatch["positions"][vId], vLabels[vId])
            for vId, vType in vMatch["instances"].items()
        },
        vMatch["wires"],
        find_wrong_wires(vMatch),
    )
    vExpected = draw_schema(get_expected_instances(pQuestion), pQuestion["connections"])
    vShift = vAnswer[0] + COLUMN_GAP
    vWidth = vShift + vExpected[0]
    vHeight = HEADING_HEIGHT + max(vAnswer[1], vExpected[1])
    vSeparator = vShift - COLUMN_GAP / 2

    rSvg = wrap_svg(
        vWidth,
        vHeight,
        f'<g font-size="15" font-weight="bold" fill="#0f172a">'
        f'<text x="{MARGIN}" y="22">Votre schéma</text>'
        f'<text x="{vShift + MARGIN}" y="22">Schéma attendu</text></g>'
        f'<line x1="{vSeparator:g}" y1="8" x2="{vSeparator:g}" '
        f'y2="{vHeight - 8}" stroke="#cbd5e1" stroke-width="1.5"/>'
        f'<g transform="translate(0,{HEADING_HEIGHT})">{vAnswer[2]}</g>'
        f'<g transform="translate({vShift},{HEADING_HEIGHT})">{vExpected[2]}</g>',
        "Votre schéma et schéma attendu",
    )

    return rSvg


def build_editor_config(pTypes, pColumns, pRows, pLimits=None):
    """Retourne la géométrie, les symboles et les exemplaires permis de l'éditeur web.

    Les constantes viennent d'ici : le navigateur dessine comme le serveur.
    """

    rConfig = {
        "limits": {vType: (pLimits or {}).get(vType, 1) for vType in pTypes},
        "grid": {
            "columns": pColumns,
            "rows": pRows,
            "cellWidth": CELL_WIDTH,
            "cellHeight": CELL_HEIGHT,
            "margin": MARGIN,
            "symbolOffset": SYMBOL_OFFSET,
            "corridorOffset": CORRIDOR_OFFSET,
            "labelGap": LABEL_GAP,
            "labelLineHeight": LABEL_LINE_HEIGHT,
            "wireExit": WIRE_EXIT,
            "laneStep": LANE_STEP,
            "laneCount": LANE_COUNT,
            "facingLimit": FACING_LIMIT,
            "width": WIDTH,
            "height": HEIGHT,
            "wireColor": WIRE_COLOR,
        },
        "components": {
            vType: {
                "label": COMPONENTS[vType].label,
                "lines": wrap_label(COMPONENTS[vType].label),
                "drawing": COMPONENTS[vType].drawing,
                "ports": [
                    [vName, vX, vY] for vName, (vX, vY) in COMPONENTS[vType].ports
                ],
            }
            for vType in pTypes
        },
    }

    return rConfig
