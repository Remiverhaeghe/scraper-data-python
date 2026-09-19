"""
Vue consacrée à la recherche des emplois.
"""

import tkinter as tk

from gui.components import (
    create_back_button,
    create_result_label,
    create_title
)


class JobsView:
    """Affiche les paramètres de recherche des emplois."""

    def __init__(self, p_parent, p_show_home):
        """Initialise la vue des emplois."""

        self.parent = p_parent
        self.show_home = p_show_home

        self.create_widgets()

    def create_widgets(self):
        """Crée les composants de la vue des emplois."""

        create_title(
            self.parent,
            "💼 Jobs"
        )

        self.offers_label = tk.Label(
            self.parent,
            text="Nombre d'offres à récupérer :"
        )

        self.offers_label.pack()

        self.offers_entry = tk.Entry(
            self.parent
        )

        self.offers_entry.insert(
            0,
            "20"
        )

        self.offers_entry.pack(
            pady=5
        )

        self.search_button = tk.Button(
            self.parent,
            text="Rechercher les offres",
            command=self.search_jobs
        )

        self.search_button.pack(
            pady=20
        )

        create_back_button(
            self.parent,
            self.show_home
        )

        self.result_label = create_result_label(
            self.parent
        )

    def search_jobs(self):
        """Affiche temporairement le nombre d'offres demandé."""

        offers = self.offers_entry.get()

        self.result_label.config(
            text=f"Nombre d'offres demandé : {offers}"
        )
