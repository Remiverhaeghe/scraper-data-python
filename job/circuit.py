"""Simulateur de circuits : analyse nodale en courant continu, relais et défauts

Le schéma est celui de l'éditeur de schémas : des composants et des fils tirés
de borne à borne. Les bornes reliées forment des nœuds ; chaque composant
devient une conductance, éventuellement avec une source. Le système G·V = I est
résolu par élimination de Gauss, sans dépendance.

Les relais et le télérupteur se règlent par itérations : on calcule, on met à
jour les contacts d'après les bobines, puis on recommence jusqu'à un état
stable. L'état précédent sert de départ : c'est ce qui permet l'auto-maintien.
Le 230 V est traité comme une tension continue de même valeur efficace : les
charges sont résistives, les puissances et les courants restent justes.
"""

from job.schema_library import COMPONENTS

SIMULATED_TYPES = (
    "alimentation",
    "pile",
    "masse",
    "disjoncteur",
    "fusible",
    "sectionneur",
    "interrupteur",
    "bouton_marche",
    "bouton_arret",
    "va_et_vient",
    "bobine_relais",
    "contact_relais",
    "contact_relais_nf",
    "contacteur",
    "relais_thermique",
    "telerupteur",
    "contact_telerupteur",
    "lampe_bornes",
    "moteur_mono",
    "resistance",
    "led",
    "diode",
    "voltmetre",
    "amperemetre",
)

# Commandes manœuvrées par l'utilisateur et leur état de repos
OPERABLE_DEFAULTS = {
    "disjoncteur": True,
    "fusible": True,
    "sectionneur": False,
    "interrupteur": False,
    "bouton_marche": False,
    "bouton_arret": False,
    "va_et_vient": False,
}
PUSH_BUTTONS = ("bouton_marche", "bouton_arret")
PROTECTIONS = ("disjoncteur", "fusible")
SOURCES = ("alimentation", "pile")
# Récepteurs résistifs : lampe et moteur d'après leur puissance sous 230 V
LOAD_WATTS = {"lampe_bornes": 60.0, "moteur_mono": 750.0}
LOADS = (
    "lampe_bornes",
    "moteur_mono",
    "resistance",
    "bobine_relais",
    "telerupteur",
    "voltmetre",
)

# Valeur réglable : (défaut, minimum, maximum, unité)
VALUE_RANGES = {
    "pile": (9.0, 1.5, 48.0, "V"),
    "resistance": (1000.0, 1.0, 1_000_000.0, "Ω"),
    "bobine_relais": (230.0, 5.0, 230.0, "V"),
    "telerupteur": (230.0, 5.0, 230.0, "V"),
}

MAINS_VOLTS = 230.0
MAINS_RESISTANCE = 0.05
MAINS_MAX_CURRENT = 63.0
BATTERY_RESISTANCE = 0.5
BATTERY_MAX_CURRENT = 3.0
CLOSED_RESISTANCE = 0.01
GMIN = 1e-9
PROTECTION_RATING = 10.0
COIL_WATTS = 8.0
# Une bobine colle au-delà de 70 % de sa tension nominale
PICKUP_RATIO = 0.7
LED_FORWARD = 2.0
LED_SERIES = 5.0
LED_NOMINAL_CURRENT = 0.02
LED_MAX_CURRENT = 0.03
LED_LIT_CURRENT = 0.002
DIODE_FORWARD = 0.7
DIODE_SERIES = 0.5
VOLTMETER_RESISTANCE = 1e7
LIVE_VOLTS = 1.0
FULL_RATIO = 0.6
DIM_RATIO = 0.1
MAX_ITERATIONS = 40
# En deçà, le courant n'est que la fuite du calcul (GMIN) : la mesure s'affiche nulle
MEASURE_FLOOR = 1e-6


def get_value(pType, pId, pValues):
    """Retourne la valeur réglée d'un composant, bornée, ou sa valeur par défaut."""

    vDefault, vMinimum, vMaximum, _ = VALUE_RANGES[pType]
    vValue = pValues.get(pId, vDefault)

    try:
        vValue = float(vValue)

    except (TypeError, ValueError):
        vValue = vDefault

    rValue = min(max(vValue, vMinimum), vMaximum)

    return rValue


def build_nets(pComponents, pWires):
    """Retourne le numéro de nœud de chaque borne (id, borne) d'après les fils."""

    vParents = {}

    def find(pKey):
        while vParents[pKey] != pKey:
            vParents[pKey] = vParents[vParents[pKey]]
            pKey = vParents[pKey]

        return pKey

    for vItem in pComponents:
        for vPort, _ in COMPONENTS[vItem["type"]].ports:
            vParents[(vItem["id"], vPort)] = (vItem["id"], vPort)

    for vIdA, vPortA, vIdB, vPortB in pWires:
        if (vIdA, vPortA) in vParents and (vIdB, vPortB) in vParents:
            vParents[find((vIdA, vPortA))] = find((vIdB, vPortB))

    vNumbers = {}
    rNets = {}

    for vKey in vParents:
        rNets[vKey] = vNumbers.setdefault(find(vKey), len(vNumbers))

    return rNets


def solve(pMatrix, pVector):
    """Résout le système linéaire par élimination de Gauss avec pivot partiel."""

    vSize = len(pVector)
    vRows = [pMatrix[vIndex][:] + [pVector[vIndex]] for vIndex in range(vSize)]

    for vColumn in range(vSize):
        vPivot = max(
            range(vColumn, vSize),
            key=lambda pRow, pColumn=vColumn: abs(vRows[pRow][pColumn]),
        )
        vRows[vColumn], vRows[vPivot] = vRows[vPivot], vRows[vColumn]
        vDivisor = vRows[vColumn][vColumn]

        if vDivisor == 0:
            continue

        for vRow in range(vColumn + 1, vSize):
            vFactor = vRows[vRow][vColumn] / vDivisor

            if vFactor:
                vTarget = vRows[vRow]
                vSource = vRows[vColumn]

                for vIndex in range(vColumn, vSize + 1):
                    vTarget[vIndex] -= vFactor * vSource[vIndex]

    rSolution = [0.0] * vSize

    for vRow in range(vSize - 1, -1, -1):
        vSum = vRows[vRow][vSize] - sum(
            vRows[vRow][vIndex] * rSolution[vIndex] for vIndex in range(vRow + 1, vSize)
        )
        rSolution[vRow] = vSum / vRows[vRow][vRow] if vRows[vRow][vRow] else 0.0

    return rSolution


def format_measure(pValue, pUnit):
    """Retourne une mesure lisible en français : 230 V, 3,33 V, 14,7 mA, 8 µA."""

    vValue = abs(pValue)

    # Arrondi avant le choix de l'unité : 0,9996 A s'écrit 1 A, pas 1e+03 mA
    if vValue < 100:
        vValue = float(f"{vValue:.3g}")

    if vValue < MEASURE_FLOOR:
        vText, vUnit = "0", pUnit
    elif vValue < 0.001:
        vText, vUnit = f"{vValue * 1e6:.3g}", "µ" + pUnit
    elif vValue < 1:
        vText, vUnit = f"{vValue * 1000:.3g}", "m" + pUnit
    elif vValue >= 100:
        vText, vUnit = f"{vValue:.0f}", pUnit
    else:
        vText, vUnit = f"{vValue:.3g}", pUnit

    rText = f"{'-' if pValue < 0 and vText != '0' else ''}{vText} {vUnit}".replace(
        ".", ","
    )

    return rText


class Circuit:
    """Un schéma prêt à simuler : composants, nœuds, valeurs réglées."""

    def __init__(self, pComponents, pWires, pValues=None):
        """Garde les composants simulables et calcule les nœuds."""
        self.components = [
            vItem for vItem in pComponents if vItem["type"] in SIMULATED_TYPES
        ]
        self.types = {vItem["id"]: vItem["type"] for vItem in self.components}
        self.values = pValues or {}
        self.nets = build_nets(self.components, pWires)
        self.ground = self.find_ground()
        self.coil = self.find_first("bobine_relais")
        self.remote = self.find_first("telerupteur")

    def find_first(self, pType):
        """Retourne le premier composant d'un type, celui que suivent les contacts."""

        rId = next(
            (vId for vId in sorted(self.types) if self.types[vId] == pType), None
        )

        return rId

    def find_ground(self):
        """Retourne le nœud de référence : neutre, masse, sinon moins d'une pile."""

        for vType, vPort in (("alimentation", "N"), ("masse", "masse"), ("pile", "−")):
            vId = self.find_first(vType)

            if vId is not None:
                return self.nets[(vId, vPort)]

        rGround = 0

        return rGround

    def get_ports(self, pId):
        """Retourne les nœuds des bornes d'un composant, dans l'ordre de la bibliothèque."""

        rNets = [
            self.nets[(pId, vPort)] for vPort, _ in COMPONENTS[self.types[pId]].ports
        ]

        return rNets

    def is_closed(self, pId, pInputs, pState):
        """Indique si l'élément de coupure d'un composant laisse passer le courant."""

        vType = self.types[pId]
        vInput = pInputs.get(pId, OPERABLE_DEFAULTS.get(vType, False))

        if vType in PROTECTIONS:
            rClosed = bool(vInput) and pId not in pState["tripped"]
        elif vType == "bouton_arret":
            rClosed = not vInput
        elif vType in ("contact_relais", "contacteur"):
            rClosed = bool(self.coil and pState["coils"].get(self.coil))
        elif vType == "contact_relais_nf":
            rClosed = not (self.coil and pState["coils"].get(self.coil))
        elif vType == "contact_telerupteur":
            rClosed = bool(self.remote and pState["latches"].get(self.remote))
        elif vType in ("relais_thermique", "amperemetre"):
            rClosed = True
        else:
            rClosed = bool(vInput)

        return rClosed

    def build_branches(self, pInputs, pState):
        """Retourne les branches : (id, nœud a, nœud b, conductance, f.é.m.)."""

        rBranches = []

        for vId, vType in self.types.items():
            vPorts = self.get_ports(vId)

            if vType == "alimentation":
                rBranches.append(
                    (vId, vPorts[0], vPorts[1], 1 / MAINS_RESISTANCE, MAINS_VOLTS)
                )
            elif vType == "pile":
                rBranches.append(
                    (
                        vId,
                        vPorts[0],
                        vPorts[1],
                        1 / BATTERY_RESISTANCE,
                        get_value("pile", vId, self.values),
                    )
                )
            elif vType == "masse":
                rBranches.append(
                    (vId, vPorts[0], self.ground, 1 / CLOSED_RESISTANCE, 0.0)
                )
            elif vType == "va_et_vient":
                vSide = vPorts[1] if pInputs.get(vId) else vPorts[0]
                rBranches.append((vId, vPorts[2], vSide, 1 / CLOSED_RESISTANCE, 0.0))
            elif vType in ("led", "diode"):
                if pState["diodes"].get(vId):
                    vForward, vSeries = (
                        (LED_FORWARD, LED_SERIES)
                        if vType == "led"
                        else (DIODE_FORWARD, DIODE_SERIES)
                    )
                    rBranches.append((vId, vPorts[0], vPorts[1], 1 / vSeries, vForward))
            elif vType in LOADS:
                rBranches.append(
                    (vId, vPorts[0], vPorts[1], 1 / self.get_resistance(vId), 0.0)
                )
            elif self.is_closed(vId, pInputs, pState):
                rBranches.append(
                    (vId, vPorts[0], vPorts[1], 1 / CLOSED_RESISTANCE, 0.0)
                )

        return rBranches

    def get_resistance(self, pId):
        """Retourne la résistance d'un récepteur, d'après sa puissance ou sa valeur."""

        vType = self.types[pId]

        if vType == "resistance":
            rResistance = get_value("resistance", pId, self.values)
        elif vType in ("bobine_relais", "telerupteur"):
            rResistance = get_value(vType, pId, self.values) ** 2 / COIL_WATTS
        elif vType == "voltmetre":
            rResistance = VOLTMETER_RESISTANCE
        else:
            rResistance = MAINS_VOLTS**2 / LOAD_WATTS[vType]

        return rResistance

    def compute(self, pInputs, pState):
        """Retourne la tension de chaque nœud et le courant de chaque branche."""

        vBranches = self.build_branches(pInputs, pState)
        vCount = max(self.nets.values(), default=-1) + 1
        vIndexes = {
            vNet: vIndex
            for vIndex, vNet in enumerate(
                vNet for vNet in range(vCount) if vNet != self.ground
            )
        }
        vSize = len(vIndexes)
        vMatrix = [[0.0] * vSize for _ in range(vSize)]
        vVector = [0.0] * vSize

        for vIndex in range(vSize):
            vMatrix[vIndex][vIndex] += GMIN

        for _, vNetA, vNetB, vConductance, vForce in vBranches:
            vA = vIndexes.get(vNetA)
            vB = vIndexes.get(vNetB)

            # Branche : courant de a vers b = G·(Va − Vb − E)
            for vRow, vSign in ((vA, 1), (vB, -1)):
                if vRow is not None:
                    vMatrix[vRow][vRow] += vConductance
                    vVector[vRow] += vSign * vConductance * vForce

            if vA is not None and vB is not None:
                vMatrix[vA][vB] -= vConductance
                vMatrix[vB][vA] -= vConductance

        vSolution = solve(vMatrix, vVector)
        vVoltages = {vNet: vSolution[vIndex] for vNet, vIndex in vIndexes.items()}
        vVoltages[self.ground] = 0.0

        vCurrents = {}

        for vId, vNetA, vNetB, vConductance, vForce in vBranches:
            # Pour une source, le courant compté est celui qu'elle débite par sa borne +
            vCurrent = vConductance * (vVoltages[vNetA] - vVoltages[vNetB] - vForce)
            vCurrents[vId] = -vCurrent if self.types[vId] in SOURCES else vCurrent

        rComputed = (vVoltages, vCurrents)

        return rComputed

    def get_voltage(self, pId, pVoltages):
        """Retourne la tension aux bornes d'un composant à deux bornes."""

        vPorts = self.get_ports(pId)

        rVoltage = pVoltages[vPorts[0]] - pVoltages[vPorts[-1]]

        return rVoltage

    def simulate(self, pInputs, pMemory=None):
        """Simule le circuit pour l'état des commandes ; retourne le résultat.

        pMemory est l'état laissé par l'étape précédente : bobines collées,
        télérupteurs, protections déclenchées. Le résultat contient le nouvel
        état à repasser à l'étape suivante.
        """

        vMemory = pMemory or {}
        vState = {
            "coils": dict(vMemory.get("coils", {})),
            "latches": dict(vMemory.get("latches", {})),
            "tripped": set(vMemory.get("tripped", [])),
            "diodes": {},
        }
        vRemoteBefore = dict(vMemory.get("remote", {}))
        vToggled = set()
        vFaults = []
        vStable = False

        for _ in range(MAX_ITERATIONS):
            vVoltages, vCurrents = self.compute(pInputs, vState)
            vOver = [
                vId
                for vId, vType in self.types.items()
                if vType in PROTECTIONS
                and vId not in vState["tripped"]
                and abs(vCurrents.get(vId, 0)) > PROTECTION_RATING
            ]

            if vOver:
                vState["tripped"].update(vOver)
                continue

            vShort = self.find_short(vCurrents)

            if vShort:
                vFaults.append(vShort)
                vStable = True
                break

            if not self.update_state(
                vState, vVoltages, vCurrents, vRemoteBefore, vToggled
            ):
                vStable = True
                break

        if not vStable:
            vFaults.append(
                "Le circuit ne se stabilise pas : un relais se coupe lui-même "
                "et bat sans arrêt."
            )

        rResult = self.describe(pInputs, vState, vVoltages, vCurrents, vFaults)

        return rResult

    def find_short(self, pCurrents):
        """Retourne le message d'un court-circuit sur une source, ou une chaîne vide."""

        for vId, vType in self.types.items():
            if (
                vType == "alimentation"
                and abs(pCurrents.get(vId, 0)) > MAINS_MAX_CURRENT
            ):
                return (
                    "Court-circuit sur l'alimentation, sans disjoncteur ni fusible "
                    "pour couper : les câbles brûlent."
                )

            if vType == "pile" and abs(pCurrents.get(vId, 0)) > BATTERY_MAX_CURRENT:
                return "La pile est en court-circuit : elle chauffe et se vide."

        return ""

    def update_state(self, pState, pVoltages, pCurrents, pRemoteBefore, pToggled):
        """Met à jour bobines, télérupteurs et diodes ; indique si quelque chose a changé."""

        vChanged = False

        for vId, vType in self.types.items():
            if vType in ("bobine_relais", "telerupteur"):
                vEnergized = abs(self.get_voltage(vId, pVoltages)) >= (
                    PICKUP_RATIO * get_value(vType, vId, self.values)
                )

                if vType == "bobine_relais":
                    vChanged |= pState["coils"].get(vId, False) != vEnergized
                    pState["coils"][vId] = vEnergized
                elif vEnergized and not pRemoteBefore.get(vId) and vId not in pToggled:
                    # Le télérupteur change d'état à chaque impulsion, une seule fois
                    pToggled.add(vId)
                    pState["latches"][vId] = not pState["latches"].get(vId, False)
                    vChanged = True

                if vType == "telerupteur":
                    pState.setdefault("remote", {})[vId] = vEnergized
            elif vType in ("led", "diode"):
                vForward = LED_FORWARD if vType == "led" else DIODE_FORWARD
                vOn = pState["diodes"].get(vId, False)
                vNext = (
                    pCurrents.get(vId, 0) > 0
                    if vOn
                    else self.get_voltage(vId, pVoltages) > vForward
                )

                if vNext != vOn:
                    pState["diodes"][vId] = vNext
                    vChanged = True

        return vChanged

    def describe(self, pInputs, pState, pVoltages, pCurrents, pFaults):
        """Retourne l'état lisible de chaque composant, les mesures et les défauts."""

        vParts = {}
        vFaults = list(pFaults)

        for vId, vType in self.types.items():
            vCurrent = pCurrents.get(vId, 0.0)
            vVoltage = (
                self.get_voltage(vId, pVoltages)
                if len(COMPONENTS[vType].ports) == 2
                else 0.0
            )
            vPart = {
                "type": vType,
                "voltage": vVoltage,
                "current": vCurrent,
                "potential": max(abs(pVoltages[vNet]) for vNet in self.get_ports(vId)),
                "on": False,
                "status": "",
                "tone": "",
            }
            self.describe_part(vId, vPart, pInputs, pState, vFaults)
            vParts[vId] = vPart

        vLive = {
            vKey
            for vKey, vNet in self.nets.items()
            if abs(pVoltages[vNet]) > LIVE_VOLTS
        }

        rResult = {
            "parts": vParts,
            "live": vLive,
            "faults": vFaults,
            "memory": {
                "coils": pState["coils"],
                "latches": pState["latches"],
                "tripped": sorted(pState["tripped"]),
                "remote": pState.get("remote", {}),
            },
        }

        return rResult

    def describe_part(self, pId, pPart, pInputs, pState, pFaults):
        """Complète l'état d'un composant : allumé, état affiché, couleur, défaut."""

        vType = pPart["type"]
        vCurrent = abs(pPart["current"])

        if vType in ("lampe_bornes", "moteur_mono"):
            vRatio = vCurrent / (LOAD_WATTS[vType] / MAINS_VOLTS)
            vWords = {
                "lampe_bornes": ("allumée", "faible", "éteinte"),
                "moteur_mono": ("tourne", "n'a pas la force de démarrer", "arrêté"),
            }[vType]
            pPart["on"] = vRatio >= FULL_RATIO
            pPart["status"] = (
                vWords[0]
                if pPart["on"]
                else vWords[1] if vRatio >= DIM_RATIO else vWords[2]
            )
            pPart["tone"] = (
                "lit" if pPart["on"] else "dim" if vRatio >= DIM_RATIO else ""
            )
        elif vType in ("led", "diode"):
            pPart["on"] = vType == "led" and vCurrent >= LED_LIT_CURRENT
            pPart["status"] = format_measure(pPart["current"], "A")

            if vType == "led" and vCurrent > LED_MAX_CURRENT:
                pPart["status"] = "grillée"
                pPart["tone"] = "fault"
                pPart["on"] = False
                pFaults.append(
                    f"LED grillée : {format_measure(vCurrent, 'A')} pour "
                    f"{format_measure(LED_NOMINAL_CURRENT, 'A')} prévus. "
                    "Une résistance en série limite le courant."
                )
            elif pPart["on"]:
                pPart["tone"] = "led"
        elif vType in ("bobine_relais", "telerupteur"):
            vActive = (
                pState["coils"].get(pId)
                if vType == "bobine_relais"
                else pState.get("remote", {}).get(pId)
            )
            pPart["on"] = bool(vActive)
            pPart["status"] = "excitée" if vActive else "au repos"
            pPart["tone"] = "active" if vActive else ""
        elif vType == "voltmetre":
            pPart["status"] = format_measure(pPart["voltage"], "V")
            pPart["tone"] = "measure"
        elif vType == "amperemetre":
            pPart["status"] = format_measure(pPart["current"], "A")
            pPart["tone"] = "measure"
        elif vType in PROTECTIONS and pId in pState["tripped"]:
            pPart["status"] = "déclenché" if vType == "disjoncteur" else "fondu"
            pPart["tone"] = "fault"
            pFaults.append(
                f"{COMPONENTS[vType].label} : surintensité de plus de "
                f"{PROTECTION_RATING:.0f} A, il a coupé le circuit."
            )
        elif vType == "va_et_vient":
            pPart["status"] = "position b" if pInputs.get(pId) else "position a"
        elif vType == "resistance":
            pPart["status"] = format_measure(pPart["current"], "A")
        elif vType not in ("alimentation", "pile", "masse"):
            vClosed = self.is_closed(pId, pInputs, pState)
            pPart["on"] = vClosed
            pPart["status"] = "fermé" if vClosed else "ouvert"

            if vType in PUSH_BUTTONS and pInputs.get(pId):
                pPart["status"] += ", appuyé"
