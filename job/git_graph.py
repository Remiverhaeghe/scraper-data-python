"""Dessin en SVG du graphe d'un dépôt simulé, commun au bureau et au web"""

from html import escape

COLUMN_WIDTH = 78
ROW_HEIGHT = 74
MARGIN = 34
RADIUS = 15

# Une couleur par ligne du graphe ; HEAD est signalé en couleur d'accent.
LANE_COLORS = ("#2563eb", "#16a34a", "#d97706", "#9333ea", "#0891b2", "#dc2626")
HEAD_COLOR = "#0f172a"
FADED_OPACITY = "0.3"


def compute_layout(pRepository):
    """Retourne la position (colonne, ligne) de chaque commit.

    La colonne suit la profondeur depuis le premier commit ; un commit reste sur
    la ligne de son premier parent tant qu'aucun autre enfant ne l'occupe.
    """

    rLayout = {}
    vLaneTaken = set()
    vLaneCount = 0

    # L'ordre de création est un ordre topologique : les parents sont déjà placés.
    for vCommit, vData in pRepository.commits.items():
        vColumn = max((rLayout[vParent][0] + 1 for vParent in vData.parents), default=0)

        if vData.parents and vData.parents[0] not in vLaneTaken:
            vLane = rLayout[vData.parents[0]][1]
            vLaneTaken.add(vData.parents[0])
        else:
            vLane = vLaneCount
            vLaneCount += 1

        rLayout[vCommit] = (vColumn, vLane)

    return rLayout


def build_labels(pRepository):
    """Retourne l'étiquette de chaque commit : ses branches, HEAD marqué d'une *."""

    rLabels = {}

    for vName, vCommit in sorted(pRepository.branches.items()):
        vCurrent = not pRepository.detached and pRepository.head == vName
        rLabels.setdefault(vCommit, []).append(f"{vName}*" if vCurrent else vName)

    if pRepository.detached:
        rLabels.setdefault(pRepository.head, []).append("HEAD")

    return rLabels


def get_position(pLayout, pCommit):
    """Retourne le centre d'un commit dans le dessin, en pixels."""

    vColumn, vLane = pLayout[pCommit]

    rPosition = (MARGIN + vColumn * COLUMN_WIDTH, MARGIN + vLane * ROW_HEIGHT)

    return rPosition


def draw_edge(pFrom, pTo, pOpacity):
    """Retourne le lien courbe entre un parent et son enfant."""

    vMiddle = (pFrom[0] + pTo[0]) / 2

    rSvg = (
        f'<path d="M{pFrom[0]} {pFrom[1]} C{vMiddle} {pFrom[1]} '
        f'{vMiddle} {pTo[1]} {pTo[0]} {pTo[1]}" fill="none" stroke="#94a3b8" '
        f'stroke-width="2.5" opacity="{pOpacity}"/>'
    )

    return rSvg


def draw_commit(pCommit, pPosition, pColor, pIsHead, pLabels):
    """Retourne le cercle d'un commit, son identifiant et ses étiquettes."""

    vX, vY = pPosition

    rSvg = (
        f'<circle cx="{vX}" cy="{vY}" r="{RADIUS}" '
        f'fill="{pColor}" stroke="{HEAD_COLOR if pIsHead else pColor}" '
        f'stroke-width="{4 if pIsHead else 2}"/>'
        f'<text x="{vX}" y="{vY + 4}" text-anchor="middle" font-size="11" '
        f'font-weight="600" fill="#ffffff">{escape(pCommit)}</text>'
    )

    if pLabels:
        rSvg += (
            f'<text x="{vX}" y="{vY + RADIUS + 15}" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="{HEAD_COLOR}">'
            f"{escape(', '.join(pLabels))}</text>"
        )

    return rSvg


def render_graph(pRepository, pTitle):
    """Retourne le SVG du graphe ; les commits devenus invisibles sont estompés."""

    vLayout = compute_layout(pRepository)
    vPositions = {vCommit: get_position(vLayout, vCommit) for vCommit in vLayout}
    vLabels = build_labels(pRepository)
    vReachable = pRepository.reachable()
    vEdges = []
    vNodes = []

    for vCommit, vData in pRepository.commits.items():
        vPosition = vPositions[vCommit]
        vOpacity = "1" if vCommit in vReachable else FADED_OPACITY

        vEdges.extend(
            draw_edge(vPositions[vParent], vPosition, vOpacity)
            for vParent in vData.parents
        )
        vNodes.append(
            f'<g opacity="{vOpacity}">'
            + draw_commit(
                vCommit,
                vPosition,
                LANE_COLORS[vLayout[vCommit][1] % len(LANE_COLORS)],
                vCommit == pRepository.head_commit(),
                vLabels.get(vCommit),
            )
            + "</g>"
        )

    # Place à droite pour les étiquettes, en bas pour celles de la dernière ligne
    vWidth = max(vX for vX, _ in vPositions.values()) + MARGIN + 60
    vHeight = max(vY for _, vY in vPositions.values()) + MARGIN + 24

    rSvg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vWidth}" '
        f'height="{vHeight}" viewBox="0 0 {vWidth} {vHeight}" role="img" '
        f'font-family="Segoe UI, Arial, sans-serif">'
        f"<title>{escape(pTitle)}</title>"
        f'<rect width="{vWidth}" height="{vHeight}" fill="#ffffff"/>'
        + "".join(vEdges)
        + "".join(vNodes)
        + "</svg>"
    )

    return rSvg
