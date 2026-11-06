"""Cas communs aux simulateurs Python et Dart : python -m tools.lab_cases

Écrit tests/fixtures/shared_lab_cases.json depuis les simulateurs de
référence. tests/job/test_shared_lab_cases.py vérifie que le fichier est à
jour, mobile/test/shared_lab_cases_test.dart que le téléphone donne les mêmes
résultats.
"""

import json
from dataclasses import asdict
from pathlib import Path

from job.circuit_levels import load_levels as load_circuit_levels
from job.code_puzzles import load_puzzles
from job.devops_levels import load_levels as load_devops_levels
from job.docker_sim import REGISTRY
from job.excel_levels import load_levels as load_excel_levels
from job.git_levels import LEVELS as GIT_LEVELS
from job.maven_sim import CENTRAL
from job.mobile_labs import (
    build_circuit_library,
    build_excel_rules,
    build_oral_rules,
    build_puzzle_rules,
    build_sql_rules,
)
from job.sql_levels import load_levels as load_sql_levels
from job.sql_sandbox import load_script
from tools.lab_cases.circuit_cases import build_circuit_cases
from tools.lab_cases.devops_cases import build_devops_cases
from tools.lab_cases.excel_cases import (
    EXCEL_SHEET,
    build_excel_cases,
    build_excel_formula_cases,
)
from tools.lab_cases.git_cases import build_git_cases
from tools.lab_cases.ladder_cases import build_ladder_cases
from tools.lab_cases.oral_cases import build_oral_cases
from tools.lab_cases.puzzle_cases import build_puzzle_cases
from tools.lab_cases.sql_cases import build_sql_cases
from tools.lab_cases.troubleshooting_cases import (
    ROUNDING_SCENARIOS,
    build_troubleshooting_cases,
)

FIXTURE_FILE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "shared_lab_cases.json"
)


def build_cases():
    """Retourne les cas de toutes les simulations portées sur le téléphone."""

    rCases = {
        "description": "Cas communs aux simulateurs Python et Dart, générés par "
        "python -m tools.lab_cases : ne pas modifier à la main.",
        "extra_scenarios": list(ROUNDING_SCENARIOS),
        "troubleshooting": build_troubleshooting_cases(),
        "ladder": build_ladder_cases(),
        "sql_content": {
            "levels": list(load_sql_levels().values()),
            "script": load_script(),
            "rules": build_sql_rules(),
        },
        "sql": build_sql_cases(),
        "devops_content": {
            "levels": list(load_devops_levels().values()),
            "central": CENTRAL,
            "registry": REGISTRY,
        },
        "devops": build_devops_cases(),
        "oral_rules": build_oral_rules(),
        "oral": build_oral_cases(),
        "puzzles_content": {
            "puzzles": list(load_puzzles().values()),
            "rules": build_puzzle_rules(),
        },
        "puzzles": build_puzzle_cases(),
        "circuit_content": {
            "levels": list(load_circuit_levels().values()),
            "library": build_circuit_library(),
        },
        "circuit": build_circuit_cases(),
        "excel_content": {
            "levels": list(load_excel_levels().values()),
            "rules": build_excel_rules(),
        },
        "excel": build_excel_cases(),
        "excel_sheet": EXCEL_SHEET,
        "excel_formulas": build_excel_formula_cases(),
        "git_levels": [asdict(vLevel) for vLevel in GIT_LEVELS],
        "git": build_git_cases(),
    }

    return rCases


def main():
    """Écrit le fichier des cas communs."""

    FIXTURE_FILE.write_text(
        json.dumps(build_cases(), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Cas écrits dans {FIXTURE_FILE}")
