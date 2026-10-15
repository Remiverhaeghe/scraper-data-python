"""Schémas SVG des lots de révision : une chaîne de cadres reliés par des flèches

Le SVG produit respecte les règles de l'import : ni script, ni lien, ni image
ou police externe, fond blanc et largeur de 900 au plus.
"""

from html import escape

WIDTH = 900
TOP = 70
BOX_HEIGHT = 64
BOX_GAP = 34
MARGIN = 20

# Largeur moyenne d'un caractère en police de 15 px, pour couper les libellés
CHARACTER_WIDTH = 8.5

ARROW_DEFINITION = (
    '<defs><marker id="fleche" markerWidth="10" markerHeight="8" refX="9"'
    ' refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#334155"/>'
    "</marker></defs>"
)


def wrap_label(pText, pWidth):
    """Coupe un libellé en lignes d'au plus pWidth caractères, mot par mot."""

    rLines = [""]

    for vWord in pText.split():
        if rLines[-1] and len(rLines[-1]) + len(vWord) + 1 > pWidth:
            rLines.append(vWord)
        else:
            rLines[-1] = f"{rLines[-1]} {vWord}".strip()

    return rLines


def build_boxes(pNodes):
    """Retourne les éléments SVG des cadres et des flèches, et le centre de chaque cadre."""

    vBoxWidth = (WIDTH - 2 * MARGIN - BOX_GAP * (len(pNodes) - 1)) / len(pNodes)
    vMiddle = TOP + BOX_HEIGHT / 2
    vParts = []
    rCenters = []

    for vIndex, vNode in enumerate(pNodes):
        vX = MARGIN + vIndex * (vBoxWidth + BOX_GAP)
        rCenters.append(vX + vBoxWidth / 2)
        vParts.append(
            f'<rect x="{vX:.1f}" y="{TOP}" width="{vBoxWidth:.1f}"'
            f' height="{BOX_HEIGHT}" rx="8" fill="#e0f2fe" stroke="#0369a1"'
            ' stroke-width="2"/>'
        )
        vLines = wrap_label(vNode, max(8, int(vBoxWidth / CHARACTER_WIDTH)))
        vFirstLine = vMiddle - (len(vLines) - 1) * 9 + 5

        vParts += [
            f'<text x="{rCenters[-1]:.1f}" y="{vFirstLine + vLine * 18:.1f}"'
            ' text-anchor="middle" font-size="15" fill="#0f172a">'
            f"{escape(vText)}</text>"
            for vLine, vText in enumerate(vLines)
        ]

        if vIndex:
            vParts.append(
                f'<line x1="{vX - BOX_GAP + 2:.1f}" y1="{vMiddle}" x2="{vX - 3:.1f}"'
                f' y2="{vMiddle}" stroke="#334155" stroke-width="2"'
                ' marker-end="url(#fleche)"/>'
            )

    return vParts, rCenters


def build_chain_svg(pTitle, pNodes, pFeedback=None, pNote=None):
    """Retourne un schéma SVG : titre, cadres reliés de gauche à droite.

    pFeedback = (indice de départ, indice d'arrivée, libellé) ajoute une flèche
    de retour en pointillé sous la chaîne ; pNote ajoute une ligne de légende.
    """

    vParts, vCenters = build_boxes(pNodes)
    vBottom = TOP + BOX_HEIGHT

    if pFeedback:
        vFrom, vTo, vLabel = pFeedback
        vY = vBottom + 40
        vParts.append(
            f'<polyline points="{vCenters[vFrom]:.1f},{vBottom}'
            f" {vCenters[vFrom]:.1f},{vY} {vCenters[vTo]:.1f},{vY}"
            f' {vCenters[vTo]:.1f},{vBottom + 3}" fill="none" stroke="#b45309"'
            ' stroke-width="2" stroke-dasharray="6 4" marker-end="url(#fleche)"/>'
        )
        vParts.append(
            f'<text x="{(vCenters[vFrom] + vCenters[vTo]) / 2:.1f}" y="{vY + 22}"'
            ' text-anchor="middle" font-size="14" fill="#b45309">'
            f"{escape(vLabel)}</text>"
        )
        vBottom = vY + 30

    if pNote:
        vParts.append(
            f'<text x="{WIDTH / 2}" y="{vBottom + 26}" text-anchor="middle"'
            f' font-size="14" fill="#475569">{escape(pNote)}</text>'
        )
        vBottom += 30

    vHeight = vBottom + 30

    rSvg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}"'
            f' height="{vHeight}" viewBox="0 0 {WIDTH} {vHeight}"'
            ' font-family="Arial, sans-serif">',
            ARROW_DEFINITION,
            f'<rect width="{WIDTH}" height="{vHeight}" fill="#ffffff"/>',
            f'<text x="{WIDTH / 2}" y="34" text-anchor="middle" font-size="20"'
            f' font-weight="bold" fill="#0f172a">{escape(pTitle)}</text>',
            *vParts,
            "</svg>",
        ]
    )

    return rSvg
