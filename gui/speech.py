"""Lecture à voix haute par la synthèse vocale de Windows, sans dépendance

Le texte passe par l'entrée standard d'un PowerShell qui appelle System.Speech :
il n'est jamais placé dans la ligne de commande, donc jamais interprété.
"""

import shutil
import sys

from PySide6.QtCore import QObject, QProcess, Signal

from utils.logger import get_logger

logger = get_logger(__name__)

# Voix française si elle est installée, sinon la voix par défaut du système
SPEECH_SCRIPT = (
    "[Console]::InputEncoding = [Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Speech; "
    "$vVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "try { $vVoice.SelectVoiceByHints('NotSet', 'NotSet', 0, "
    "[Globalization.CultureInfo]'fr-FR') } catch {}; "
    "$vVoice.Speak([Console]::In.ReadToEnd())"
)


def find_powershell():
    """Retourne le chemin de PowerShell sous Windows, ou None ailleurs."""

    rPath = shutil.which("powershell") if sys.platform == "win32" else None

    return rPath


class Speaker(QObject):
    """Lit un texte à voix haute ; finished est émis à la fin de la lecture."""

    finished = Signal()

    def __init__(self, pParent=None):
        """Prépare le processus de lecture, lancé à chaque texte."""
        super().__init__(pParent)

        self.program = find_powershell()
        self.process = None

    def is_available(self):
        """Indique si la synthèse vocale est utilisable sur ce système."""
        rAvailable = self.program is not None

        return rAvailable

    def speak(self, pText):
        """Lit pText ; une lecture en cours est interrompue."""
        self.stop()

        if not self.is_available():
            self.finished.emit()
            return

        self.process = QProcess(self)
        self.process.finished.connect(lambda *_pArgs: self.finished.emit())
        self.process.errorOccurred.connect(self.report_error)
        self.process.start(
            self.program, ["-NoProfile", "-NonInteractive", "-Command", SPEECH_SCRIPT]
        )
        self.process.write(pText.encode("utf-8"))
        self.process.closeWriteChannel()

    def report_error(self, pError):
        """Journalise une lecture impossible, puis rend la main comme une lecture finie."""
        logger.warning("Lecture à voix haute impossible : %s", pError)
        self.finished.emit()

    def stop(self):
        """Arrête la lecture en cours, sans signaler de fin."""
        if self.process is not None:
            self.process.finished.disconnect()
            self.process.kill()
            self.process.waitForFinished(1000)
            self.process = None
