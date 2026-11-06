"""Cas des pannes à résoudre : parties rejouées sur chaque scénario."""

from job.troubleshooting import load_scenarios, play_scenario

RESULT_KEYS = ("done", "wrong", "log", "minutes", "solved", "proven", "score", "stars")
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


def build_troubleshooting_cases():
    """Retourne les parties rejouées de chaque scénario de panne."""

    rCases = []

    for vScenario in [*load_scenarios().values(), *ROUNDING_SCENARIOS]:
        for vName, vActions in build_paths(vScenario):
            vState = play_scenario(vScenario, vActions)
            rCases.append(
                {
                    "name": f"{vScenario['id']} : {vName}",
                    "scenario": vScenario["id"],
                    "actions": vActions,
                    "expected": {vKey: vState[vKey] for vKey in RESULT_KEYS},
                }
            )

    return rCases
