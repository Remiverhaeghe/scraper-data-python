"""Son court de réussite, joué par Windows sans dépendance

Le carillon de deux notes est généré une fois en WAV dans le dossier temporaire,
puis lu de façon asynchrone : l'interface ne se fige pas pendant le son.
"""

import math
import struct
import sys
import tempfile
import wave
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

SAMPLE_RATE = 22050
# Deux notes montantes, do puis sol, avec une attaque et une fin adoucies
NOTES = ((523.25, 0.12), (783.99, 0.22))
VOLUME = 0.25
SOUND_FILE = Path(tempfile.gettempdir()) / "jobboard-reussite.wav"


def build_chime():
    """Retourne les échantillons 16 bits du carillon."""

    vSamples = []

    for vFrequency, vDuration in NOTES:
        vCount = int(SAMPLE_RATE * vDuration)

        for vIndex in range(vCount):
            vEnvelope = min(1.0, vIndex / 200, (vCount - vIndex) / 800)
            vValue = (
                VOLUME
                * vEnvelope
                * math.sin(2 * math.pi * vFrequency * vIndex / SAMPLE_RATE)
            )
            vSamples.append(int(vValue * 32767))

    rData = struct.pack(f"<{len(vSamples)}h", *vSamples)

    return rData


def write_chime(pPath=SOUND_FILE):
    """Écrit le carillon en WAV s'il n'existe pas encore ; retourne son chemin."""

    if not pPath.exists():
        with wave.open(str(pPath), "wb") as vFile:
            vFile.setnchannels(1)
            vFile.setsampwidth(2)
            vFile.setframerate(SAMPLE_RATE)
            vFile.writeframes(build_chime())

    return pPath


def play_success():
    """Joue le carillon de réussite sous Windows ; ailleurs, ne fait rien."""

    if sys.platform != "win32":
        return

    try:
        import winsound  # pylint: disable=import-outside-toplevel

        winsound.PlaySound(
            str(write_chime()), winsound.SND_FILENAME | winsound.SND_ASYNC
        )

    except (OSError, RuntimeError):
        logger.warning("Son de réussite impossible à jouer")
