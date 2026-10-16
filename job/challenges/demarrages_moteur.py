"""Défi : le temps de marche des moteurs et les redémarrages trop rapprochés"""

ID = "demarrages-moteur"
TITLE = "Les démarrages du moteur"
SERIES = "Maintenance"
LEVEL = "débutant"

STATEMENTS = (
    """Le superviseur d'un atelier enregistre les ordres envoyés aux moteurs pendant une
journée, dans l'ordre chronologique : l'heure, le moteur et l'ordre, par exemple
`08:15:30 M4 marche`.

Un ordre qui ne change rien est ignoré : `marche` pour un moteur qui tourne déjà,
`arret` pour un moteur déjà à l'arrêt. Tous les moteurs sont à l'arrêt à 00:00:00 ;
un moteur encore en marche en fin de journée s'arrête à 24:00:00.

**Quel est le temps de marche cumulé de tous les moteurs, en secondes ?**""",
    """Pour laisser refroidir le bobinage, un moteur ne doit pas redémarrer moins de
600 secondes après son dernier arrêt. Seuls les démarrages effectifs comptent.

**Combien de démarrages ne respectent pas ce délai ?**""",
)
EXAMPLE = """00:00:00 M1 marche
00:10:00 M1 arret
00:15:00 M1 marche
00:15:30 M2 marche
00:20:00 M1 marche
00:30:00 M1 arret
01:00:00 M2 arret
23:50:00 M3 marche"""
EXAMPLE_ANSWERS = ("4770", "1")
HINTS = (
    "Convertissez chaque heure en secondes depuis minuit : 01:00:00 vaut 3600.",
    "Gardez, par moteur, l'heure de son démarrage en cours et celle de son dernier "
    "arrêt.",
)
NOTE = """Un dictionnaire par moteur suffit : l'heure de démarrage tant qu'il tourne,
l'heure du dernier arrêt sinon. Un ordre redondant ne touche à rien, ce qui évite de
compter deux fois la même marche ; la fin de journée referme les marches encore
ouvertes.

Les compteurs d'heures de marche et de démarrages servent à planifier la maintenance
(roulements, contacteurs) ; un démarrage trop rapproché échauffe le bobinage et use
prématurément le moteur."""

DAY_SECONDS = 86400
COOLING_SECONDS = 600


def format_time(pSeconds):
    """Écrit un nombre de secondes depuis minuit au format HH:MM:SS."""

    vHours, vRest = divmod(pSeconds, 3600)

    rText = f"{vHours:02d}:{vRest // 60:02d}:{vRest % 60:02d}"

    return rText


def generate(pRandom):
    """Retourne une journée d'ordres pour une douzaine de moteurs."""

    vEvents = [
        (
            pRandom.randrange(DAY_SECONDS),
            f"M{pRandom.randint(1, 12)}",
            pRandom.choice(("marche", "marche", "arret")),
        )
        for _ in range(pRandom.randint(500, 700))
    ]
    vEvents.sort()

    rInput = "\n".join(
        f"{format_time(vTime)} {vMotor} {vOrder}" for vTime, vMotor, vOrder in vEvents
    )

    return rInput


def parse_time(pText):
    """Retourne le nombre de secondes depuis minuit d'une heure HH:MM:SS."""

    vHours, vMinutes, vSeconds = (int(vPart) for vPart in pText.split(":"))

    rSeconds = vHours * 3600 + vMinutes * 60 + vSeconds

    return rSeconds


def solve(pInput):
    """Retourne le temps de marche cumulé et le nombre de redémarrages trop rapides."""

    vStarted = {}
    vStopped = {}
    vRunning = 0
    vTooSoon = 0

    for vLine in pInput.strip().splitlines():
        vText, vMotor, vOrder = vLine.split()
        vTime = parse_time(vText)

        if vOrder == "marche" and vMotor not in vStarted:
            if vMotor in vStopped and vTime - vStopped[vMotor] < COOLING_SECONDS:
                vTooSoon += 1

            vStarted[vMotor] = vTime
        elif vOrder == "arret" and vMotor in vStarted:
            vRunning += vTime - vStarted.pop(vMotor)
            vStopped[vMotor] = vTime

    vRunning += sum(DAY_SECONDS - vStart for vStart in vStarted.values())

    rAnswers = (str(vRunning), str(vTooSoon))

    return rAnswers
