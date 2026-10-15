"""Défi : le plus court chemin d'un chariot dans l'atelier"""

from collections import deque

ID = "chemin-atelier"
TITLE = "Le chariot de l'atelier"
SERIES = "Algorithmique"
LEVEL = "confirmé"

STATEMENTS = (
    """Le plan de l'atelier est une grille : `#` est une machine ou un mur, `.` une
allée libre, `S` le quai de départ du chariot et `E` le poste à livrer. Le chariot se
déplace d'une case à la fois, vers le haut, le bas, la gauche ou la droite, jamais en
diagonale ni à travers une machine.

**Combien de déplacements faut-il, au minimum, pour aller de S à E ?**""",
    """Avant de livrer, le chariot doit maintenant passer par le contrôle qualité,
marqué `C`.

**Combien de déplacements faut-il, au minimum, pour aller de S à E en passant par C ?**""",
)
EXAMPLE = """S..#....
.#.#.##.
.#...#C.
.####.#.
......#E"""
EXAMPLE_ANSWERS = ("15", "17")
HINTS = (
    "Un parcours en largeur, avec une file, trouve le plus court chemin sur une grille.",
    "Le chemin par C est la somme de deux plus courts chemins : S vers C, puis C vers E.",
)
NOTE = """Le parcours en largeur explore les cases par distance croissante : la première
fois qu'il atteint E, la distance est minimale. Pour un passage obligé, on additionne
deux parcours. C'est la base des calculs d'itinéraires de chariots et de robots
mobiles."""

SIZE = 41


def generate(pRandom):
    """Retourne une grille d'atelier où S, C et E sont reliés."""

    while True:
        vGrid = [
            ["#" if pRandom.random() < 0.28 else "." for _ in range(SIZE)]
            for _ in range(SIZE)
        ]
        vCells = pRandom.sample(range(SIZE * SIZE), 3)

        for vCell, vMark in zip(vCells, "SCE"):
            vGrid[vCell // SIZE][vCell % SIZE] = vMark

        vInput = "\n".join("".join(vRow) for vRow in vGrid)

        try:
            vAnswers = solve(vInput)

        except ValueError:
            continue

        # Un trajet assez long, que le passage par C rallonge vraiment.
        if SIZE <= int(vAnswers[0]) < int(vAnswers[1]):
            return vInput


def find(pGrid, pMark):
    """Retourne la ligne et la colonne d'une marque de la grille."""

    rPosition = next(
        (vRow, vColumn)
        for vRow, vLine in enumerate(pGrid)
        for vColumn, vValue in enumerate(vLine)
        if vValue == pMark
    )

    return rPosition


def get_distance(pGrid, pStart, pEnd):
    """Retourne la longueur du plus court chemin ; lève ValueError s'il n'y en a pas."""

    vDistances = {pStart: 0}
    vQueue = deque([pStart])

    while vQueue:
        vRow, vColumn = vQueue.popleft()

        if (vRow, vColumn) == pEnd:
            return vDistances[pEnd]

        for vNext in (
            (vRow - 1, vColumn),
            (vRow + 1, vColumn),
            (vRow, vColumn - 1),
            (vRow, vColumn + 1),
        ):
            if (
                0 <= vNext[0] < len(pGrid)
                and 0 <= vNext[1] < len(pGrid[0])
                and pGrid[vNext[0]][vNext[1]] != "#"
                and vNext not in vDistances
            ):
                vDistances[vNext] = vDistances[(vRow, vColumn)] + 1
                vQueue.append(vNext)

    raise ValueError("aucun chemin")


def solve(pInput):
    """Retourne le plus court chemin de S à E, direct puis par C."""

    vGrid = pInput.strip().splitlines()
    vStart, vCheck, vEnd = (find(vGrid, vMark) for vMark in "SCE")

    rAnswers = (
        str(get_distance(vGrid, vStart, vEnd)),
        str(get_distance(vGrid, vStart, vCheck) + get_distance(vGrid, vCheck, vEnd)),
    )

    return rAnswers
