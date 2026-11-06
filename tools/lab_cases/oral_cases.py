"""Cas de l'entraînement à l'oral : notes attendues d'une réponse."""

from job.oral_interview import grade_answer


def build_oral_cases():
    """Retourne les notes attendues d'une réponse orale : temps, durée, grille."""

    rCases = []

    for vSeconds, vDuration, vStructure, vExample in (
        (0, 60, 0, 0),
        (19.4, 60, 2, 2),
        (19.6, 60, 2, 2),
        (20, 90, 1, 2),
        (90, 90, 2, 1),
        (90.4, 90, 2, 2),
        (125, 120, 1, 1),
        (45, 60, 3, 1),
        (45, 60, True, 1),
        (-1, 60, 1, 1),
        (3601, 60, 1, 1),
    ):
        try:
            vExpected = {
                "grade": grade_answer(vSeconds, vDuration, vStructure, vExample)
            }

        except ValueError as vError:
            vExpected = {"error": str(vError)}

        rCases.append(
            {
                "seconds": vSeconds,
                "duration": vDuration,
                "structure": vStructure,
                "example": vExample,
                **vExpected,
            }
        )

    return rCases
