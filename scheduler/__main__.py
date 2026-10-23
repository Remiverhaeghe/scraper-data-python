"""Point d'entrée du planificateur : python -m scheduler"""

import argparse
import signal
import threading
from datetime import datetime

from config import DATABASE_FILE
from scheduler.runner import run_due_search, run_forever
from storage.database import initialize_database
from utils.permissions import warn_permission_problems


def parse_arguments(pArguments=None):
    """Lit les options de la ligne de commande."""

    vParser = argparse.ArgumentParser(
        prog="python -m scheduler",
        description="Lance la recherche planifiée aux échéances définies dans "
        "les paramètres.",
    )
    vParser.add_argument(
        "--once",
        action="store_true",
        help="vérifie l'échéance une seule fois, puis s'arrête",
    )

    rArguments = vParser.parse_args(pArguments)

    return rArguments


def main(pArguments=None):
    """Démarre le planificateur, arrêté proprement par Ctrl+C ou SIGTERM."""

    vArguments = parse_arguments(pArguments)
    vStopEvent = threading.Event()
    warn_permission_problems()

    # SIGTERM est le signal d'arrêt envoyé par Docker.
    for vSignal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(vSignal, lambda *_: vStopEvent.set())

    initialize_database(DATABASE_FILE)

    if vArguments.once:
        run_due_search(DATABASE_FILE, datetime.now(), vStopEvent)
    else:
        run_forever(DATABASE_FILE, vStopEvent)


if __name__ == "__main__":
    main()
