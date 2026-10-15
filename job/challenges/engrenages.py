"""Défi : le réalignement des repères d'un train d'engrenages"""

from math import lcm

ID = "engrenages"
TITLE = "Les repères des engrenages"
SERIES = "Mathématiques"
LEVEL = "intermédiaire"

STATEMENTS = (
    """Chaque ligne décrit un train d'engrenages qui engrènent l'un après l'autre, par
leur nombre de dents. Au départ, un repère peint sur chaque roue est tourné vers le
haut. Quand la première roue fait un tour, elle fait passer autant de dents que son
nombre de dents, et chaque roue tourne du même nombre de dents.

Les repères sont tous de nouveau vers le haut quand chaque roue a fait un nombre entier
de tours.

**Pour chaque train, combien de tours doit faire la première roue, au minimum, pour
que tous les repères se réalignent ? Donnez la somme sur tous les trains.**""",
    """Le constructeur veut connaître l'usure de la dernière roue.

**Au moment du premier réalignement de chaque train, combien de tours la dernière
roue a-t-elle faits ? Donnez la somme sur tous les trains.**""",
)
EXAMPLE = """12 18
10 15 25
8 12 20 6"""
EXAMPLE_ANSWERS = ("33", "28")
HINTS = (
    "Après t tours d'une première roue de z dents, z × t dents sont passées partout.",
    "Chaque roue i doit voir un multiple de ses dents : cherchez un PPCM.",
)
NOTE = """Après t tours de la première roue de z₁ dents, z₁ × t dents sont passées. Il faut
que ce nombre soit un multiple de chaque zᵢ : le plus petit est le PPCM des zᵢ, donc
t = PPCM / z₁. La dernière roue fait alors PPCM / z_dernière tours. Le PGCD et le PPCM
reviennent souvent dans les calculs de rapports de transmission."""


def generate(pRandom):
    """Retourne une liste de trains d'engrenages."""

    rInput = "\n".join(
        " ".join(str(pRandom.randint(8, 60)) for _ in range(pRandom.randint(2, 6)))
        for _ in range(pRandom.randint(60, 90))
    )

    return rInput


def solve(pInput):
    """Retourne les sommes des tours de la première et de la dernière roue."""

    vFirstTurns = 0
    vLastTurns = 0

    for vLine in pInput.strip().splitlines():
        vTeeth = [int(vValue) for vValue in vLine.split()]
        vTotal = lcm(*vTeeth)
        vFirstTurns += vTotal // vTeeth[0]
        vLastTurns += vTotal // vTeeth[-1]

    rAnswers = (str(vFirstTurns), str(vLastTurns))

    return rAnswers
