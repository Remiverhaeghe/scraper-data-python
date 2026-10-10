"""Vue d'accueil de l'application"""

import tkinter as tk

from gui.components import (
    Card,
    PrimaryButton,
    SecondaryButton,
    StatisticCard,
)

from gui.styles import (
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_BOOKS,
    COLOR_BOOKS_LIGHT,
    COLOR_JOBS,
    COLOR_JOBS_LIGHT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SETTINGS,
    COLOR_SETTINGS_LIGHT,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_WHITE,
    COLOR_SUCCESS,
    FONT_BUTTON,
    FONT_PAGE_TITLE,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    SPACING_SMALL,
    SPACING_MEDIUM,
    SPACING_LARGE,
    SPACING_XLARGE,
)
from job.sources.registry import SOURCES

# Vue principale


class HomeView(tk.Frame):
    """Dashboard principal de l'application."""

    def __init__(
        self,
        p_parent,
        p_controller=None,
    ):
        super().__init__(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        self.a_controller = p_controller

        # Références vers les cartes statistiques
        self.a_searches_stat = None
        self.a_jobs_stat = None
        self.a_books_stat = None
        self.a_duration_stat = None

        self._build_view()

    # ========================================================================
    # Construction générale
    # ========================================================================

    def _build_view(self):
        """Construit le dashboard."""

        v_container = tk.Frame(
            self,
            bg=COLOR_BACKGROUND,
        )

        v_container.pack(
            fill="both",
            expand=True,
            padx=24,
            pady=20,
        )

        self._build_top_bar(
            v_container,
        )

        self._build_welcome_banner(
            v_container,
        )

        self._build_main_cards(
            v_container,
        )

        self._build_statistics(
            v_container,
        )

        self._build_bottom_area(
            v_container,
        )

    # ========================================================================
    # En-tête
    # ========================================================================

    def _build_top_bar(
        self,
        p_parent,
    ):
        """Construit la barre supérieure."""

        v_frame = tk.Frame(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        v_frame.pack(
            fill="x",
            pady=(0, 15),
        )

        v_left = tk.Frame(
            v_frame,
            bg=COLOR_BACKGROUND,
        )

        v_left.pack(
            side="left",
        )

        v_title = tk.Label(
            v_left,
            text="RV - Web Scraper",
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT,
            font=FONT_TITLE,
            anchor="w",
        )

        v_title.pack(
            anchor="w",
        )

        v_subtitle = tk.Label(
            v_left,
            text="Des données utiles, simplement",
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SUBTITLE,
            anchor="w",
        )

        v_subtitle.pack(
            anchor="w",
            pady=(3, 0),
        )

        v_right = tk.Frame(
            v_frame,
            bg=COLOR_BACKGROUND,
        )

        v_right.pack(
            side="right",
            anchor="n",
        )

        v_github = SecondaryButton(
            v_right,
            "GitHub",
            self._on_github,
            10,
        )

        v_github.pack(
            side="left",
            padx=(0, 8),
        )

        v_settings = SecondaryButton(
            v_right,
            "⚙",
            self._on_settings,
            5,
        )

        v_settings.pack(
            side="left",
        )

    # ========================================================================
    # Bannière
    # ========================================================================

    def _build_welcome_banner(
        self,
        p_parent,
    ):
        """Construit la bannière de bienvenue."""

        v_banner = tk.Frame(
            p_parent,
            bg=COLOR_PRIMARY_LIGHT,
            highlightbackground="#D5E4FA",
            highlightthickness=1,
        )

        v_banner.pack(
            fill="x",
            pady=(0, SPACING_LARGE),
        )

        v_content = tk.Frame(
            v_banner,
            bg=COLOR_PRIMARY_LIGHT,
        )

        v_content.pack(
            side="left",
            padx=30,
            pady=25,
        )

        v_title = tk.Label(
            v_content,
            text="Bienvenue sur RV - Web Scraper",
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_TEXT,
            font=FONT_PAGE_TITLE,
            anchor="w",
        )

        v_title.pack(
            anchor="w",
        )

        v_text = tk.Label(
            v_content,
            text=(
                "Récupérez, analysez et exportez facilement des données\n"
                "à partir de différentes sources."
            ),
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_TEXT_SECONDARY,
            font=("Segoe UI", 13),
            justify="left",
            anchor="w",
        )

        v_text.pack(
            anchor="w",
            pady=(8, 0),
        )

        v_visual = tk.Frame(
            v_banner,
            bg=COLOR_PRIMARY_LIGHT,
        )

        v_visual.pack(
            side="right",
            padx=35,
            pady=20,
        )

        v_visual_label = tk.Label(
            v_visual,
            text="⌕\n▣  ◫  ⚙",
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_PRIMARY,
            font=("Segoe UI", 30, "bold"),
            justify="center",
        )

        v_visual_label.pack()

    # ========================================================================
    # Cartes principales
    # ========================================================================

    def _build_main_cards(
        self,
        p_parent,
    ):
        """Construit les cartes Offres et Livres."""

        v_container = tk.Frame(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        v_container.pack(
            fill="x",
            pady=(0, SPACING_LARGE),
        )

        v_container.columnconfigure(
            0,
            weight=1,
        )

        v_container.columnconfigure(
            1,
            weight=1,
        )

        self._build_jobs_card(
            v_container,
        )

        self._build_books_card(
            v_container,
        )

    def _build_jobs_card(
        self,
        p_parent,
    ):
        """Construit la carte des offres d'emploi."""

        v_card = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )

        v_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        v_icon = tk.Label(
            v_card,
            text="💼",
            bg=COLOR_JOBS_LIGHT,
            fg=COLOR_JOBS,
            font=("Segoe UI Emoji", 25),
            width=4,
            height=2,
        )

        v_icon.pack(
            side="left",
            padx=20,
            pady=20,
        )

        v_content = tk.Frame(
            v_card,
            bg=COLOR_SURFACE,
        )

        v_content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10),
            pady=18,
        )

        tk.Label(
            v_content,
            text="Offres d'emploi",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        ).pack(
            fill="x",
        )

        tk.Label(
            v_content,
            text=(
                "Recherchez et centralisez les offres correspondant\n"
                "à vos critères sur plusieurs sources."
            ),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            justify="left",
            anchor="w",
        ).pack(
            fill="x",
            pady=(5, 10),
        )

        tk.Label(
            v_content,
            text=" · ".join(vSource.label for vSource in SOURCES.values()),
            bg=COLOR_SURFACE,
            fg=COLOR_JOBS,
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            wraplength=320,
        ).pack(
            fill="x",
        )

        PrimaryButton(
            v_card,
            "→",
            self._on_jobs,
            5,
        ).pack(
            side="right",
            padx=18,
            pady=20,
        )

    def _build_books_card(
        self,
        p_parent,
    ):
        """Construit la carte des livres."""

        v_card = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )

        v_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0),
        )

        v_icon = tk.Label(
            v_card,
            text="📚",
            bg=COLOR_BOOKS_LIGHT,
            fg=COLOR_BOOKS,
            font=("Segoe UI Emoji", 25),
            width=4,
            height=2,
        )

        v_icon.pack(
            side="left",
            padx=20,
            pady=20,
        )

        v_content = tk.Frame(
            v_card,
            bg=COLOR_SURFACE,
        )

        v_content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10),
            pady=18,
        )

        tk.Label(
            v_content,
            text="Livres",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        ).pack(
            fill="x",
        )

        tk.Label(
            v_content,
            text=(
                "Récupérez, analysez et exportez les informations\n"
                "des livres depuis différentes sources."
            ),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            justify="left",
            anchor="w",
        ).pack(
            fill="x",
            pady=(5, 10),
        )

        tk.Label(
            v_content,
            text="Pages    Métadonnées    Export",
            bg=COLOR_SURFACE,
            fg=COLOR_BOOKS,
            font=FONT_SMALL,
            anchor="w",
        ).pack(
            fill="x",
        )

        PrimaryButton(
            v_card,
            "→",
            self._on_books,
            5,
        ).pack(
            side="right",
            padx=18,
            pady=20,
        )

    # ========================================================================
    # Statistiques
    # ========================================================================

    def _build_statistics(
        self,
        p_parent,
    ):
        """Construit la zone des statistiques."""

        v_card = Card(
            p_parent,
        )

        v_card.pack(
            fill="x",
            pady=(0, SPACING_LARGE),
        )

        v_title = tk.Label(
            v_card,
            text="Statistiques",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        )

        v_title.pack(
            anchor="w",
            padx=20,
            pady=(15, 10),
        )

        v_stats = tk.Frame(
            v_card,
            bg=COLOR_SURFACE,
        )

        v_stats.pack(
            fill="x",
            padx=20,
            pady=(0, 18),
        )

        v_stats.columnconfigure(
            0,
            weight=1,
        )

        v_stats.columnconfigure(
            1,
            weight=1,
        )

        v_stats.columnconfigure(
            2,
            weight=1,
        )

        v_stats.columnconfigure(
            3,
            weight=1,
        )

        self.a_searches_stat = StatisticCard(
            v_stats,
            "24",
            "Recherches effectuées",
            COLOR_JOBS,
            COLOR_JOBS_LIGHT,
        )

        self.a_searches_stat.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=4,
        )

        self.a_jobs_stat = StatisticCard(
            v_stats,
            "187",
            "Offres d'emploi trouvées",
            COLOR_SUCCESS,
            "#E8F8EF",
        )

        self.a_jobs_stat.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        self.a_books_stat = StatisticCard(
            v_stats,
            "12",
            "Livres récupérés",
            COLOR_BOOKS,
            COLOR_BOOKS_LIGHT,
        )

        self.a_books_stat.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=4,
        )

        self.a_duration_stat = StatisticCard(
            v_stats,
            "2 min 32 s",
            "Temps moyen de traitement",
            COLOR_SETTINGS,
            COLOR_SETTINGS_LIGHT,
        )

        self.a_duration_stat.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=4,
        )

        self._load_statistics()

    # ========================================================================
    # Zone inférieure
    # ========================================================================

    def _build_bottom_area(
        self,
        p_parent,
    ):
        """Construit activité récente et actions rapides."""

        v_container = tk.Frame(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        v_container.pack(
            fill="both",
            expand=True,
        )

        v_container.columnconfigure(
            0,
            weight=1,
        )

        v_container.columnconfigure(
            1,
            weight=1,
        )

        self._build_recent_activity(
            v_container,
        )

        self._build_quick_actions(
            v_container,
        )

    def _build_recent_activity(
        self,
        p_parent,
    ):
        """Construit la liste des dernières activités."""

        v_card = Card(
            p_parent,
        )

        v_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        tk.Label(
            v_card,
            text="Activité récente",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(18, 2),
        )

        tk.Label(
            v_card,
            text="Vos dernières actions sur l'application",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        self._add_activity(
            v_card,
            "💼",
            "Recherche d'offres d'emploi",
            "Mot-clé : Développeur Java • Lille",
            "20 offres",
        )

        self._add_activity(
            v_card,
            "📚",
            "Scraping de livres",
            "Source : Open Library • 1 page",
            "12 livres",
        )

        self._add_activity(
            v_card,
            "💼",
            "Recherche d'offres d'emploi",
            "Mot-clé : Data Analyst • Paris",
            "18 offres",
        )

        self._add_activity(
            v_card,
            "📚",
            "Scraping de livres",
            "Source : Google Books • 2 pages",
            "25 livres",
        )

    def _add_activity(
        self,
        p_parent,
        p_icon,
        p_title,
        p_description,
        p_result,
    ):
        """Ajoute une activité récente."""

        v_frame = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
        )

        v_frame.pack(
            fill="x",
            padx=20,
            pady=4,
        )

        tk.Label(
            v_frame,
            text=p_icon,
            bg=COLOR_SURFACE,
            font=("Segoe UI Emoji", 14),
        ).pack(
            side="left",
            padx=(0, 10),
        )

        v_content = tk.Frame(
            v_frame,
            bg=COLOR_SURFACE,
        )

        v_content.pack(
            side="left",
            fill="x",
            expand=True,
        )

        tk.Label(
            v_content,
            text=p_title,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_BUTTON,
            anchor="w",
        ).pack(
            fill="x",
        )

        tk.Label(
            v_content,
            text=p_description,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        ).pack(
            fill="x",
        )

        tk.Label(
            v_frame,
            text=p_result,
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_PRIMARY,
            font=FONT_SMALL,
            padx=8,
            pady=4,
        ).pack(
            side="right",
        )

    def _build_quick_actions(
        self,
        p_parent,
    ):
        """Construit les actions rapides."""

        v_card = Card(
            p_parent,
        )

        v_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0),
        )

        tk.Label(
            v_card,
            text="Actions rapides",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(18, 2),
        )

        tk.Label(
            v_card,
            text="Accédez rapidement aux fonctionnalités principales",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 15),
        )

        v_actions = tk.Frame(
            v_card,
            bg=COLOR_SURFACE,
        )

        v_actions.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20),
        )

        v_actions.columnconfigure(
            0,
            weight=1,
        )

        v_actions.columnconfigure(
            1,
            weight=1,
        )

        self._add_action(
            v_actions,
            0,
            0,
            "💼  Rechercher des offres",
            "Lancer une nouvelle recherche",
            self._on_jobs,
            COLOR_JOBS_LIGHT,
        )

        self._add_action(
            v_actions,
            0,
            1,
            "📚  Scraper des livres",
            "Récupérer des informations",
            self._on_books,
            COLOR_BOOKS_LIGHT,
        )

        self._add_action(
            v_actions,
            1,
            0,
            "⚙  Paramètres",
            "Configurer l'application",
            self._on_settings,
            COLOR_SETTINGS_LIGHT,
        )

        self._add_action(
            v_actions,
            1,
            1,
            "▣  Voir l'historique",
            "Consulter vos recherches",
            self._on_history,
            COLOR_PRIMARY_LIGHT,
        )

    def _add_action(
        self,
        p_parent,
        p_row,
        p_column,
        p_title,
        p_description,
        p_command,
        p_background,
    ):
        """Ajoute une action rapide."""

        v_button = tk.Button(
            p_parent,
            text=f"{p_title}\n{p_description}",
            command=p_command,
            bg=p_background,
            fg=COLOR_TEXT,
            activebackground=p_background,
            activeforeground=COLOR_TEXT,
            font=FONT_BUTTON,
            justify="left",
            anchor="w",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=15,
            pady=12,
        )

        v_button.grid(
            row=p_row,
            column=p_column,
            sticky="nsew",
            padx=4,
            pady=4,
        )

    # ========================================================================
    # Actions
    # ========================================================================

    def _on_jobs(self):
        """Ouvre la vue des offres d'emploi."""

        if self.a_controller is not None:
            self.a_controller._show_jobs()

    def _on_books(self):
        """Ouvre la vue des livres."""

        if self.a_controller is not None:
            self.a_controller._show_books()

    def _on_settings(self):
        """Ouvre les paramètres."""

        if self.a_controller is not None:
            self.a_controller._show_settings()

    def _on_history(self):
        """Affiche temporairement l'historique."""

        if self.a_controller is not None:
            self.a_controller._show_settings()

    def _on_github(self):
        """Action temporaire pour le bouton GitHub."""

        pass

    # =========================================================================
    # Chargement des statistiques
    # =========================================================================

    def _load_statistics(self):
        """Charge les statistiques réelles de l'application."""

        v_statistics = {
            "searches": 0,
            "jobs": 0,
            "books": 0,
            "duration": "0 s",
        }

        self._update_statistics(
            v_statistics,
        )

    def _update_statistics(
        self,
        p_statistics,
    ):
        """Met à jour les cartes statistiques de l'accueil."""

        self.a_searches_stat.value_label.configure(
            text=str(
                p_statistics["searches"],
            ),
        )

        self.a_jobs_stat.value_label.configure(
            text=str(
                p_statistics["jobs"],
            ),
        )

        self.a_books_stat.value_label.configure(
            text=str(
                p_statistics["books"],
            ),
        )

        self.a_duration_stat.value_label.configure(
            text=p_statistics["duration"],
        )
