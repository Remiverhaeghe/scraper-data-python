"""Vue graphique consacrée aux offres d'emploi"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from gui.job_controller import JobController
from gui.job_results_view import JobResultsView
from gui.styles import COLOR_BACKGROUND, COLOR_SURFACE, FONT_NORMAL, BUTTON_WIDTH


class JobsView:
    """Affiche l'interface de recherche des offres d'emploi."""

    def __init__(self, pParent, pShowHome):
        """Initialise la vue Jobs."""
        self.parent = pParent
        self.show_home = pShowHome
        self.controller = JobController()
        self.results_view = None

        self.keyword = tk.StringVar(value="Développeur Java")

        self.location = tk.StringVar(value="Lille")

        self.max_items = tk.StringVar(value="20")

        self.france_travail = tk.BooleanVar(value=False)

        self.greenhouse = tk.BooleanVar(value=True)

        self.lever = tk.BooleanVar(value=False)

        self.status = tk.StringVar(value="Prêt")

        self.result_count = tk.StringVar(value="0")

        self.source_count = tk.StringVar(value="0")

        self.progress_value = tk.DoubleVar(value=0)

        self.search_thread = None
        self.search_result = None
        self.search_error = None
        self.search_cancelled = False

        self.create_view()

    def create_view(self):
        """Construit l'interface complète Jobs."""
        self.clear_view()

        vContainer = tk.Frame(self.parent, bg=COLOR_BACKGROUND)

        vContainer.pack(fill="both", expand=True, padx=40, pady=25)

        self.create_header(vContainer)

        self.create_configuration_section(vContainer)

        self.create_progress_section(vContainer)

        self.create_results_section(vContainer)

    def clear_view(self):
        """Supprime les widgets précédemment affichés."""
        for vWidget in self.parent.winfo_children():
            vWidget.destroy()

    def create_header(self, pParent):
        """Construit l'en-tête de la vue Jobs."""
        vHeader = tk.Frame(pParent, bg=COLOR_BACKGROUND)

        vHeader.pack(fill="x", pady=(0, 25))

        vTitleFrame = tk.Frame(vHeader, bg=COLOR_BACKGROUND)

        vTitleFrame.pack(side="left")

        tk.Label(
            vTitleFrame,
            text="💼  Offres d'emploi",
            font=("Segoe UI", 28, "bold"),
            bg=COLOR_BACKGROUND,
            fg="#0F172A",
        ).pack(anchor="w")

        tk.Label(
            vTitleFrame,
            text="Recherchez, centralisez et analysez les offres",
            font=("Segoe UI", 12),
            bg=COLOR_BACKGROUND,
            fg="#52658A",
        ).pack(anchor="w", pady=(4, 0))

        tk.Button(
            vHeader,
            text="←  Retour à l'accueil",
            command=self.go_home,
            width=BUTTON_WIDTH,
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_SURFACE,
            fg="#0F172A",
            activebackground="#E8F1FF",
            relief="solid",
            bd=1,
            padx=12,
            pady=7,
        ).pack(side="right", anchor="n")

    def create_card(self, pParent, pTitle, pSubtitle):
        """Crée une carte principale."""
        vCard = tk.Frame(
            pParent,
            bg=COLOR_SURFACE,
            highlightthickness=1,
            highlightbackground="#D6E2F0",
        )

        vCard.pack(fill="x", pady=(0, 18))

        vHeader = tk.Frame(vCard, bg=COLOR_SURFACE)

        vHeader.pack(fill="x", padx=22, pady=(18, 12))

        tk.Label(
            vHeader,
            text=pTitle,
            font=("Segoe UI", 16, "bold"),
            bg=COLOR_SURFACE,
            fg="#0F172A",
        ).pack(anchor="w")

        tk.Label(
            vHeader,
            text=pSubtitle,
            font=("Segoe UI", 10),
            bg=COLOR_SURFACE,
            fg="#52658A",
        ).pack(anchor="w", pady=(3, 0))

        vContent = tk.Frame(vCard, bg=COLOR_SURFACE)

        vContent.pack(fill="x", padx=22, pady=(0, 20))

        return vCard, vContent

    def create_configuration_section(self, pParent):
        """Construit la zone de configuration de la recherche."""
        vCard, vContent = self.create_card(
            pParent, "Configuration", "Définissez les paramètres de votre recherche"
        )

        vFields = tk.Frame(vContent, bg=COLOR_SURFACE)

        vFields.pack(fill="x")

        vFields.columnconfigure(0, weight=2)

        vFields.columnconfigure(1, weight=2)

        vFields.columnconfigure(2, weight=1)

        self.create_field(vFields, "Mot-clé", self.keyword, 0)

        self.create_field(vFields, "Localisation", self.location, 1)

        self.create_field(vFields, "Nombre maximum", self.max_items, 2)

        vSourcesTitle = tk.Label(
            vContent,
            text="Sources",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_SURFACE,
            fg="#52658A",
        )

        vSourcesTitle.pack(anchor="w", pady=(18, 7))

        vSources = tk.Frame(vContent, bg=COLOR_SURFACE)

        vSources.pack(anchor="w")

        self.create_source_checkbutton(vSources, "France Travail", self.france_travail)

        self.create_source_checkbutton(vSources, "Greenhouse", self.greenhouse)

        self.create_source_checkbutton(vSources, "Lever", self.lever)

        vActions = tk.Frame(vContent, bg=COLOR_SURFACE)

        vActions.pack(fill="x", pady=(20, 0))

        self.search_button = tk.Button(
            vActions,
            text="▶  Lancer la recherche",
            command=self.search_jobs,
            font=("Segoe UI", 11, "bold"),
            bg="#1769E0",
            fg="white",
            activebackground="#0F56BE",
            activeforeground="white",
            relief="flat",
            padx=25,
            pady=10,
        )

        self.search_button.pack(side="left")

        self.stop_button = tk.Button(
            vActions,
            text="Arrêter",
            command=self.stop_search,
            font=("Segoe UI", 10),
            state="disabled",
            padx=18,
            pady=8,
        )

        self.stop_button.pack(side="left", padx=(10, 0))

    def create_field(self, pParent, pLabel, pVariable, pColumn):
        """Crée un champ de configuration."""
        vFrame = tk.Frame(pParent, bg=COLOR_SURFACE)

        vFrame.grid(row=0, column=pColumn, sticky="ew", padx=(0, 15))

        tk.Label(
            vFrame, text=pLabel, font=("Segoe UI", 10), bg=COLOR_SURFACE, fg="#52658A"
        ).pack(anchor="w")

        tk.Entry(
            vFrame, textvariable=pVariable, font=FONT_NORMAL, relief="solid", bd=1
        ).pack(fill="x", pady=(6, 0), ipady=5)

    def create_source_checkbutton(self, pParent, pText, pVariable):
        """Crée une case de sélection d'une source."""
        tk.Checkbutton(
            pParent,
            text=pText,
            variable=pVariable,
            font=FONT_NORMAL,
            bg=COLOR_SURFACE,
            activebackground=COLOR_SURFACE,
            padx=5,
        ).pack(side="left", padx=(0, 25))

    def create_progress_section(self, pParent):
        """Construit la zone de progression."""
        vCard, vContent = self.create_card(
            pParent, "Progression", "Suivez l'avancement de la recherche en temps réel"
        )

        vStatus = tk.Frame(vContent, bg=COLOR_SURFACE)

        vStatus.pack(fill="x")

        vStatusIndicator = tk.Frame(vStatus, bg=COLOR_SURFACE)

        vStatusIndicator.pack(side="left")

        self.status_indicator = tk.Label(
            vStatusIndicator,
            text="●",
            font=("Segoe UI", 22),
            bg=COLOR_SURFACE,
            fg="#94A3B8",
        )

        self.status_indicator.pack(side="left")

        vStatusText = tk.Frame(vStatusIndicator, bg=COLOR_SURFACE)

        vStatusText.pack(side="left", padx=(8, 0))

        tk.Label(
            vStatusText,
            textvariable=self.status,
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_SURFACE,
            fg="#0F172A",
        ).pack(anchor="w")

        tk.Label(
            vStatusText,
            text="Recherche d'offres en cours",
            font=("Segoe UI", 9),
            bg=COLOR_SURFACE,
            fg="#52658A",
        ).pack(anchor="w")

        self.progress_label = tk.Label(
            vStatus,
            text="0 %",
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_SURFACE,
            fg="#0F172A",
        )

        self.progress_label.pack(side="right")

        self.progress_bar = ttk.Progressbar(
            vContent, variable=self.progress_value, maximum=100, mode="determinate"
        )

        self.progress_bar.pack(fill="x", pady=(15, 20))

        vStatistics = tk.Frame(vContent, bg=COLOR_SURFACE)

        vStatistics.pack(fill="x")

        vStatistics.columnconfigure(0, weight=1)

        vStatistics.columnconfigure(1, weight=1)

        self.create_statistic(vStatistics, "Offres trouvées", self.result_count, 0)

        self.create_statistic(vStatistics, "Sources utilisées", self.source_count, 1)

    def create_statistic(self, pParent, pLabel, pVariable, pColumn):
        """Crée un indicateur statistique."""
        vFrame = tk.Frame(pParent, bg=COLOR_SURFACE)

        vFrame.grid(row=0, column=pColumn, sticky="nsew")

        tk.Label(
            vFrame, text=pLabel, font=("Segoe UI", 10), bg=COLOR_SURFACE, fg="#52658A"
        ).pack()

        tk.Label(
            vFrame,
            textvariable=pVariable,
            font=("Segoe UI", 18, "bold"),
            bg=COLOR_SURFACE,
            fg="#0F172A",
        ).pack(pady=(3, 0))

    def create_results_section(self, pParent):
        """Construit la zone de résultats."""
        vCard, vContent = self.create_card(
            pParent, "Résultats", "Consultez les offres récupérées"
        )

        self.results_container = tk.Frame(vContent, bg=COLOR_SURFACE)

        self.results_container.pack(fill="both", expand=True)

        self.results_view = JobResultsView(self.results_container)

    def get_selected_sources(self):
        """Retourne les sources sélectionnées."""
        vSources = []

        if self.france_travail.get():
            vSources.append("france-travail")

        if self.greenhouse.get():
            vSources.append("greenhouse")

        if self.lever.get():
            vSources.append("lever")

        return vSources

    def search_jobs(self):
        """Valide les paramètres et lance la recherche."""
        if self.search_thread is None:
            try:
                vMaxItems = int(self.max_items.get())

                if vMaxItems <= 0:
                    raise ValueError("Le nombre maximum doit être supérieur à zéro.")

                vSources = self.get_selected_sources()

                if not vSources:
                    raise ValueError("Sélectionnez au moins une source.")

                self.search_result = None
                self.search_error = None
                self.search_cancelled = False

                self.status.set("Recherche en cours...")

                self.result_count.set("0")

                self.source_count.set(str(len(vSources)))

                self.progress_value.set(10)

                self.progress_label.config(text="10 %")

                self.results_view.clear_results()

                self.set_search_state(True)

                vThread = threading.Thread(
                    target=self.run_search,
                    args=(
                        vMaxItems,
                        self.keyword.get().strip() or None,
                        self.location.get().strip() or None,
                        vSources,
                    ),
                    daemon=True,
                )

                self.search_thread = vThread

                vThread.start()

                self.check_search_result()

            except ValueError as vException:
                self.status.set("Erreur")

                messagebox.showwarning("Paramètres invalides", str(vException))

    def run_search(self, pMaxItems, pKeyword, pLocation, pSources):
        """Exécute la recherche dans le thread secondaire."""
        try:
            self.search_result = self.controller.search_jobs(
                pMaxItems, pKeyword, pLocation, pSources
            )

        except Exception as vException:
            self.search_error = vException

    def check_search_result(self):
        """Vérifie périodiquement l'état de la recherche."""
        if self.search_thread is not None:
            if self.search_thread.is_alive():
                self.progress_value.set(50)

                self.progress_label.config(text="50 %")

                self.parent.after(100, self.check_search_result)
            else:
                self.finish_search()

    def finish_search(self):
        """Termine proprement la recherche."""
        self.search_thread = None

        if self.search_cancelled:
            self.status.set("Recherche arrêtée")

            self.status_indicator.config(fg="#94A3B8")

            self.progress_value.set(0)

            self.progress_label.config(text="0 %")

        elif self.search_error is not None:
            self.status.set("Erreur")

            self.status_indicator.config(fg="#DC2626")

            self.progress_value.set(0)

            self.progress_label.config(text="0 %")

            messagebox.showerror(
                "Erreur", f"La recherche a échoué :\n{self.search_error}"
            )

        else:
            vCount = len(self.search_result.items)

            self.result_count.set(str(vCount))

            self.results_view.display_results(self.search_result.items)

            self.progress_value.set(100)

            self.progress_label.config(text="100 %")

            self.status.set("Recherche terminée")

            self.status_indicator.config(fg="#16A34A")

        self.set_search_state(False)

    def stop_search(self):
        """Arrête la surveillance de la recherche côté interface."""
        if self.search_thread is not None:
            self.search_cancelled = True
            self.search_thread = None

            self.progress_value.set(0)

            self.progress_label.config(text="0 %")

            self.status.set("Recherche arrêtée")

            self.status_indicator.config(fg="#94A3B8")

            self.set_search_state(False)

    def set_search_state(self, pRunning):
        """Met à jour l'état des boutons."""
        if pRunning:
            self.search_button.config(state="disabled")

            self.stop_button.config(state="normal")

        else:
            self.search_button.config(state="normal")

            self.stop_button.config(state="disabled")

    def go_home(self):
        """Retourne à l'accueil."""
        if self.search_thread is None:
            self.show_home()
