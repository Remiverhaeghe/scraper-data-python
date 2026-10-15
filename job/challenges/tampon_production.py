"""Défi : la simulation du stock tampon entre deux machines"""

ID = "tampon-production"
TITLE = "Le stock tampon"
SERIES = "Algorithmique"
LEVEL = "débutant"

STATEMENTS = (
    """Entre une presse et une soudeuse, un convoyeur tampon accueille les pièces. La
première ligne donne sa capacité, `capacite N`. Chaque ligne suivante est un
événement : `E n` quand la presse livre n pièces, `S n` quand la soudeuse en prend n.

Le tampon est vide au départ. Quand une livraison dépasse la place libre, seules les
pièces qui rentrent sont acceptées ; les autres sont refusées. La soudeuse ne peut pas
prendre plus de pièces qu'il n'y en a.

**Quel est le nombre maximal de pièces présentes en même temps dans le tampon ?**""",
    """Chaque pièce refusée est déviée vers un stock manuel, ce qui coûte du temps.

**Combien de pièces ont été refusées au total ?**""",
)
EXAMPLE = """capacite 5
E 3
S 1
E 4
S 2
E 1"""
EXAMPLE_ANSWERS = ("5", "1")
HINTS = (
    "Les pièces acceptées valent le minimum entre n et la place libre.",
    "Les pièces prises valent le minimum entre n et le stock présent.",
)
NOTE = """Une simulation pas à pas suffit : un stock, une capacité, et les minimums aux
bonnes places. Ce raisonnement sert à dimensionner un tampon : trop petit, il bloque la
presse ; trop grand, il immobilise des pièces."""


def generate(pRandom):
    """Retourne la capacité du tampon et une longue suite d'événements."""

    vLines = [f"capacite {pRandom.randint(20, 60)}"]
    vLines += [
        f"{pRandom.choice('ES')} {pRandom.randint(1, 15)}"
        for _ in range(pRandom.randint(400, 600))
    ]

    rInput = "\n".join(vLines)

    return rInput


def solve(pInput):
    """Retourne le stock maximal atteint et le nombre de pièces refusées."""

    vLines = pInput.strip().splitlines()
    vCapacity = int(vLines[0].split()[1])
    vStock = vMaximum = vRefused = 0

    for vLine in vLines[1:]:
        vKind, vCount = vLine.split()
        vCount = int(vCount)

        if vKind == "E":
            vAccepted = min(vCount, vCapacity - vStock)
            vRefused += vCount - vAccepted
            vStock += vAccepted
        else:
            vStock -= min(vCount, vStock)

        vMaximum = max(vMaximum, vStock)

    rAnswers = (str(vMaximum), str(vRefused))

    return rAnswers
