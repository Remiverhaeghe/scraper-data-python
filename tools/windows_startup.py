"""Lancement du serveur web et du planificateur à l'ouverture de session Windows

Un fichier JobBoard Perso.cmd est placé dans le dossier Démarrage de l'utilisateur :
sans droits administrateur, et retiré en supprimant ce seul fichier. Les deux
programmes s'ouvrent dans des fenêtres réduites, où leurs messages restent lisibles.

    python -m tools.windows_startup            installe le lancement
    python -m tools.windows_startup --remove   le retire
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent

SCRIPT_NAME = "JobBoard Perso.cmd"

# Le Wi-Fi n'est pas toujours connecté à l'ouverture de session : sans attente, le
# serveur ne pourrait pas écouter sur l'adresse WEB_HOST du .env.
STARTUP_DELAY_SECONDS = 30


def get_startup_directory():
    """Retourne le dossier Démarrage de l'utilisateur Windows."""

    rDirectory = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )

    return rDirectory


def build_script(pProjectDirectory, pPython):
    """Retourne le contenu du fichier de lancement."""

    rScript = "\r\n".join(
        [
            "@echo off",
            f'cd /d "{pProjectDirectory}"',
            f"timeout /t {STARTUP_DELAY_SECONDS} /nobreak >nul",
            f'start "JobBoard Perso - serveur web" /min "{pPython}" -m web',
            f'start "JobBoard Perso - planificateur" /min "{pPython}" -m scheduler',
            "",
        ]
    )

    return rScript


def install(pStartupDirectory, pProjectDirectory, pPython):
    """Écrit le fichier de lancement et retourne son chemin."""

    rPath = Path(pStartupDirectory) / SCRIPT_NAME
    # cmd lit les fichiers .cmd dans la page de code OEM : en UTF-8, un accent du
    # chemin (C:\Users\rémi) serait mal lu.
    rPath.write_text(
        build_script(pProjectDirectory, pPython), encoding="oem", newline=""
    )

    return rPath


def remove(pStartupDirectory):
    """Supprime le fichier de lancement ; retourne s'il existait."""

    vPath = Path(pStartupDirectory) / SCRIPT_NAME
    rRemoved = vPath.exists()
    vPath.unlink(missing_ok=True)

    return rRemoved


def main(pArguments=None):
    """Installe ou retire le lancement à l'ouverture de session."""

    vParser = argparse.ArgumentParser(prog="python -m tools.windows_startup")
    vParser.add_argument(
        "--remove", action="store_true", help="retire le lancement automatique"
    )
    vArguments = vParser.parse_args(pArguments)
    vStartupDirectory = get_startup_directory()

    if vArguments.remove:
        vRemoved = remove(vStartupDirectory)
        print(
            "Lancement automatique retiré."
            if vRemoved
            else "Aucun lancement automatique n'était installé."
        )
    else:
        vPath = install(vStartupDirectory, PROJECT_DIRECTORY, sys.executable)
        print(f"Lancement automatique installé : {vPath}")
        print(
            "Le serveur web et le planificateur démarreront à la prochaine ouverture"
            " de session."
        )

    rStatus = 0

    return rStatus


if __name__ == "__main__":
    sys.exit(main())
