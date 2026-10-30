"""Cas communs aux simulateurs Python et Dart : python -m tools.lab_cases

Écrit tests/fixtures/shared_lab_cases.json depuis les simulateurs de
référence. tests/job/test_shared_lab_cases.py vérifie que le fichier est à
jour, mobile/test/shared_lab_cases_test.dart que le téléphone donne les mêmes
résultats.
"""

import json
from dataclasses import asdict
from pathlib import Path

from job.git_graph import render_graph
from job.git_levels import LEVELS as GIT_LEVELS
from job.git_levels import is_goal_reached
from job.git_sandbox import describe_worktree, replay, run_command
from job.ladder import parse_program, render_svg
from job.ladder_game import (
    Simulator,
    get_names,
    load_levels,
    render_chronogram,
    run_level,
)
from job.troubleshooting import load_scenarios, play_scenario

FIXTURE_FILE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "shared_lab_cases.json"
)
RESULT_KEYS = ("done", "wrong", "log", "minutes", "solved", "proven", "score", "stars")
RUN_KEYS = ("passed", "error", "line", "checks", "violations", "signals", "samples")
# Commandes Git jouées à la suite sur chaque niveau, bonnes ou fautives
GIT_COMMANDS = (
    "git status",
    "git log",
    "git diff",
    "git branch",
    "modifier notes.txt",
    "modifier réglages.yml",
    "git stash",
    "git stash list",
    "git stash pop",
    "git add notes.txt",
    "git restore --staged notes.txt",
    "git commit",
    "git commit -am 'premier jet'",
    'git commit -m "message \\"cité\\""',
    "git switch -c essai",
    "modifier notes.txt",
    "git commit -a",
    "git switch main",
    "git merge essai",
    "git merge --abort",
    "git rebase essai",
    "git cherry-pick essai",
    "git checkout --ours notes.txt",
    "git reset --soft HEAD~1",
    "git status",
    "git reset --hard HEAD~1",
    "git revert HEAD",
    "git checkout C0",
    "git switch --detach HEAD^",
    "git branch -f essai C1",
    "git branch -d essai",
    "git push",
    "git pull --rebase",
    "git fetch",
    "git bisect",
    "git commit --amend",
    "rm -rf /",
    'git commit -m "non fermé',
    "modifier ../secret",
    "git log --oneline",
    "git merge couleur",
    "git status",
    "git switch main",
    "git checkout --theirs app.py",
    "git add .",
    "git commit",
    "git rebase --continue",
    "git stash pop",
)
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

# Scénarios d'essai : arrondis à la moitié, où Python arrondit au pair
ROUNDING_SCENARIOS = (
    {
        "id": "essai-arrondi-bas",
        "best_minutes": 1,
        "checks": [
            {
                "id": "mesure",
                "label": "Mesure",
                "minutes": 8,
                "result": "ok",
                "evidence": True,
            }
        ],
        "causes": [{"id": "reparer", "label": "Réparer", "minutes": 0, "right": True}],
    },
    {
        "id": "essai-arrondi-haut",
        "best_minutes": 3,
        "checks": [
            {
                "id": "mesure",
                "label": "Mesure",
                "minutes": 8,
                "result": "ok",
                "evidence": True,
            }
        ],
        "causes": [{"id": "reparer", "label": "Réparer", "minutes": 0, "right": True}],
    },
)


def get_right_cause(pScenario):
    """Retourne la bonne réparation d'un scénario."""

    rCause = next(vCause for vCause in pScenario["causes"] if vCause.get("right"))

    return rCause


def build_paths(pScenario):
    """Retourne les parties à rejouer : (nom, actions)."""

    vChecks = {vCheck["id"]: vCheck for vCheck in pScenario["checks"]}
    vRight = f"repair:{get_right_cause(pScenario)['id']}"
    vEvidence = min(
        (vCheck for vCheck in pScenario["checks"] if vCheck.get("evidence")),
        key=lambda pCheck: pCheck["minutes"]
        + (vChecks[pCheck["requires"]]["minutes"] if pCheck.get("requires") else 0),
    )
    vShortest = (
        [f"check:{vEvidence['requires']}"] if vEvidence.get("requires") else []
    ) + [f"check:{vEvidence['id']}", vRight]
    vWrong = [
        f"repair:{vCause['id']}"
        for vCause in pScenario["causes"]
        if not vCause.get("right")
    ][:1]

    rPaths = [
        ("chemin le plus court", vShortest),
        ("réparation sans preuve", [vRight]),
        (
            "toutes les mesures, une erreur, puis une action ignorée",
            [f"check:{vCheck['id']}" for vCheck in pScenario["checks"]]
            + vWrong
            + vWrong
            + [vRight, f"check:{pScenario['checks'][0]['id']}"],
        ),
    ]

    return rPaths


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


def build_cases():
    """Retourne les cas de toutes les simulations portées sur le téléphone."""

    vCases = []

    for vScenario in [*load_scenarios().values(), *ROUNDING_SCENARIOS]:
        for vName, vActions in build_paths(vScenario):
            vState = play_scenario(vScenario, vActions)
            vCases.append(
                {
                    "name": f"{vScenario['id']} : {vName}",
                    "scenario": vScenario["id"],
                    "actions": vActions,
                    "expected": {vKey: vState[vKey] for vKey in RESULT_KEYS},
                }
            )

    vLadder = []

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
            vLadder.append(
                {
                    "name": f"{vLevel['id']} : {vName}",
                    "level": vLevel["id"],
                    "program": vProgram,
                    "expected": build_ladder_expected(vLevel, vProgram),
                }
            )

    rCases = {
        "description": "Cas communs aux simulateurs Python et Dart, générés par "
        "python -m tools.lab_cases : ne pas modifier à la main.",
        "extra_scenarios": list(ROUNDING_SCENARIOS),
        "troubleshooting": vCases,
        "ladder": vLadder,
        "git_levels": [asdict(vLevel) for vLevel in GIT_LEVELS],
        "git": [
            build_git_case(vLevel, vName, vCommands)
            for vLevel in GIT_LEVELS
            for vName, vCommands in (
                ("solution", vLevel.solution),
                ("commandes variées", GIT_COMMANDS),
            )
        ],
    }

    return rCases


def build_git_case(pLevel, pName, pCommands):
    """Rejoue des commandes sur un niveau Git : message, fichiers, objectif, graphes."""

    vRepository = replay(pLevel.setup)
    vSteps = []

    for vCommand in pCommands:
        try:
            vStep = {"command": vCommand, "message": run_command(vRepository, vCommand)}

        except ValueError as vError:
            vStep = {"command": vCommand, "error": str(vError)}

        vStep["worktree"] = describe_worktree(vRepository)
        vStep["reached"] = is_goal_reached(pLevel, vRepository)
        vSteps.append(vStep)

    rCase = {
        "name": f"{pLevel.id} : {pName}",
        "level": pLevel.id,
        "steps": vSteps,
        "graph": render_graph(vRepository.local_view(), "Votre dépôt"),
        "server": (
            render_graph(vRepository.server_view(), "Serveur", pShowHead=False)
            if vRepository.remote
            else ""
        ),
        "goal": render_graph(
            replay(pLevel.setup + pLevel.solution).local_view(), "Objectif"
        ),
    }

    return rCase


def main():
    """Écrit le fichier des cas communs."""

    FIXTURE_FILE.write_text(
        json.dumps(build_cases(), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Cas écrits dans {FIXTURE_FILE}")


if __name__ == "__main__":
    main()
