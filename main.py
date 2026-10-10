"""Point d'entrée de l'application"""

import sys

from config import DATABASE_FILE
from gui.app import run
from storage.database import initialize_database


def main():
    """Initialise la base et lance l'interface graphique."""

    initialize_database(DATABASE_FILE)

    sys.exit(run())


if __name__ == "__main__":
    main()
