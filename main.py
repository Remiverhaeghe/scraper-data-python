"""Point d'entrée de l'application"""

from config import DATABASE_FILE
from gui.window import ApplicationWindow
from storage.database import initialize_database


def main():
    """Initialise l'application et lance l'interface graphique."""

    initialize_database(DATABASE_FILE)

    vApplication = ApplicationWindow()

    vApplication.mainloop()


if __name__ == "__main__":
    main()
