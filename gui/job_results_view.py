"""Affichage des résultats de recherche Jobs"""

import tkinter as tk
import webbrowser

from gui.styles import (
    COLOR_BORDER,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_SECONDARY,
    FONT_NORMAL,
    FONT_SECTION,
)


class JobResultsView:
    """Affiche une liste d'offres d'emploi."""

    def __init__(self, pParent):
        """Initialise la zone de résultats."""

        self.parent = pParent
        self.result_items = []

        self.create_view()

    def create_view(self):
        """Construit la zone d'affichage des résultats."""

        self.container = tk.Frame(self.parent, bg=COLOR_SURFACE)

        self.container.pack(fill="both", expand=True, padx=10, pady=10)

    def display_results(self, pItems):
        """Affiche les offres récupérées."""

        self.clear_results()
        self.result_items = pItems

        if pItems is None or pItems.empty:
            tk.Label(
                self.container,
                text="Aucune offre trouvée.",
                font=FONT_NORMAL,
                fg=COLOR_TEXT_SECONDARY,
                bg=COLOR_SURFACE,
            ).pack(pady=20)

        else:
            for _, vItem in pItems.iterrows():
                self.create_job_card(vItem)

    def clear_results(self):
        """Supprime les résultats précédemment affichés."""

        for vWidget in self.container.winfo_children():
            vWidget.destroy()

    def create_job_card(self, pItem):
        """Crée une carte représentant une offre."""

        vCard = tk.Frame(
            self.container,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )

        vCard.pack(fill="x", padx=5, pady=5)

        vTitle = self.get_value(pItem, "title", "Titre non renseigné")

        vCompany = self.get_value(pItem, "company", "Entreprise non renseignée")

        vLocation = self.get_value(pItem, "location", "Localisation non renseignée")

        vContract = self.get_value(pItem, "contract")

        vSource = self.get_value(pItem, "source", "Source inconnue")

        tk.Label(
            vCard,
            text=vTitle,
            font=FONT_SECTION,
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 2))

        tk.Label(
            vCard,
            text=vCompany,
            font=FONT_NORMAL,
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_SURFACE,
            anchor="w",
        ).pack(fill="x", padx=15)

        vInformation = " • ".join(
            vValue for vValue in (vLocation, vContract, vSource) if vValue
        )

        tk.Label(
            vCard,
            text=vInformation,
            font=FONT_NORMAL,
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_SURFACE,
            anchor="w",
        ).pack(fill="x", padx=15, pady=(2, 5))

        vUrl = self.get_value(pItem, "url")

        if vUrl:
            tk.Button(
                vCard, text="Voir l'offre", command=lambda: self.open_url(vUrl)
            ).pack(anchor="e", padx=15, pady=(0, 10))

    def get_value(self, pItem, pColumn, pDefault=None):
        """Récupère une valeur de manière sécurisée."""

        vValue = pItem.get(pColumn, pDefault)

        if vValue is not None:
            if hasattr(vValue, "item"):
                vValue = vValue.item()

            if not isinstance(vValue, str):
                vValue = str(vValue)

            if not vValue.strip():
                vValue = pDefault

        rValue = vValue

        return rValue

    def open_url(self, pUrl):
        """Ouvre l'offre dans le navigateur."""

        webbrowser.open(pUrl)
