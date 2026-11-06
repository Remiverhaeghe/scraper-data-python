"""Cas de l'automate : tests, dessins du ladder et chronogrammes."""

from job.ladder import parse_program, render_svg
from job.ladder_game import (
    Simulator,
    get_names,
    load_levels,
    render_chronogram,
    run_level,
)

RUN_KEYS = ("passed", "error", "line", "checks", "violations", "signals", "samples")
# Cycles joués avant de dessiner le ladder coloré, comme pendant une simulation
LIVE_CYCLES = 15
# Programmes fautifs, joués sur le premier niveau
WRONG_PROGRAMS = (
    "moteur = !(marche)",
    "marche = arret",
    "t = TON(marche, 0s)",
    "moteur = marche &",
    "SET = marche",
    "moteur = marche ¤ arret",
    "Moteur = marche",
    "lot = CTU(marche, 0)",
    "moteur = (marche | moteur) & arret arret",
    "# rien que des commentaires\n\n",
)


def build_ladder_expected(pLevel, pProgram):
    """Retourne ce que le téléphone doit retrouver : test, dessins et chronogramme."""

    vRun = run_level(pLevel, pProgram)
    rExpected = {vKey: vRun[vKey] for vKey in RUN_KEYS if vKey in vRun}

    if vRun["error"]:
        return rExpected

    vInputs = set(get_names(pLevel, "input"))
    vRungs = parse_program(pProgram, vInputs)
    vSimulator = Simulator(pLevel, vRungs)

    for _ in range(LIVE_CYCLES):
        vSimulator.step()

    rExpected["ladder_svg"] = render_svg(vRungs)
    rExpected["live_svg"] = render_svg(vRungs, vSimulator.values)
    rExpected["chart_svg"] = render_chronogram(
        vRun["signals"], vRun["samples"], vInputs
    )

    return rExpected


def build_ladder_cases():
    """Retourne les cas ladder : solution, départ, temporisations, programmes fautifs."""

    rCases = []

    for vIndex, vLevel in enumerate(load_levels().values()):
        vPrograms = [
            ("solution", vLevel["solution"]),
            ("départ", vLevel["starter"]),
            (
                "temporisations arrondies",
                vLevel["solution"].replace("2s", "0.25s").replace("1s", "350ms"),
            ),
        ]

        if vIndex == 0:
            vPrograms += [
                (f"faute {vNumber}", vText)
                for vNumber, vText in enumerate(WRONG_PROGRAMS, 1)
            ]

        for vName, vProgram in vPrograms:
            rCases.append(
                {
                    "name": f"{vLevel['id']} : {vName}",
                    "level": vLevel["id"],
                    "program": vProgram,
                    "expected": build_ladder_expected(vLevel, vProgram),
                }
            )

    return rCases
