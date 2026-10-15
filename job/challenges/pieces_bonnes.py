"""Défi : les pièces bonnes et le taux de rebut d'une presse"""

ID = "pieces-bonnes"
TITLE = "Le compteur de la presse"
SERIES = "Industrie"
LEVEL = "débutant"

STATEMENTS = (
    """La presse à injecter enregistre, pour chaque heure de la journée, le nombre de
pièces produites et le nombre de pièces mises au rebut, sous la forme
`heure;produites;rebuts`.

**Combien de pièces bonnes la presse a-t-elle produites sur la journée ?**""",
    """Le service qualité veut savoir quand la presse a le plus dérivé.

**À quelle heure le taux de rebut, rebuts divisés par pièces produites, est-il le
plus élevé ?** Donnez l'heure sur deux chiffres, telle qu'elle est écrite.""",
)
EXAMPLE = """06;120;3
07;118;12
08;0;0
09;125;5"""
EXAMPLE_ANSWERS = ("343", "07")
HINTS = (
    "Les pièces bonnes d'une heure valent produites moins rebuts.",
    "Une heure sans production a un taux de rebut nul : évitez la division par zéro.",
)
NOTE = """La première partie est une simple somme. La seconde demande de calculer un
rapport et de garder le maximum, sans diviser par zéro pendant les arrêts. Le taux de
qualité de la journée, pièces bonnes sur pièces produites, est l'un des trois facteurs
du TRS."""


def generate(pRandom):
    """Retourne le relevé horaire d'une journée de production."""

    while True:
        vLines = []

        for vHour in range(24):
            vProduced = 0 if pRandom.random() < 0.1 else pRandom.randint(80, 160)
            vScrap = pRandom.randint(0, vProduced // 8) if vProduced else 0
            vLines.append(f"{vHour:02d};{vProduced};{vScrap}")

        vInput = "\n".join(vLines)
        vRates = sorted(get_rates(vInput).values(), reverse=True)

        if vRates[0] != vRates[1]:
            return vInput


def get_rates(pInput):
    """Retourne le taux de rebut de chaque heure."""

    rRates = {}

    for vLine in pInput.strip().splitlines():
        vHour, vProduced, vScrap = vLine.split(";")
        rRates[vHour] = int(vScrap) / int(vProduced) if int(vProduced) else 0.0

    return rRates


def solve(pInput):
    """Retourne le nombre de pièces bonnes et l'heure au plus fort taux de rebut."""

    vGood = sum(
        int(vProduced) - int(vScrap)
        for _, vProduced, vScrap in (
            vLine.split(";") for vLine in pInput.strip().splitlines()
        )
    )
    vRates = get_rates(pInput)

    rAnswers = (str(vGood), max(vRates, key=vRates.get))

    return rAnswers
