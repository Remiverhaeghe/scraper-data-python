"""Défi : rejouer un grafcet à partir de la trace des capteurs"""

ID = "grafcet-rejeu"
TITLE = "La trace du grafcet"
SERIES = "Automatisme"
LEVEL = "intermédiaire"

STATEMENTS = (
    """Une machine est pilotée par un grafcet linéaire avec quelques retours. Ses
transitions sont décrites sous la forme `Xa -> Xb : capteur` ; une ligne vide les
sépare de la trace, où chaque ligne donne le nom d'un capteur qui vient de passer à 1.

Au départ, seule l'étape X0 est active. À chaque événement, si une transition part de
l'étape active avec ce capteur pour réceptivité, elle est franchie ; sinon
l'événement est ignoré. Une seule étape est active à la fois.

**Quel est le numéro de l'étape active à la fin de la trace ?**""",
    """Le régleur veut savoir combien de cycles ont été terminés ou abandonnés.

**Combien de fois l'étape X0 a-t-elle été réactivée pendant la trace ?** L'activation
initiale ne compte pas.""",
)
EXAMPLE = """X0 -> X1 : depart
X1 -> X2 : capteur_haut
X2 -> X0 : capteur_bas
X1 -> X0 : arret

depart
capteur_bas
capteur_haut
capteur_bas
depart
arret
depart
capteur_haut
capteur_bas"""
EXAMPLE_ANSWERS = ("0", "3")
HINTS = (
    "Rangez les transitions dans un dictionnaire indexé par (étape, capteur).",
    "Un événement qui ne correspond à aucune transition de l'étape active ne change rien.",
)
NOTE = """C'est l'interprétation d'un grafcet à une seule étape active : un dictionnaire
(étape, réceptivité) vers étape suivante, puis un parcours de la trace. Un automate
fait la même chose à chaque cycle, en testant les réceptivités des étapes actives."""


def generate(pRandom):
    """Retourne les transitions d'un grafcet et une longue trace de capteurs."""

    vSteps = pRandom.randint(5, 9)
    vLines = [
        f"X{vStep} -> X{(vStep + 1) % vSteps} : capteur_{vStep + 1}"
        for vStep in range(vSteps)
    ]
    vLines += [
        f"X{vStep} -> X0 : defaut_{vStep}"
        for vStep in range(1, vSteps)
        if pRandom.random() < 0.4
    ]
    vSensors = [vLine.split(" : ")[1] for vLine in vLines]
    vEvents = [pRandom.choice(vSensors) for _ in range(pRandom.randint(400, 600))]

    rInput = "\n".join(pRandom.sample(vLines, len(vLines)) + [""] + vEvents)

    return rInput


def solve(pInput):
    """Retourne l'étape active finale et le nombre de réactivations de X0."""

    vTransitionText, vEventText = pInput.strip().split("\n\n")
    vTransitions = {}

    for vLine in vTransitionText.splitlines():
        vSteps, vSensor = vLine.split(" : ")
        vSource, vTarget = (int(vStep.strip()[1:]) for vStep in vSteps.split("->"))
        vTransitions[(vSource, vSensor.strip())] = vTarget

    vActive = 0
    vReturns = 0

    for vEvent in vEventText.splitlines():
        vNext = vTransitions.get((vActive, vEvent.strip()))

        if vNext is not None:
            vActive = vNext
            vReturns += vNext == 0

    rAnswers = (str(vActive), str(vReturns))

    return rAnswers
