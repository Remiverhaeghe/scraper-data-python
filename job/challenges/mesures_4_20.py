"""Défi : la mise à l'échelle des transmetteurs 4-20 mA d'une unité"""

import math

ID = "mesures-4-20"
TITLE = "La tournée des transmetteurs"
SERIES = "Instrumentation"
LEVEL = "intermédiaire"

STATEMENTS = (
    """Lors d'une tournée, un technicien relève le courant de chaque transmetteur
4-20 mA sous la forme `repère;début d'échelle;fin d'échelle;courant en mA`. Selon la
recommandation NAMUR NE 43, un courant inférieur à 3,6 mA ou supérieur à 21 mA
signale un transmetteur en défaut.

**Combien de transmetteurs sont en défaut ?**""",
    """Pour chaque transmetteur valide, la valeur physique vaut
début + (courant − 4) × (fin − début) / 16.

**Quelle est la partie entière de la somme des valeurs physiques des transmetteurs
valides ?**""",
)
EXAMPLE = """PT101;0;10;12.00
TT102;-20;80;3.20
FT103;0;400;20.00
LT104;0;100;21.50"""
EXAMPLE_ANSWERS = ("2", "405")
HINTS = (
    "Un courant de 3,6 mA exactement n'est pas en défaut : la limite est stricte.",
    "Additionnez les valeurs en nombres réels et ne tronquez qu'à la fin.",
)
NOTE = """Le zéro vivant à 4 mA permet de distinguer une mesure nulle d'une boucle coupée,
qui donne 0 mA. Le piège classique est d'oublier de retrancher ces 4 mA : 12 mA font
50 % de l'échelle, pas 60 %."""

RANGES = (
    ("PT", 0, 10),
    ("PT", 0, 250),
    ("TT", -20, 80),
    ("TT", 0, 150),
    ("FT", 0, 400),
    ("LT", 0, 100),
)


def generate(pRandom):
    """Retourne le relevé de la tournée, avec quelques transmetteurs en défaut."""

    while True:
        vLines = []

        for vIndex in range(pRandom.randint(80, 120)):
            vPrefix, vLow, vHigh = pRandom.choice(RANGES)
            vCurrent = (
                pRandom.uniform(0.0, 3.5)
                if pRandom.random() < 0.08
                else pRandom.uniform(4.0, 20.0)
            )
            vLines.append(f"{vPrefix}{100 + vIndex};{vLow};{vHigh};{vCurrent:.2f}")

        vInput = "\n".join(vLines)
        vTotal = get_valid_total(vInput)

        # Une somme trop proche d'un entier dépendrait des arrondis du langage.
        if 0.01 < vTotal - math.floor(vTotal) < 0.99:
            return vInput


def get_valid_total(pInput):
    """Retourne la somme des valeurs physiques des transmetteurs valides."""

    rTotal = 0.0

    for vLine in pInput.strip().splitlines():
        _, vLow, vHigh, vCurrent = vLine.split(";")
        vCurrent = float(vCurrent)

        if 3.6 <= vCurrent <= 21.0:
            rTotal += float(vLow) + (vCurrent - 4) * (float(vHigh) - float(vLow)) / 16

    return rTotal


def solve(pInput):
    """Retourne le nombre de transmetteurs en défaut et la somme des valeurs valides."""

    vFaults = sum(
        not 3.6 <= float(vLine.split(";")[3]) <= 21.0
        for vLine in pInput.strip().splitlines()
    )

    rAnswers = (str(vFaults), str(math.floor(get_valid_total(pInput))))

    return rAnswers
