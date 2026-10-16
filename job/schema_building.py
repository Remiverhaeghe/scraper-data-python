"""Schémas à construire : vérification d'une question et correction d'un schéma

Un schéma se décrit par ses composants et ses liaisons, chaque liaison reliant
une borne d'un composant à une borne d'un autre. Chaque composant a son propre
identifiant ; sans identifiant, c'est son type qui en tient lieu.

L'apprenant ne sait pas quel vérin la question appelle « v1 » : la correction
cherche la correspondance entre ses composants et ceux attendus, de même type,
qui laisse le moins d'écarts. Elle essaie aussi les deux sens de chaque composant
symétrique, et ne tient pas compte de la place des composants sur la grille.
"""

import re
from collections import Counter
from itertools import permutations, product
from math import factorial

from job.schema_library import COMPONENTS

MAX_COMPONENTS = 12
MAX_CONNECTIONS = 24
MAX_DISTRACTORS = 6
GRID_SIZE = 10
MAX_LABEL_LENGTH = 40
ID_PATTERN = re.compile(r"[a-z0-9_-]{1,40}")

# Plafond des combinaisons essayées à la correction : correspondances entre
# composants de même type, multipliées par les deux sens des symétriques.
MAX_SEARCH = 20_000

# Bornes d'un composant symétrique, interchangeables à la correction
SYMMETRIC_PORTS = ("1", "2")
# Nom commun des bornes d'un équipement à point de raccordement unique
NODE_PORT = "liaison"
# Marque d'un composant de la réponse sans équivalent dans le schéma attendu
EXTRA = "en trop"

# Limites d'une réponse, pour refuser un envoi démesuré
MAX_ANSWER_COMPONENTS = 16
MAX_ANSWER_WIRES = 40


def get_ports(pType):
    """Retourne les noms des bornes d'un type de composant."""

    rPorts = [vName for vName, _ in COMPONENTS[pType].ports]

    return rPorts


def get_instance_id(pItem):
    """Retourne l'identifiant d'un composant, son type à défaut."""

    rId = pItem.get("id", pItem.get("type"))

    return rId


def get_instances(pComponents):
    """Retourne le type de chaque composant, par identifiant."""

    rInstances = {get_instance_id(vItem): vItem["type"] for vItem in pComponents}

    return rInstances


def is_connection(pConnection, pInstances):
    """Indique si une liaison relie deux bornes existantes de composants présents."""

    rValid = (
        isinstance(pConnection, (list, tuple))
        and len(pConnection) == 4
        and all(isinstance(vValue, str) for vValue in pConnection)
        and pConnection[0] in pInstances
        and pConnection[2] in pInstances
        and pConnection[1] in get_ports(pInstances[pConnection[0]])
        and pConnection[3] in get_ports(pInstances[pConnection[2]])
        and (pConnection[0], pConnection[1]) != (pConnection[2], pConnection[3])
    )

    return rValid


def count_search(pTypes):
    """Retourne le nombre de combinaisons qu'essaiera la correction."""

    rCount = 2 ** sum(COMPONENTS[vType].symmetric for vType in pTypes)

    for vCount in Counter(pTypes).values():
        rCount *= factorial(vCount)

    return rCount


def is_component(pItem):
    """Indique si un composant attendu est bien formé : type, case, nom facultatif."""

    rValid = (
        isinstance(pItem, dict)
        and pItem.get("type") in COMPONENTS
        and isinstance(get_instance_id(pItem), str)
        and ID_PATTERN.fullmatch(get_instance_id(pItem)) is not None
        and all(
            isinstance(pItem.get(vAxis), int)
            and not isinstance(pItem.get(vAxis), bool)
            and 0 <= pItem[vAxis] < GRID_SIZE
            for vAxis in ("x", "y")
        )
        and (
            "label" not in pItem
            or (
                isinstance(pItem["label"], str)
                and 0 < len(pItem["label"].strip()) <= MAX_LABEL_LENGTH
            )
        )
    )

    return rValid


def check_components(pComponents):
    """Vérifie les composants attendus d'un schéma ; retourne le défaut, ou ""."""

    if (
        not isinstance(pComponents, list)
        or not 2 <= len(pComponents) <= MAX_COMPONENTS
        or not all(is_component(vItem) for vItem in pComponents)
    ):
        return f"2 à {MAX_COMPONENTS} composants {{type, x, y}} connus attendus"

    if len(get_instances(pComponents)) != len(pComponents):
        return "deux composants ont le même identifiant"

    if len({(vItem["x"], vItem["y"]) for vItem in pComponents}) != len(pComponents):
        return "deux composants occupent la même case"

    if count_search([vItem["type"] for vItem in pComponents]) > MAX_SEARCH:
        return "trop de composants identiques ou symétriques à départager"

    return ""


def check_construction(pQuestion):
    """Vérifie un schéma à construire ; retourne le défaut trouvé, ou ""."""

    vComponents = pQuestion["components"]
    vIssue = check_components(vComponents)

    if vIssue:
        return vIssue

    vInstances = get_instances(vComponents)
    vConnections = pQuestion["connections"]

    if (
        not isinstance(vConnections, list)
        or not 1 <= len(vConnections) <= MAX_CONNECTIONS
        or not all(is_connection(vItem, vInstances) for vItem in vConnections)
    ):
        return "liaison invalide [composant, borne, composant, borne]"

    if {vId for vItem in vConnections for vId in vItem[::2]} != set(vInstances):
        return "un composant attendu n'est relié à rien"

    vDistractors = pQuestion.get("distractors", [])

    if (
        not isinstance(vDistractors, list)
        or len(vDistractors) > MAX_DISTRACTORS
        or not all(
            vType in COMPONENTS and vType not in vInstances.values()
            for vType in vDistractors
        )
    ):
        return f"au plus {MAX_DISTRACTORS} leurres connus, absents du schéma attendu"

    return ""


def get_palette_limits(pQuestion):
    """Retourne combien d'exemplaires de chaque type la palette permet de poser."""

    rLimits = Counter(vItem["type"] for vItem in pQuestion["components"])
    rLimits.update(pQuestion.get("distractors", []))

    return dict(rLimits)


def get_labels(pComponents):
    """Retourne le nom affiché de chaque composant : le sien, ou son type numéroté."""

    vCounts = Counter(vItem["type"] for vItem in pComponents)
    vSeen = Counter()
    rLabels = {}

    for vItem in pComponents:
        vSeen[vItem["type"]] += 1
        vLabel = COMPONENTS[vItem["type"]].label

        if vCounts[vItem["type"]] > 1:
            vLabel += f" {vSeen[vItem['type']]}"

        rLabels[get_instance_id(vItem)] = vItem.get("label", vLabel)

    return rLabels


def read_answer(pResponse, pLimits=None):
    """Vérifie le schéma envoyé ; retourne (types par identifiant, cases, liaisons).

    pLimits plafonne le nombre d'exemplaires de chaque type, comme la palette.
    Lève ValueError si le schéma est vide, illisible ou démesuré.
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

    vInstances = {}
    vPositions = {}

    for vItem in vComponents:
        if (
            not isinstance(vItem, dict)
            or vItem.get("type") not in COMPONENTS
            or not isinstance(get_instance_id(vItem), str)
            or not ID_PATTERN.fullmatch(get_instance_id(vItem))
        ):
            raise ValueError("Schéma illisible.")

        vId = get_instance_id(vItem)
        vInstances[vId] = vItem["type"]
        # Case bornée à la grille : un envoi forgé ne grossit pas le dessin.
        vPositions[vId] = tuple(
            (
                min(max(vItem[vAxis], 0), GRID_SIZE - 1)
                if isinstance(vItem.get(vAxis), int)
                else 0
            )
            for vAxis in ("x", "y")
        )

    if len(vInstances) != len(vComponents) or not all(
        is_connection(vWire, vInstances) for vWire in vWires
    ):
        raise ValueError("Schéma illisible.")

    for vType, vCount in Counter(vInstances.values()).items():
        if pLimits is not None and vCount > pLimits.get(vType, 0):
            raise ValueError(f"Trop de composants : {COMPONENTS[vType].label}.")

    rAnswer = (vInstances, vPositions, [tuple(vWire) for vWire in vWires])

    return rAnswer


def iterate_mappings(pAnswer, pExpected):
    """Énumère les correspondances entre composants de la réponse et attendus.

    Chaque composant de la réponse va vers un composant attendu de même type,
    au plus un par composant ; ceux qui restent sans équivalent sont en trop.
    """

    vChoices = []

    for vType in set(pAnswer.values()):
        vAnswerIds = sorted(vId for vId, vKind in pAnswer.items() if vKind == vType)
        vExpectedIds = sorted(vId for vId, vKind in pExpected.items() if vKind == vType)

        if len(vAnswerIds) <= len(vExpectedIds):
            vChoices.append(
                [
                    dict(zip(vAnswerIds, vTargets))
                    for vTargets in permutations(vExpectedIds, len(vAnswerIds))
                ]
            )
        else:
            vChoices.append(
                [
                    dict(zip(vSources, vExpectedIds))
                    for vSources in permutations(vAnswerIds, len(vExpectedIds))
                ]
            )

    for vCombination in product(*vChoices):
        rMapping = {}

        for vPart in vCombination:
            rMapping.update(vPart)

        yield rMapping


def build_edges(pConnections, pInstances, pMapping=None, pSwapped=frozenset()):
    """Retourne les liaisons sans sens, exprimées dans les identifiants attendus.

    pMapping traduit les identifiants de la réponse ; un composant sans
    équivalent devient (EXTRA, identifiant). Les bornes des composants de
    pSwapped sont inversées, celles d'un point de raccordement unique fusionnées.
    """

    def end(pId, pPort):
        vType = COMPONENTS[pInstances[pId]]

        if vType.node:
            vPort = NODE_PORT
        elif pId in pSwapped and pPort in SYMMETRIC_PORTS:
            vPort = SYMMETRIC_PORTS[1 - SYMMETRIC_PORTS.index(pPort)]
        else:
            vPort = pPort

        vId = pId if pMapping is None else pMapping.get(pId, (EXTRA, pId))

        return (vId, vPort)

    rEdges = {
        frozenset((end(vIdA, vPortA), end(vIdB, vPortB)))
        for vIdA, vPortA, vIdB, vPortB in pConnections
    }

    return rEdges


def iterate_matches(pQuestion, pInstances, pWires):
    """Énumère (correspondance, retournés, manquantes, en trop) de chaque combinaison."""

    vExpectedInstances = get_instances(pQuestion["components"])
    vExpected = build_edges(pQuestion["connections"], vExpectedInstances)

    for vMapping in iterate_mappings(pInstances, vExpectedInstances):
        vSymmetric = sorted(
            vId for vId in vMapping if COMPONENTS[pInstances[vId]].symmetric
        )

        for vChoices in product((False, True), repeat=len(vSymmetric)):
            vSwapped = frozenset(
                vId for vId, vSwap in zip(vSymmetric, vChoices) if vSwap
            )
            vAnswer = build_edges(pWires, pInstances, vMapping, vSwapped)

            yield (vMapping, vSwapped, vExpected - vAnswer, vAnswer - vExpected)


def match_answer(pQuestion, pResponse):
    """Lit une réponse et la rapproche au mieux du schéma attendu.

    Retourne un dictionnaire : types par identifiant, cases, liaisons de la
    réponse, correspondance retenue, composants retournés, liaisons manquantes
    et en trop. Lève ValueError si la réponse est illisible.
    """

    vInstances, vPositions, vWires = read_answer(
        pResponse, get_palette_limits(pQuestion)
    )
    vBest = min(
        iterate_matches(pQuestion, vInstances, vWires),
        key=lambda pMatch: len(pMatch[2]) + len(pMatch[3]),
    )

    rMatch = {
        "instances": vInstances,
        "positions": vPositions,
        "wires": vWires,
        "mapping": vBest[0],
        "swapped": vBest[1],
        "missing": vBest[2],
        "extra": vBest[3],
    }

    return rMatch


def find_wrong_wires(pMatch):
    """Retourne les indices des fils d'une réponse absents du schéma attendu."""

    rIndexes = {
        vIndex
        for vIndex, vWire in enumerate(pMatch["wires"])
        if build_edges(
            [vWire], pMatch["instances"], pMatch["mapping"], pMatch["swapped"]
        )
        <= pMatch["extra"]
    }

    return rIndexes


def get_answer_labels(pQuestion, pMatch):
    """Retourne le nom de chaque composant de la réponse : celui de son équivalent."""

    vLabels = get_labels(pQuestion["components"])

    rLabels = {
        vId: (
            vLabels[pMatch["mapping"][vId]]
            if vId in pMatch["mapping"]
            else COMPONENTS[vType].label
        )
        for vId, vType in pMatch["instances"].items()
    }

    return rLabels


def describe_end(pEnd, pLabels, pExpectedTypes, pAnswerTypes=None):
    """Décrit une extrémité de liaison ; la borne n'est citée que si elle compte.

    pLabels et pExpectedTypes décrivent les composants attendus, pAnswerTypes
    ceux de la réponse restés en trop.
    """

    vId, vPort = pEnd

    if isinstance(vId, tuple):
        vType = COMPONENTS[pAnswerTypes[vId[1]]]
        vLabel = vType.label
    else:
        vType = COMPONENTS[pExpectedTypes[vId]]
        vLabel = pLabels[vId]

    if len(vType.ports) > 1 and not vType.symmetric and not vType.node:
        vLabel += f" ({vPort})"

    rText = vLabel

    return rText


def describe_edge(pEdge, pLabels, pExpectedTypes, pAnswerTypes):
    """Décrit une liaison par ses deux extrémités, dans un ordre stable."""

    rText = " – ".join(
        sorted(
            describe_end(vEnd, pLabels, pExpectedTypes, pAnswerTypes) for vEnd in pEdge
        )
    )

    return rText


def describe_connections(pQuestion):
    """Décrit les liaisons attendues dans l'ordre où la question les donne."""

    vLabels = get_labels(pQuestion["components"])
    vTypes = get_instances(pQuestion["components"])

    rText = " ; ".join(
        describe_end((vIdA, vPortA), vLabels, vTypes)
        + " – "
        + describe_end((vIdB, vPortB), vLabels, vTypes)
        for vIdA, vPortA, vIdB, vPortB in pQuestion["connections"]
    )

    return rText


def grade_construction(pQuestion, pResponse):
    """Corrige un schéma construit ; retourne (juste, écarts constatés, attendu)."""

    vMatch = match_answer(pQuestion, pResponse)
    vLabels = get_labels(pQuestion["components"])
    vExpectedTypes = get_instances(pQuestion["components"])
    vMapped = set(vMatch["mapping"].values())

    vGaps = []

    for vTitle, vNames in (
        (
            "composants manquants",
            [vLabel for vId, vLabel in vLabels.items() if vId not in vMapped],
        ),
        (
            "composants en trop",
            [
                COMPONENTS[vType].label
                for vId, vType in vMatch["instances"].items()
                if vId not in vMatch["mapping"]
            ],
        ),
    ):
        if vNames:
            vGaps.append(f"{vTitle} : " + ", ".join(sorted(vNames)))

    for vTitle, vEdges in (
        ("liaisons manquantes", vMatch["missing"]),
        ("liaisons en trop", vMatch["extra"]),
    ):
        if vEdges:
            vGaps.append(
                f"{vTitle} : "
                + ", ".join(
                    sorted(
                        describe_edge(
                            vEdge, vLabels, vExpectedTypes, vMatch["instances"]
                        )
                        for vEdge in vEdges
                    )
                )
            )

    rGrade = (
        not vGaps,
        "Schéma conforme" if not vGaps else " ; ".join(vGaps),
        describe_connections(pQuestion),
    )

    return rGrade
