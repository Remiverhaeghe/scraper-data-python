"""Défi : l'énergie en heures pleines et les dépassements d'une courbe de charge"""

ID = "courbe-charge"
TITLE = "La courbe de charge"
SERIES = "Électricité"
LEVEL = "intermédiaire"

STATEMENTS = (
    """Le compteur d'un atelier relève la puissance moyenne appelée sur chaque quart
d'heure. La première ligne donne la puissance souscrite, `souscrite S`, en watts.
Chaque ligne suivante est un relevé, dans l'ordre : le jour, l'heure de début du
quart d'heure et la puissance moyenne en watts, par exemple `J2 14:30 31840`.

Les heures creuses vont de 22:00 à 06:00 : un quart d'heure commençant à 22:00 ou
après, ou avant 06:00, est creux ; tous les autres sont pleins. Sur un quart d'heure,
l'énergie consommée vaut la puissance multipliée par 0,25 h.

**Quelle énergie, en Wh, a été consommée en heures pleines ?**""",
    """Le fournisseur facture un supplément à chaque épisode de dépassement : une suite
de relevés consécutifs dont la puissance est strictement supérieure à la puissance
souscrite. Un épisode qui continue après minuit reste un seul épisode.

**Combien d'épisodes de dépassement le relevé contient-il ?**""",
)
EXAMPLE = """souscrite 9000
J1 05:30 4000
J1 05:45 9200
J1 06:00 9600
J1 06:15 8000
J1 21:45 9400
J1 22:00 9800"""
EXAMPLE_ANSWERS = ("6750", "2")
HINTS = (
    "Comparer l'heure sous forme de texte HH:MM suffit : '05:45' < '06:00'.",
    "Un épisode commence quand un relevé dépasse alors que le précédent ne dépassait "
    "pas.",
)
NOTE = """La première partie est une somme filtrée : les puissances en watts sont des
multiples de 4, si bien que P / 4 tombe juste et qu'aucun arrondi n'intervient. La
seconde compte des fronts montants, comme on détecte un front sur une entrée
d'automate : on garde l'état précédent (dépassement ou non) et on compte les passages
de non à oui.

Ce découpage heures pleines / heures creuses et le suivi des dépassements sont la base
du choix d'une puissance souscrite : trop basse, les suppléments s'accumulent ; trop
haute, l'abonnement coûte cher toute l'année."""

QUARTERS_PER_DAY = 96


def generate(pRandom):
    """Retourne une semaine environ de relevés au quart d'heure."""

    vSubscribed = pRandom.randrange(30000, 42000, 1000)
    vLines = [f"souscrite {vSubscribed}"]

    for vDay in range(1, pRandom.randint(5, 8) + 1):
        for vQuarter in range(QUARTERS_PER_DAY):
            vHour, vMinute = divmod(vQuarter * 15, 60)
            vWorking = 7 <= vHour < 19
            vBase = vSubscribed * (0.75 if vWorking else 0.2)
            vPower = vBase + pRandom.uniform(-0.2, 0.32) * vSubscribed
            # Multiple de 20 W : l'énergie d'un quart d'heure reste un entier de Wh.
            vPower = max(0, round(vPower / 20) * 20)
            vLines.append(f"J{vDay} {vHour:02d}:{vMinute:02d} {vPower}")

    rInput = "\n".join(vLines)

    return rInput


def solve(pInput):
    """Retourne l'énergie en heures pleines et le nombre d'épisodes de dépassement."""

    vLines = pInput.strip().splitlines()
    vSubscribed = int(vLines[0].split()[1])
    vFullEnergy = 0
    vEpisodes = 0
    vAbove = False

    for vLine in vLines[1:]:
        _, vTime, vPower = vLine.split()
        vPower = int(vPower)

        if "06:00" <= vTime < "22:00":
            vFullEnergy += vPower // 4

        if vPower > vSubscribed and not vAbove:
            vEpisodes += 1

        vAbove = vPower > vSubscribed

    rAnswers = (str(vFullEnergy), str(vEpisodes))

    return rAnswers
