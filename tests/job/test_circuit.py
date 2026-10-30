"""Tests du simulateur de circuits : lois électriques, relais et défauts"""

import pytest

from job.circuit import Circuit, format_measure
from job.circuit_drawing import render_circuit
from job.circuit_levels import read_state


def build(pIds, pWires, pValues=None):
    """Retourne un circuit dont chaque composant a pour identifiant son type."""

    vComponents = [
        {"id": vId, "type": vId.split("-")[0], "x": vIndex % 4, "y": vIndex // 4}
        for vIndex, vId in enumerate(pIds)
    ]

    return Circuit(vComponents, pWires, pValues)


LAMP = build(
    ["alimentation", "disjoncteur", "interrupteur", "lampe_bornes"],
    [
        ["alimentation", "L", "disjoncteur", "1"],
        ["disjoncteur", "2", "interrupteur", "1"],
        ["interrupteur", "2", "lampe_bornes", "1"],
        ["lampe_bornes", "2", "alimentation", "N"],
    ],
)


def test_lamp_follows_the_switch_and_ohms_law():
    """Vérifie la lampe éteinte puis allumée, et son courant de 60 W sous 230 V."""

    vOff = LAMP.simulate({"interrupteur": False})["parts"]["lampe_bornes"]
    vOn = LAMP.simulate({"interrupteur": True})

    assert vOff["status"] == "éteinte"
    assert vOff["potential"] < 1
    assert vOn["parts"]["lampe_bornes"]["status"] == "allumée"
    assert vOn["parts"]["lampe_bornes"]["current"] == pytest.approx(60 / 230, rel=0.01)
    assert ("interrupteur", "2") in vOn["live"]
    assert not vOn["faults"]


def test_short_circuit_trips_the_breaker_or_is_reported():
    """Vérifie le disjoncteur qui déclenche, et le court-circuit sans protection."""

    vProtected = build(
        ["alimentation", "disjoncteur", "interrupteur"],
        [
            ["alimentation", "L", "disjoncteur", "1"],
            ["disjoncteur", "2", "interrupteur", "1"],
            ["interrupteur", "2", "alimentation", "N"],
        ],
    ).simulate({"interrupteur": True})
    vBare = build(
        ["alimentation", "interrupteur"],
        [
            ["alimentation", "L", "interrupteur", "1"],
            ["interrupteur", "2", "alimentation", "N"],
        ],
    ).simulate({"interrupteur": True})

    assert vProtected["memory"]["tripped"] == ["disjoncteur"]
    assert vProtected["parts"]["disjoncteur"]["status"] == "déclenché"
    assert "les câbles brûlent" in vBare["faults"][0]


def test_led_needs_a_resistor():
    """Vérifie le courant d'une LED avec 470 Ω, et la LED grillée avec 10 Ω."""

    vWires = [
        ["pile", "+", "resistance", "1"],
        ["resistance", "2", "led", "anode"],
        ["led", "cathode", "pile", "−"],
    ]
    vLit = build(["pile", "resistance", "led"], vWires, {"resistance": 470})
    vBurnt = build(["pile", "resistance", "led"], vWires, {"resistance": 10})
    vReversed = build(
        ["pile", "resistance", "led"],
        [
            ["pile", "+", "resistance", "1"],
            ["resistance", "2", "led", "cathode"],
            ["led", "anode", "pile", "−"],
        ],
    )

    assert vLit.simulate({})["parts"]["led"]["current"] == pytest.approx(
        0.0147, abs=0.0005
    )
    assert "LED grillée" in vBurnt.simulate({})["faults"][0]
    assert not vReversed.simulate({})["parts"]["led"]["on"]


def test_divider_and_series_lamps():
    """Vérifie le diviseur de tension mesuré et les lampes en série qui éclairent peu."""

    vDivider = build(
        ["pile", "resistance-1", "resistance-2", "voltmetre"],
        [
            ["pile", "+", "resistance-1", "1"],
            ["resistance-1", "2", "resistance-2", "1"],
            ["resistance-2", "2", "pile", "−"],
            ["voltmetre", "1", "resistance-2", "1"],
            ["voltmetre", "2", "resistance-2", "2"],
        ],
        {"pile": 5, "resistance-1": 1000, "resistance-2": 2000},
    )
    vSeries = build(
        ["alimentation", "lampe_bornes-1", "lampe_bornes-2"],
        [
            ["alimentation", "L", "lampe_bornes-1", "1"],
            ["lampe_bornes-1", "2", "lampe_bornes-2", "1"],
            ["lampe_bornes-2", "2", "alimentation", "N"],
        ],
    )

    assert vDivider.simulate({})["parts"]["voltmetre"]["status"] == "3,33 V"
    assert vSeries.simulate({})["parts"]["lampe_bornes-1"]["status"] == "faible"


def test_relay_self_holding_and_remote_switch_keep_their_state():
    """Vérifie l'auto-maintien par le contact du relais et le télérupteur par impulsions."""

    vMotor = build(
        ["alimentation", "bouton_arret", "bouton_marche", "bobine_relais"]
        + ["contact_relais", "contacteur", "moteur_mono"],
        [
            ["alimentation", "L", "bouton_arret", "1"],
            ["bouton_arret", "2", "bouton_marche", "1"],
            ["bouton_marche", "2", "bobine_relais", "1"],
            ["bouton_arret", "2", "contact_relais", "1"],
            ["contact_relais", "2", "bobine_relais", "1"],
            ["bobine_relais", "2", "alimentation", "N"],
            ["alimentation", "L", "contacteur", "1"],
            ["contacteur", "2", "moteur_mono", "1"],
            ["moteur_mono", "2", "alimentation", "N"],
        ],
    )
    vRemote = build(
        ["alimentation", "bouton_marche", "telerupteur"]
        + ["contact_telerupteur", "lampe_bornes"],
        [
            ["alimentation", "L", "bouton_marche", "1"],
            ["bouton_marche", "2", "telerupteur", "1"],
            ["telerupteur", "2", "alimentation", "N"],
            ["alimentation", "L", "contact_telerupteur", "1"],
            ["contact_telerupteur", "2", "lampe_bornes", "1"],
            ["lampe_bornes", "2", "alimentation", "N"],
        ],
    )
    vStates = []
    vMemory = None

    for vInputs in ({"bouton_marche": True}, {}, {"bouton_arret": True}, {}):
        vResult = vMotor.simulate(vInputs, vMemory)
        vMemory = vResult["memory"]
        vStates.append(vResult["parts"]["moteur_mono"]["on"])

    vLamp = []
    vMemory = None

    for vPressed in (True, False, True, False):
        vResult = vRemote.simulate({"bouton_marche": vPressed}, vMemory)
        vMemory = vResult["memory"]
        vLamp.append(vResult["parts"]["lampe_bornes"]["on"])

    assert vStates == [True, True, False, False]
    assert vLamp == [True, True, False, False]


def test_browser_state_is_reduced_to_the_schema():
    """Vérifie qu'un état forgé ne garde que des booléens sur les bons composants."""

    vComponents = LAMP.components
    vInputs, vMemory = read_state(
        {"interrupteur": True, "lampe_bornes": True, "inconnu": True, "disjoncteur": 1},
        {"coils": {"interrupteur": True}, "tripped": ["disjoncteur", "lampe_bornes"]},
        vComponents,
    )

    assert vInputs == {"interrupteur": True}
    assert vMemory["coils"] == {}
    assert vMemory["tripped"] == ["disjoncteur"]


def test_measures_and_drawing():
    """Vérifie l'écriture des mesures et le dessin des fils sous tension."""

    vSvg = render_circuit(
        LAMP.components,
        [["alimentation", "L", "disjoncteur", "1"]],
        LAMP.simulate({"interrupteur": True}),
    )

    assert format_measure(0.0147, "A") == "14,7 mA"
    assert format_measure(230, "V") == "230 V"
    assert 'stroke="#dc2626"' in vSvg
    assert "allumée" in vSvg
