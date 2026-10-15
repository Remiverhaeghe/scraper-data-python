"""Défi : l'analyse du journal d'accès d'une API"""

from collections import Counter

ID = "journal-http"
TITLE = "Le journal de l'API"
SERIES = "Exploitation"
LEVEL = "débutant"

STATEMENTS = (
    """Le serveur de l'API des commandes écrit une ligne par requête :
`horodatage adresse méthode chemin statut durée_ms`. Un statut de 500 à 599 signale
une erreur du serveur.

**Combien de requêtes ont reçu une erreur serveur ?**""",
    """L'équipe d'exploitation cherche le pic de charge.

**Quelle minute, au format HH:MM, a reçu le plus de requêtes ?**""",
)
EXAMPLE = """2026-10-12T08:15:32 10.0.0.5 GET /api/commandes 200 120
2026-10-12T08:15:59 10.0.0.7 POST /api/commandes 503 2100
2026-10-12T08:16:03 10.0.0.5 GET /api/clients 200 80
2026-10-12T08:15:10 10.0.0.9 GET /api/stock 500 950
2026-10-12T08:17:45 10.0.0.5 GET /api/stock 404 15"""
EXAMPLE_ANSWERS = ("2", "08:15")
HINTS = (
    "Le statut est l'avant-dernier champ de chaque ligne.",
    "La minute se lit dans l'horodatage, entre le T et les secondes.",
)
NOTE = """C'est le quotidien de l'exploitation : découper des lignes de journal, compter
et regrouper. En ligne de commande, `awk '$5 >= 500' fichier | wc -l` répond à la
première partie ; en Python, un `Counter` sur la minute répond à la seconde."""

PATHS = ("/api/commandes", "/api/clients", "/api/stock", "/api/factures")
STATUSES = (200, 200, 200, 200, 201, 204, 400, 404, 500, 502, 503)


def generate(pRandom):
    """Retourne deux heures de journal d'accès, avec un pic de charge."""

    while True:
        vPeak = pRandom.randint(0, 119)
        vLines = []

        for _ in range(pRandom.randint(1500, 2500)):
            vMinute = vPeak if pRandom.random() < 0.03 else pRandom.randint(0, 119)
            vLines.append(
                f"2026-10-12T{8 + vMinute // 60:02d}:{vMinute % 60:02d}:"
                f"{pRandom.randint(0, 59):02d} 10.0.{pRandom.randint(0, 9)}."
                f"{pRandom.randint(1, 254)} {pRandom.choice(('GET', 'POST'))} "
                f"{pRandom.choice(PATHS)} {pRandom.choice(STATUSES)} "
                f"{pRandom.randint(5, 3000)}"
            )

        vInput = "\n".join(sorted(vLines))
        vTop = get_minutes(vInput).most_common(2)

        if vTop[0][1] != vTop[1][1]:
            return vInput


def get_minutes(pInput):
    """Retourne le nombre de requêtes par minute."""

    rMinutes = Counter(vLine.split()[0][11:16] for vLine in pInput.strip().splitlines())

    return rMinutes


def solve(pInput):
    """Retourne le nombre d'erreurs serveur et la minute la plus chargée."""

    vErrors = sum(
        500 <= int(vLine.split()[4]) <= 599 for vLine in pInput.strip().splitlines()
    )

    rAnswers = (str(vErrors), get_minutes(pInput).most_common(1)[0][0])

    return rAnswers
