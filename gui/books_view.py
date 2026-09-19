"""
Vue consacrée au scraping des livres.
"""

import tkinter as tk

from gui.components import (
    create_back_button,
    create_data_count,
    create_download_button,
    create_progress_bar,
    create_result_label,
    create_section,
    create_status_label,
    create_subtitle,
    create_title
)
from gui.styles import (
    COLOR_SURFACE,
    COLOR_TEXT,
    FONT_NORMAL
)


class BooksView:
    """Affiche les paramètres et les résultats du scraping des livres."""

    def __init__(self, p_parent, p_show_home):
        """Initialise la vue des livres."""

        self.parent = p_parent
        self.show_home = p_show_home

        self.create_widgets()

    def create_widgets(self):
        """Crée les composants de la vue des livres."""

        create_title(
            self.parent,
            "📚 Livres"
        )

        create_subtitle(
            self.parent,
            "Récupérez, analysez et exportez les données"
        )

        self.create_configuration_section()
        self.create_progress_section()
        self.create_result_section()

        create_back_button(
            self.parent,
            self.show_home
        )

    def create_configuration_section(self):
        """Crée la section de configuration."""

        configuration_frame = create_section(
            self.parent,
            "Configuration"
        )

        self.pages_label = tk.Label(
            configuration_frame,
            text="Nombre de pages à scraper :",
            font=FONT_NORMAL,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT
        )

        self.pages_label.pack(
            pady=5
        )

        self.pages_entry = tk.Entry(
            configuration_frame,
            width=10,
            justify="center"
        )

        self.pages_entry.insert(
            0,
            "1"
        )

        self.pages_entry.pack(
            pady=5
        )

        self.scrape_button = tk.Button(
            configuration_frame,
            text="▶ Lancer le scraping",
            command=self.scrape_books,
            width=22
        )

        self.scrape_button.pack(
            pady=10
        )

    def create_progress_section(self):
        """Crée la section de progression."""

        progress_frame = create_section(
            self.parent,
            "Progression"
        )

        self.status_label = create_status_label(
            progress_frame
        )

        self.progress_bar = create_progress_bar(
            progress_frame
        )

        self.page_label = tk.Label(
            progress_frame,
            text="Page : 0 / 0",
            font=FONT_NORMAL,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT
        )

        self.page_label.pack(
            pady=5
        )

        self.data_count_label = create_data_count(
            progress_frame
        )

    def create_result_section(self):
        """Crée la section des résultats."""

        result_frame = create_section(
            self.parent,
            "Résultats"
        )

        self.result_label = create_result_label(
            result_frame
        )

        buttons_frame = tk.Frame(
            result_frame,
            bg=COLOR_SURFACE
        )

        buttons_frame.pack(
            pady=5
        )

        create_download_button(
            buttons_frame,
            "📥 Ouvrir les données",
            self.download_data
        )

        create_download_button(
            buttons_frame,
            "📋 Ouvrir les logs",
            self.download_logs
        )

    def scrape_books(self):
        """Affiche temporairement les paramètres du scraping."""

        pages = self.pages_entry.get()

        self.status_label.config(
            text="● Prêt"
        )

        self.progress_bar["value"] = 0

        self.page_label.config(
            text=f"Page : 0 / {pages}"
        )

        self.data_count_label.config(
            text="Données trouvées : 0"
        )

        self.result_label.config(
            text=f"Scraping configuré pour {pages} page(s)"
        )

    def download_data(self):
        """Prépare l'accès aux données générées."""

        self.result_label.config(
            text="Les données seront accessibles ici"
        )

    def download_logs(self):
        """Prépare l'accès aux logs."""

        self.result_label.config(
            text="Les logs seront accessibles ici"
        )