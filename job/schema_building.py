"""Schémas à construire : vérification d'une question et correction d'un schéma

Un schéma se décrit par ses composants et ses liaisons, chaque liaison reliant
une borne d'un composant à une borne d'un autre. La correction compare ces
liaisons, sans tenir compte de la place des composants sur la grille. Chaque
type de composant n'apparaît qu'une fois par question : il sert d'identifiant.
"""

from itertools import product

from job.schema_library import COMPONENTS

MAX_COMPONENTS = 10
MAX_CONNECTIONS = 20
MAX_DISTRACTORS = 6
GRID_SIZE = 10

# Bornes d'un composant symétrique, interchangeables à la correction
SYMMETRIC_PORTS = ("1", "2")
# Nom commun des bornes d'un équipement à point de raccordement unique
NODE_PORT = "liaison"

# Limites d'une réponse, pour refuser un envoi démesuré
MAX_ANSWER_COMPONENTS = 16
MAX_ANSWER_WIRES = 40


def get_ports(pType):
    """Retourne les noms des bornes d'un type de composant."""

    rPorts = [vName for vName, _ in COMPONENTS[pType].ports]

    return rPorts


def is_connection(pConnection, pTypes):
    """Indique si une liaison relie deux bornes existantes de composants présents."""

    rValid = (
        isinstance(pConnection, (list, tuple))
        and len(pConnection) == 4
        and all(isinstance(vValue, str) for vValue in pConnection)
        and pConnection[0] in pTypes
        and pConnection[2] in pTypes
        and pConnection[1] in get_ports(pConnection[0])
        and pConnection[3] in get_ports(pConnection[2])
        and (pConnection[0], pConnection[1]) != (pConnection[2], pConnection[3])
    )

    return rValid


def check_components(pComponents):
    """Vérifie les composants attendus d'un schéma ; retourne le défaut, ou ""."""

    if (
        not isinstance(pComponents, list)
        or not 2 <= len(pComponents) <= MAX_COMPONENTS
        or not all(
            isinstance(vItem, dict)
            and vItem.get("type") in COMPONENTS
            and all(
                isinstance(vItem.get(vAxis), int)
                and not isinstance(vItem.get(vAxis), bool)
                and 0 <= vItem[vAxis] < GRID_SIZE
                for vAxis in ("x", "y")
            )
            for vItem in pComponents
        )
    ):
        return f"2 à {MAX_COMPONENTS} composants {{type, x, y}} connus attendus"

    vTypes = [vItem["type"] for vItem in pComponents]

    if len(set(vTypes)) != len(vTypes):
        return "chaque type de composant n'apparaît qu'une fois"

    if len({(vItem["x"], vItem["y"]) for vItem in pComponents}) != len(vTypes):
        return "deux composants occupent la même case"

    return ""


def check_construction(pQuestion):
    """Vérifie un schéma à construire ; retourne le défaut trouvé, ou ""."""

    vComponents = pQuestion["components"]
    vIssue = check_components(vComponents)

    if vIssue:
        return vIssue

    vTypes = [vItem["type"] for vItem in vComponents]
    vConnections = pQuestion["connections"]

    if (
        not isinstance(vConnections, list)
        or not 1 <= len(vConnections) <= MAX_CONNECTIONS
        or not all(is_connection(vItem, vTypes) for vItem in vConnections)
    ):
        return "liaison invalide [composant, borne, composant, borne]"

    if {vType for vItem in vConnections for vType in vItem[::2]} != set(vTypes):
        return "un composant attendu n'est relié à rien"

    vDistractors = pQuestion.get("distractors", [])

    if (
        not isinstance(vDistractors, list)
        or len(vDistractors) > MAX_DISTRACTORS
        or not all(
            vType in COMPONENTS and vType not in vTypes for vType in vDistractors
        )
    ):
        return f"au plus {MAX_DISTRACTORS} leurres connus, absents du schéma attendu"

    return ""


def read_answer(pResponse):
    """Vérifie le schéma envoyé ; retourne (types placés, positions, liaisons).

    Lève ValueError si le schéma est vide ou illisible.
    """

    if not isinstance(pResponse, dict):
        raise ValueError("Schéma illisible.")

    vComponents = pResponse.get("components")
    vWires = pResponse.get("wires", [])

    if not isinstance(vComponents, list) or not isinstance(vWires, list):
        raise ValueError("Schéma illisible.")

    if not vComponents:
        raise ValueError("Placez au moins un composant.")

    if len(vComponents) > MAX_ANSWER_COMPONENTS or len(vWires) > MAX_ANSWER_WIRES:
        raise ValueError("Schéma trop grand.")

    vPositions = {}

    for vItem in vComponents:
        if not isinstance(vItem, dict) or vItem.get("type") not in COMPONENTS:
            raise ValueError("Schéma illisible.")

        vPositions[vItem["type"]] = (
            vItem.get("x") if isinstance(vItem.get("x"), int) else 0,
            vItem.get("y") if isinstance(vItem.get("y"), int) else 0,
        )

    if len(vPositions) != len(vComponents) or not all(
        is_connection(vWire, vPositions) for vWire in vWires
    ):
        raise ValueError("Schéma illisible.")

    rAnswer = (set(vPositions), vPositions, [tuple(vWire) for vWire in vWires])

    return rAnswer


def build_edges(pConnections, pSwapped=frozenset()):
    """Retourne les liaisons sans sens, bornes des composants pSwapped inversées."""

    def port(pType, pPort):
        if COMPONENTS[pType].node:
            return NODE_PORT

        if pType in pSwapped and pPort in SYMMETRIC_PORTS:
            return SYMMETRIC_PORTS[1 - SYMMETRIC_PORTS.index(pPort)]

        return pPort

    rEdges = {
        frozenset(((vTypeA, port(vTypeA, vPortA)), (vTypeB, port(vTypeB, vPortB))))
        for vTypeA, vPortA, vTypeB, vPortB in pConnections
    }

    return rEdges


def compare_edges(pExpected, pAnswer, pTypes):
    """Retourne (liaisons manquantes, liaisons en trop) au plus près de l'attendu.

    Un composant symétrique peut avoir été branché à l'envers : on essaie les
    deux sens de chacun et l'on garde la variante la plus proche.
    """

    vExpected = build_edges(pExpected)
    vSymmetric = sorted(vType for vType in pTypes if COMPONENTS[vType].symmetric)
    rBest = None

    for vChoices in product((False, True), repeat=len(vSymmetric)):
        vSwapped = frozenset(
            vType for vType, vSwap in zip(vSymmetric, vChoices) if vSwap
        )
        vAnswer = build_edges(pAnswer, vSwapped)
        vGap = (vExpected - vAnswer, vAnswer - vExpected)

        if rBest is None or sum(map(len, vGap)) < sum(map(len, rBest)):
            rBest = vGap

        if not any(vGap):
            break

    return rBest


def describe_end(pType, pPort):
    """Décrit une extrémité de liaison ; la borne n'est citée que si elle compte."""

    vType = COMPONENTS[pType]
    vLabel = vType.label

    if len(vType.ports) > 1 and not vType.symmetric and not vType.node:
        vLabel += f" ({pPort})"

    rText = vLabel

    return rText


def describe_edge(pEdge):
    """Décrit une liaison par ses deux extrémités, dans un ordre stable."""

    rText = " – ".join(sorted(describe_end(*vEnd) for vEnd in pEdge))

    return rText


def describe_connections(pConnections):
    """Décrit les liaisons d'un schéma dans l'ordre où la question les donne."""

    rText = " ; ".join(
        f"{describe_end(vTypeA, vPortA)} – {describe_end(vTypeB, vPortB)}"
        for vTypeA, vPortA, vTypeB, vPortB in pConnections
    )

    return rText


def grade_construction(pQuestion, pResponse):
    """Corrige un schéma construit ; retourne (juste, écarts constatés, attendu)."""

    vExpectedTypes = {vItem["type"] for vItem in pQuestion["components"]}
    vTypes, _, vWires = read_answer(pResponse)
    vMissing, vExtra = compare_edges(
        pQuestion["connections"], vWires, vTypes | vExpectedTypes
    )

    vGaps = []

    for vTitle, vItems in (
        ("composants manquants", vExpectedTypes - vTypes),
        ("composants en trop", vTypes - vExpectedTypes),
    ):
        if vItems:
            vGaps.append(
                f"{vTitle} : "
                + ", ".join(sorted(COMPONENTS[vType].label for vType in vItems))
            )

    for vTitle, vEdges in (
        ("liaisons manquantes", vMissing),
        ("liaisons en trop", vExtra),
    ):
        if vEdges:
            vGaps.append(f"{vTitle} : " + ", ".join(sorted(map(describe_edge, vEdges))))

    rGrade = (
        not vGaps,
        "Schéma conforme" if not vGaps else " ; ".join(vGaps),
        describe_connections(pQuestion["connections"]),
    )

    return rGrade
