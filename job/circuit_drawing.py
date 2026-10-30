"""Dessin SVG d'un circuit simulé : fils sous tension, récepteurs en marche, mesures

Le dessin reprend la grille et les symboles de l'éditeur de schémas
(job/schema_drawing.py) et y ajoute l'état calculé par job/circuit.py.
"""

from html import escape

from job.schema_drawing import (
    HEIGHT,
    LABEL_GAP,
    LABEL_LINE_HEIGHT,
    LANE_COUNT,
    MARGIN,
    WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
    draw_label,
    draw_wire,
    get_origin,
    wrap_label,
    wrap_svg,
)
from job.schema_library import COMPONENTS

LIVE_COLOR = "#dc2626"
# Halo derrière le symbole, selon l'état : (couleur, opacité)
HALOS = {
    "lit": ("#facc15", 0.55),
    "dim": ("#fde68a", 0.45),
    "led": ("#f87171", 0.6),
    "active": ("#4ade80", 0.35),
    "fault": ("#f87171", 0.35),
}
STATUS_COLORS = {
    "lit": "#a16207",
    "dim": "#a16207",
    "led": "#b91c1c",
    "active": "#15803d",
    "fault": "#b91c1c",
    "measure": "#1d4ed8",
}


def get_instance_label(pId, pType):
    """Retourne le nom affiché d'un composant, numéroté comme dans l'éditeur."""

    vLabel = COMPONENTS[pType].label
    vSuffix = pId.rsplit("-", 1)[-1] if "-" in pId else ""

    rLabel = f"{vLabel} {vSuffix}" if vSuffix.isdigit() else vLabel

    return rLabel


def draw_halo(pTone, pOrigin):
    """Retourne le halo coloré placé derrière un symbole actif."""

    if pTone not in HALOS:
        return ""

    vColor, vOpacity = HALOS[pTone]

    rSvg = (
        f'<rect x="{pOrigin[0] + 6:g}" y="{pOrigin[1] + 14:g}" width="{WIDTH - 12}" '
        f'height="{HEIGHT - 28}" rx="18" fill="{vColor}" opacity="{vOpacity}"/>'
    )

    return rSvg


def draw_status(pPart, pLabel, pOrigin):
    """Retourne l'état d'un composant, écrit sous son nom."""

    if not pPart["status"]:
        return ""

    vLines = len(wrap_label(pLabel))
    vY = pOrigin[1] + HEIGHT / 2 + (vLines + 1) * LABEL_LINE_HEIGHT / 2 + 8
    vColor = STATUS_COLORS.get(pPart["tone"], "#475569")

    rSvg = (
        f'<text x="{pOrigin[0] + WIDTH + LABEL_GAP:g}" y="{vY:g}" font-size="12" '
        f'font-weight="bold" fill="{vColor}">{escape(pPart["status"])}</text>'
    )

    return rSvg


def get_tone(pPart):
    """Retourne la teinte d'un composant : le moteur qui tourne est vert, pas jaune."""

    rTone = pPart["tone"]

    if pPart["type"] == "moteur_mono" and rTone == "lit":
        rTone = "active"

    return rTone


def render_circuit(pComponents, pWires, pResult=None, pTitle="Circuit"):
    """Retourne le SVG d'un circuit, avec l'état simulé s'il est fourni."""

    vOrigins = {
        vItem["id"]: get_origin(vItem["x"], vItem["y"]) for vItem in pComponents
    }
    vTypes = {vItem["id"]: vItem["type"] for vItem in pComponents}
    vLive = pResult["live"] if pResult else set()
    vParts = []

    for vIndex, (vIdA, vPortA, vIdB, vPortB) in enumerate(pWires):
        if vIdA in vOrigins and vIdB in vOrigins:
            vParts.append(
                draw_wire(
                    (vTypes[vIdA], vPortA, vOrigins[vIdA]),
                    (vTypes[vIdB], vPortB, vOrigins[vIdB]),
                    vIndex % LANE_COUNT,
                    pColor=LIVE_COLOR if (vIdA, vPortA) in vLive else None,
                )
            )

    for vItem in pComponents:
        vId = vItem["id"]
        vOrigin = vOrigins[vId]
        vLabel = get_instance_label(vId, vItem["type"])
        vPart = (pResult or {}).get("parts", {}).get(vId)

        if vPart:
            vParts.append(draw_halo(get_tone(vPart), vOrigin))

        vParts.append(
            f'<g transform="translate({vOrigin[0]:g},{vOrigin[1]:g})">'
            f'{COMPONENTS[vItem["type"]].drawing}</g>' + draw_label(vLabel, vOrigin)
        )

        if vPart:
            vParts.append(
                draw_status({**vPart, "tone": get_tone(vPart)}, vLabel, vOrigin)
            )

    vColumns = max((vItem["x"] for vItem in pComponents), default=0) + 1
    vRows = max((vItem["y"] for vItem in pComponents), default=0) + 1

    rSvg = wrap_svg(
        2 * MARGIN + vColumns * CELL_WIDTH,
        2 * MARGIN + vRows * CELL_HEIGHT,
        "".join(vParts),
        pTitle,
    )

    return rSvg
