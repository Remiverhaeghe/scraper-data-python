"""Cas des schémas électriques : niveaux, circuits libres et mesures."""

from job.circuit import Circuit, format_measure
from job.circuit_drawing import render_circuit
from job.circuit_levels import build_values, get_controls
from job.circuit_levels import load_levels as load_circuit_levels
from job.circuit_levels import run_level as run_circuit_level

# Circuits libres : (nom, composants (id, x, y), fils, valeurs, commandes par étape)
FREE_CIRCUITS = (
    (
        "court-circuit sur le secteur",
        [("alimentation", 0, 0)],
        [["alimentation", "L", "alimentation", "N"]],
        {},
        [{}],
    ),
    (
        "disjoncteur qui déclenche",
        [("alimentation", 0, 0), ("disjoncteur", 1, 0)],
        [
            ["alimentation", "L", "disjoncteur", "1"],
            ["disjoncteur", "2", "alimentation", "N"],
        ],
        {},
        [{}, {"disjoncteur": False}, {"disjoncteur": True}],
    ),
    (
        "LED sans résistance",
        [("pile", 0, 0), ("led", 1, 0)],
        [["pile", "+", "led", "anode"], ["led", "cathode", "pile", "−"]],
        {"pile": 9},
        [{}],
    ),
    (
        "LED inversée et voltmètre",
        [("pile", 0, 0), ("resistance", 1, 0), ("led", 2, 0), ("voltmetre", 2, 1)],
        [
            ["pile", "+", "resistance", "1"],
            ["resistance", "2", "led", "cathode"],
            ["led", "anode", "pile", "−"],
            ["voltmetre", "1", "led", "cathode"],
            ["voltmetre", "2", "led", "anode"],
        ],
        {"pile": 5, "resistance": 220},
        [{}],
    ),
    (
        "diode et microampères",
        [("pile", 0, 0), ("amperemetre", 1, 0), ("diode", 2, 0), ("resistance", 3, 0)],
        [
            ["pile", "+", "amperemetre", "1"],
            ["amperemetre", "2", "diode", "anode"],
            ["diode", "cathode", "resistance", "1"],
            ["resistance", "2", "pile", "−"],
        ],
        {"pile": 1.5, "resistance": 100000},
        [{}],
    ),
    (
        "relais qui bat",
        [("pile", 0, 0), ("contact_relais_nf", 1, 0), ("bobine_relais", 2, 0)],
        [
            ["pile", "+", "contact_relais_nf", "1"],
            ["contact_relais_nf", "2", "bobine_relais", "1"],
            ["bobine_relais", "2", "pile", "−"],
        ],
        {"pile": 12, "bobine_relais": 12},
        [{}],
    ),
    (
        "ampèremètre en court-circuit sur la pile",
        [("pile", 0, 0), ("amperemetre", 0, 1)],
        [["pile", "+", "amperemetre", "1"], ["amperemetre", "2", "pile", "−"]],
        {"pile": 48},
        [{}],
    ),
    (
        "moteur derrière fusible et sectionneur, retour par la masse",
        [
            ("alimentation", 0, 0),
            ("fusible", 1, 0),
            ("sectionneur", 2, 0),
            ("moteur_mono", 3, 0),
            ("masse", 3, 1),
            ("relais_thermique", 0, 1),
        ],
        [
            ["alimentation", "L", "fusible", "1"],
            ["fusible", "2", "sectionneur", "1"],
            ["sectionneur", "2", "relais_thermique", "1"],
            ["relais_thermique", "2", "moteur_mono", "1"],
            ["moteur_mono", "2", "masse", "masse"],
        ],
        {},
        [{}, {"sectionneur": True}, {"fusible": False}],
    ),
    (
        "valeurs hors limites",
        [
            ("pile", 0, 0),
            ("resistance-1", 1, 0),
            ("resistance-2", 2, 0),
            ("voltmetre", 2, 1),
        ],
        [
            ["pile", "+", "resistance-1", "1"],
            ["resistance-1", "2", "resistance-2", "1"],
            ["resistance-2", "2", "pile", "−"],
            ["voltmetre", "1", "resistance-2", "1"],
            ["voltmetre", "2", "resistance-2", "2"],
        ],
        {"pile": "1000", "resistance-1": -5, "resistance-2": "abc"},
        [{}],
    ),
    (
        "lampe et moteur en série",
        [("alimentation", 0, 0), ("lampe_bornes-1", 1, 0), ("lampe_bornes-2", 2, 0)]
        + [("moteur_mono", 3, 0), ("va_et_vient", 1, 1), ("bouton_arret", 2, 1)],
        [
            ["alimentation", "L", "bouton_arret", "1"],
            ["bouton_arret", "2", "va_et_vient", "commun"],
            ["va_et_vient", "a", "lampe_bornes-1", "1"],
            ["lampe_bornes-1", "2", "lampe_bornes-2", "1"],
            ["lampe_bornes-2", "2", "alimentation", "N"],
            ["va_et_vient", "b", "moteur_mono", "1"],
            ["moteur_mono", "2", "lampe_bornes-2", "1"],
        ],
        {},
        [{}, {"va_et_vient": True}, {"bouton_arret": True}],
    ),
    (
        "Zener en direct, puis en inverse sans résistance",
        [("pile-1", 0, 0), ("zener-1", 1, 0), ("pile-2", 0, 1), ("zener-2", 1, 1)],
        [
            ["pile-1", "+", "zener-1", "anode"],
            ["zener-1", "cathode", "pile-1", "−"],
            ["pile-2", "+", "zener-2", "cathode"],
            ["zener-2", "anode", "pile-2", "−"],
            ["pile-1", "−", "pile-2", "−"],
        ],
        {"pile-1": 1.5, "pile-2": 12, "zener-2": "6.8"},
        [{}],
    ),
    (
        "base sans résistance et collecteur en l'air",
        [("pile-1", 0, 0), ("transistor_npn-1", 1, 0)]
        + [("pile-2", 0, 1), ("resistance", 1, 1), ("transistor_npn-2", 2, 1)],
        [
            ["pile-1", "+", "transistor_npn-1", "base"],
            ["transistor_npn-1", "émetteur", "pile-1", "−"],
            ["pile-2", "+", "resistance", "1"],
            ["resistance", "2", "transistor_npn-2", "base"],
            ["transistor_npn-2", "émetteur", "pile-2", "−"],
        ],
        {"pile-1": 5, "pile-2": 5, "resistance": 4700},
        [{}],
    ),
    (
        "buzzer à l'envers et potentiomètre en butée sur une LED",
        [("pile", 0, 0), ("buzzer", 1, 0), ("potentiometre", 2, 0), ("led", 3, 0)],
        [
            ["pile", "+", "buzzer", "−"],
            ["buzzer", "+", "pile", "−"],
            ["pile", "+", "potentiometre", "1"],
            ["potentiometre", "curseur", "led", "anode"],
            ["led", "cathode", "pile", "−"],
        ],
        {"pile": 9, "potentiometre": 99.5},
        [{}],
    ),
    (
        "capteurs manœuvrés et transistor en régime linéaire",
        [("pile", 0, 0), ("ldr", 1, 0), ("ctn", 2, 0), ("transistor_npn", 1, 1)]
        + [("resistance-1", 2, 1), ("buzzer", 3, 1), ("amperemetre", 3, 0)],
        [
            ["pile", "+", "ctn", "1"],
            ["ctn", "2", "resistance-1", "1"],
            ["resistance-1", "2", "transistor_npn", "base"],
            ["transistor_npn", "base", "ldr", "1"],
            ["ldr", "2", "pile", "−"],
            ["pile", "+", "amperemetre", "1"],
            ["amperemetre", "2", "buzzer", "+"],
            ["buzzer", "−", "transistor_npn", "collecteur"],
            ["transistor_npn", "émetteur", "pile", "−"],
        ],
        {"pile": 9, "resistance-1": 220000},
        [{}, {"ldr": False}, {"ldr": False, "ctn": True}, {"ctn": True}],
    ),
)
MEASURES = (
    0.0,
    -0.0004,
    0.0005,
    4e-07,
    0.0009996,
    -0.000123456,
    0.001,
    0.0125,
    0.375,
    1.125,
    1.5e-06,
    1e-09,
    3.3333333,
    -2.5,
    12.345,
    99.95,
    99.96,
    100.0,
    229.5,
    230.5,
    0.9995,
    1234567.0,
)


def to_json(pResult):
    """Retourne le résultat d'une simulation de circuit, bornes sous tension en liste."""

    rResult = {**pResult, "live": sorted([list(vKey) for vKey in pResult["live"]])}

    return rResult


def build_circuit_level_case(pLevel, pName, pComponents, pWires, pRaw):
    """Joue un niveau de circuit : vérifications, état final et dessin simulé."""

    vValues = build_values(
        pComponents, pRaw, pLevel.get("values"), pLevel.get("editable", [])
    )
    vRun = run_circuit_level(pLevel, pComponents, pWires, vValues)

    rCase = {
        "name": f"{pLevel['id']} : {pName}",
        "level": pLevel["id"],
        "components": pComponents,
        "wires": pWires,
        "raw": pRaw,
        "values": vValues,
        "run": {**vRun, "result": to_json(vRun["result"])},
        "svg": render_circuit(pComponents, pWires, vRun["result"]),
    }

    return rCase


def build_level_cases():
    """Retourne les cas des niveaux : solution et erreurs classiques."""

    rCases = []

    for vLevel in load_circuit_levels().values():
        vComponents = vLevel["solution_components"]
        vWires = vLevel["solution_wires"]
        vRaw = vLevel.get("solution_values", {})
        vVariants = [
            ("solution", vWires, vRaw),
            ("sans le dernier fil", vWires[:-1], vRaw),
            ("sans fil", [], {}),
        ]

        if vLevel.get("editable"):
            vVariants.append(
                ("valeurs extrêmes", vWires, dict.fromkeys(vLevel["editable"], 1e9))
            )

        rCases += [
            build_circuit_level_case(vLevel, vName, vComponents, vWires, vRaw)
            for vName, vWires, vRaw in vVariants
        ]

    return rCases


def build_free_cases():
    """Retourne les cas des circuits libres, simulés étape par étape."""

    rCases = []

    for vName, vParts, vWires, vRaw, vSteps in FREE_CIRCUITS:
        vComponents = [
            {"id": vId, "type": vId.split("-")[0], "x": vX, "y": vY}
            for vId, vX, vY in vParts
        ]
        vValues = build_values(vComponents, vRaw)
        vCircuit = Circuit(vComponents, vWires, vValues)
        vMemory = None
        vResults = []

        for vInputs in vSteps:
            vResult = vCircuit.simulate(vInputs, vMemory)
            vMemory = vResult["memory"]
            vResults.append(to_json(vResult))

        rCases.append(
            {
                "name": vName,
                "components": vComponents,
                "wires": vWires,
                "raw": vRaw,
                "values": vValues,
                "steps": vSteps,
                "results": vResults,
                "plain": render_circuit(vComponents, vWires, pTitle=vName),
                "svg": render_circuit(vComponents, vWires, vResult),
                "controls": [list(vControl) for vControl in get_controls(vComponents)],
            }
        )

    return rCases


def build_circuit_cases():
    """Retourne les cas de circuits : niveaux, circuits libres et mesures."""

    rCases = {
        "levels": build_level_cases(),
        "free": build_free_cases(),
        "measures": [
            [vValue, format_measure(vValue, "V"), format_measure(vValue, "A")]
            for vValue in MEASURES
        ],
    }

    return rCases
