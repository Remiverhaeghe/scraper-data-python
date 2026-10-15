"""Défi : les arrêts d'une ligne de production pendant un poste"""

from collections import Counter

ID = "arrets-ligne"
TITLE = "Les arrêts de la ligne 3"
SERIES = "Industrie"
LEVEL = "débutant"

STATEMENTS = (
    """La ligne 3 tourne sur le poste du matin, de 06:00 à 14:00. Chaque arrêt est noté
par l'opérateur sous la forme `début-fin;cause`, dans le désordre. Deux arrêts ne se
chevauchent jamais, et la fin d'un arrêt est exclue : `06:10-06:14` dure 4 minutes.

**Combien de minutes la ligne a-t-elle été arrêtée pendant le poste ?**""",
    """Le responsable de production veut traiter d'abord la cause la plus coûteuse.

**Quelle cause totalise le plus de minutes d'arrêt ?** Donnez son nom tel qu'il est
écrit dans le journal.""",
)
EXAMPLE = """07:15-07:27;Bourrage
06:10-06:14;Réglage
09:00-09:05;Bourrage
11:40-12:00;Manque matière"""
EXAMPLE_ANSWERS = ("41", "Manque matière")
HINTS = (
    "Convertissez chaque heure en minutes depuis minuit : HH × 60 + MM.",
    "Pour la seconde partie, additionnez les durées dans un dictionnaire indexé par cause.",
)
NOTE = """Il suffit de découper chaque ligne sur `;` puis sur `-`, et de convertir les heures
en minutes. La seconde partie se résout avec un dictionnaire de cumuls, ou un `Counter`
en Python. Pour aller plus loin : calculez la disponibilité du poste, temps de marche
divisé par 480 minutes."""

CAUSES = (
    "Bourrage",
    "Réglage",
    "Panne électrique",
    "Manque matière",
    "Changement de série",
    "Nettoyage",
    "Attente qualité",
)
SHIFT_START = 6 * 60
SHIFT_LENGTH = 8 * 60


def format_time(pMinutes):
    """Retourne une heure HH:MM à partir de minutes depuis minuit."""

    rText = f"{pMinutes // 60:02d}:{pMinutes % 60:02d}"

    return rText


def generate(pRandom):
    """Retourne un journal d'arrêts du poste, dans le désordre."""

    while True:
        vLines = []
        vTime = SHIFT_START

        while True:
            vStart = vTime + pRandom.randint(0, 12)
            vEnd = vStart + pRandom.randint(1, 14)

            if vEnd > SHIFT_START + SHIFT_LENGTH:
                break

            vLines.append(
                f"{format_time(vStart)}-{format_time(vEnd)};{pRandom.choice(CAUSES)}"
            )
            vTime = vEnd

        vInput = "\n".join(pRandom.sample(vLines, len(vLines)))
        vTotals = Counter(get_durations(vInput)).most_common(2)

        # Une seule cause en tête : la réponse ne doit pas être ambiguë.
        if len(vTotals) < 2 or vTotals[0][1] != vTotals[1][1]:
            return vInput


def get_durations(pInput):
    """Retourne la durée cumulée de chaque cause, en minutes."""

    rDurations = Counter()

    for vLine in pInput.strip().splitlines():
        vPeriod, vCause = vLine.split(";")
        vStart, vEnd = (
            int(vTime[:2]) * 60 + int(vTime[3:]) for vTime in vPeriod.split("-")
        )
        rDurations[vCause] += vEnd - vStart

    return rDurations


def solve(pInput):
    """Retourne la durée totale d'arrêt et la cause la plus coûteuse."""

    vDurations = get_durations(pInput)

    rAnswers = (str(sum(vDurations.values())), vDurations.most_common(1)[0][0])

    return rAnswers
