"""
Fenêtre principale de l'application.
"""

import tkinter as tk

from gui.books_view import BooksView
from gui.home_view import HomeView
from gui.jobs_view import JobsView
from gui.styles import (
    COLOR_BACKGROUND,
    WINDOW_HEIGHT,
    WINDOW_WIDTH
)


class ApplicationWindow:
    """Gère la fenêtre principale et la navigation entre les vues."""

    def __init__(self):
        """Initialise la fenêtre."""

        self.window = tk.Tk()

        self.window.title("Web Scraper")

        self.window.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.window.configure(
            bg=COLOR_BACKGROUND
        )

        self.center_window()

        self.show_home()

    def center_window(self):
        """Centre la fenêtre sur l'écran."""

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        position_x = int(
            (screen_width - WINDOW_WIDTH) / 2
        )

        position_y = int(
            (screen_height - WINDOW_HEIGHT) / 2
        )

        self.window.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+"
            f"{position_x}+{position_y}"
        )

    def clear_window(self):
        """Supprime les composants actuellement affichés."""

        for widget in self.window.winfo_children():
            widget.destroy()

    def show_home(self):
        """Affiche la vue d'accueil."""

        self.clear_window()

        HomeView(
            self.window,
            self.show_books,
            self.show_jobs
        )

    def show_books(self):
        """Affiche la vue consacrée aux livres."""

        self.clear_window()

        BooksView(
            self.window,
            self.show_home
        )

    def show_jobs(self):
        """Affiche la vue consacrée aux emplois."""

        self.clear_window()

        JobsView(
            self.window,
            self.show_home
        )

    def run(self):
        """Lance la boucle principale de l'interface."""

        self.window.mainloop()


if __name__ == "__main__":
    application = ApplicationWindow()
    application.run()