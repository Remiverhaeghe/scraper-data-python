"""
Vue d'accueil de l'application.
"""

import tkinter as tk

from gui.components import create_title
from gui.styles import FONT_SUBTITLE


class HomeView:
    """Affiche le choix du domaine à utiliser."""

    def __init__(self, p_parent, p_show_books, p_show_jobs):
        """Initialise la vue d'accueil."""

        self.parent = p_parent
        self.show_books = p_show_books
        self.show_jobs = p_show_jobs

        self.create_widgets()

    def create_widgets(self):
        """Crée les composants de la vue d'accueil."""

        create_title(
            self.parent,
            "🐍 Web Scraper"
        )

        self.description_label = tk.Label(
            self.parent,
            text="Que souhaitez-vous scraper ?",
            font=FONT_SUBTITLE
        )

        self.description_label.pack(
            pady=(0, 40)
        )

        self.books_button = tk.Button(
            self.parent,
            text="📚 Livres",
            width=20,
            height=2,
            command=self.show_books
        )

        self.books_button.pack(
            pady=10
        )

        self.jobs_button = tk.Button(
            self.parent,
            text="💼 Jobs",
            width=20,
            height=2,
            command=self.show_jobs
        )

        self.jobs_button.pack(
            pady=10
        )