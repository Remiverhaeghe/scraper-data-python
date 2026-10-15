"""Défi : la vérification de trames Modbus RTU captées sur une liaison série"""

ID = "trames-modbus"
TITLE = "Les trames Modbus"
SERIES = "Réseaux industriels"
LEVEL = "confirmé"

STATEMENTS = (
    """Un analyseur a capté sur une liaison RS-485 des réponses Modbus RTU à la fonction
03, lecture de registres, une trame hexadécimale par ligne. Chaque trame contient :
l'adresse de l'esclave (1 octet), la fonction `03` (1 octet), le nombre d'octets de
données (1 octet), les données, puis le CRC sur 2 octets, octet de poids faible en
premier.

Le CRC-16 Modbus se calcule sur tous les octets qui le précèdent : on part de 0xFFFF ;
pour chaque octet, on fait un OU exclusif avec le CRC, puis, huit fois, on décale le
CRC d'un bit vers la droite et, si le bit sorti valait 1, on fait un OU exclusif avec
0xA001.

**Combien de trames ont un CRC correct ?**""",
    """Les données d'une trame sont des registres de 16 bits, octet de poids fort en
premier.

**Quelle est la somme de tous les registres des trames au CRC correct ?**""",
)
EXAMPLE = """0103020064B9AF
01030400C8012C7B80
0103020064B9AE"""
EXAMPLE_ANSWERS = ("2", "600")
HINTS = (
    "Les deux derniers octets d'une trame sont le CRC, le poids faible d'abord.",
    "Un registre vaut octet_fort × 256 + octet_faible.",
)
NOTE = """Le CRC protège chaque trame contre les erreurs de transmission : une trame dont le
CRC ne correspond pas est ignorée par le maître. Savoir le recalculer aide à
diagnostiquer une liaison perturbée ou une mauvaise vitesse de communication."""


def compute_crc(pData):
    """Retourne le CRC-16 Modbus d'une suite d'octets."""

    rCrc = 0xFFFF

    for vByte in pData:
        rCrc ^= vByte

        for _ in range(8):
            rCrc = (rCrc >> 1) ^ 0xA001 if rCrc & 1 else rCrc >> 1

    return rCrc


def build_frame(pSlave, pRegisters):
    """Retourne une trame de réponse à la fonction 03, CRC compris."""

    vData = bytes([pSlave, 3, 2 * len(pRegisters)]) + b"".join(
        vRegister.to_bytes(2, "big") for vRegister in pRegisters
    )
    vCrc = compute_crc(vData)

    rFrame = vData + vCrc.to_bytes(2, "little")

    return rFrame


def generate(pRandom):
    """Retourne des trames captées, dont certaines altérées en transmission."""

    vLines = []

    for _ in range(pRandom.randint(150, 250)):
        vFrame = bytearray(
            build_frame(
                pRandom.randint(1, 20),
                [pRandom.randint(0, 65535) for _ in range(pRandom.randint(1, 8))],
            )
        )

        if pRandom.random() < 0.15:
            vFrame[pRandom.randrange(len(vFrame))] ^= 1 << pRandom.randrange(8)

        vLines.append(vFrame.hex().upper())

    rInput = "\n".join(vLines)

    return rInput


def solve(pInput):
    """Retourne le nombre de trames valides et la somme de leurs registres."""

    vValid = 0
    vTotal = 0

    for vLine in pInput.strip().splitlines():
        vFrame = bytes.fromhex(vLine.strip())

        if compute_crc(vFrame[:-2]) != int.from_bytes(vFrame[-2:], "little"):
            continue

        vValid += 1
        vTotal += sum(
            int.from_bytes(vFrame[vIndex : vIndex + 2], "big")
            for vIndex in range(3, len(vFrame) - 2, 2)
        )

    rAnswers = (str(vValid), str(vTotal))

    return rAnswers
