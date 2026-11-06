"""Cas des puzzles de code : corrections et niveau après une série."""

from job.code_puzzles import get_answer, get_next_level, grade_puzzle, load_puzzles


def build_puzzle_responses(pPuzzle):
    """Retourne des réponses à un puzzle : la bonne, des fausses et des illisibles."""

    vAnswer = get_answer(pPuzzle)

    if pPuzzle["type"] == "ordre":
        return [
            vAnswer,
            vAnswer[::-1],
            vAnswer[1:] + vAnswer[:1],
            vAnswer[:-1],
            [0] * len(vAnswer),
            "0",
        ]

    if pPuzzle["type"] == "saisie":
        return [
            vAnswer,
            f"  {vAnswer.lower()}  ",
            vAnswer.replace(" ", "	"),
            "?" * 250,
            " ",
            None,
            3,
        ]

    rResponses = [
        vAnswer,
        (vAnswer + 1) % len(pPuzzle["lines"]),
        len(pPuzzle["lines"]),
        -1,
        True,
        "1",
    ]

    return rResponses


def build_puzzle_cases():
    """Retourne les corrections attendues de chaque puzzle, et le niveau après une série."""

    vCases = []

    for vPuzzle in load_puzzles().values():
        for vResponse in build_puzzle_responses(vPuzzle):
            try:
                vExpected = {"grade": list(grade_puzzle(vPuzzle, vResponse))}

            except ValueError as vError:
                vExpected = {"error": str(vError)}

            vCases.append({"puzzle": vPuzzle["id"], "response": vResponse, **vExpected})

    rCases = {
        "grades": vCases,
        "levels": [
            [vLevel, vScore, get_next_level(vLevel, vScore)]
            for vLevel in (1, 2, 3)
            for vScore in range(11)
        ],
    }

    return rCases
