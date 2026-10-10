"""Fenêtre principale de l'application"""

import tkinter as tk

from gui.home_view import HomeView
from gui.styles import (
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WHITE,
    FONT_BUTTON,
    FONT_NORMAL,
    FONT_SMALL,
    FONT_TITLE,
    SIDEBAR_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)

# Fenêtre principale


class ApplicationWindow(tk.Tk):
    """Fenêtre principale de RV - Web Scraper."""

    def __init__(self):
        super().__init__()

        self.a_current_view = None
        self.a_content_frame = None
        self.a_navigation_buttons = {}

        self._configure_window()
        self._build_layout()
        self._show_home()

    # ========================================================================
    # Configuration
    # ========================================================================

    def _configure_window(self):
        """Configure les propriétés générales de la fenêtre."""

        self.title(
            "RV - Web Scraper",
        )

        self.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}",
        )

        self.minsize(
            WINDOW_MIN_WIDTH,
            WINDOW_MIN_HEIGHT,
        )

        self.configure(
            bg=COLOR_BACKGROUND,
        )

    # ========================================================================
    # Construction de la fenêtre
    # ========================================================================

    def _build_layout(self):
        """Construit la structure générale de la fenêtre."""

        v_main_frame = tk.Frame(
            self,
            bg=COLOR_BACKGROUND,
        )

        v_main_frame.pack(
            fill="both",
            expand=True,
        )

        self._build_sidebar(
            v_main_frame,
        )

        self._build_content_area(
            v_main_frame,
        )

    def _build_sidebar(self, p_parent):
        """Construit la barre de navigation latérale."""

        v_sidebar = tk.Frame(
            p_parent,
            width=SIDEBAR_WIDTH,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )

        v_sidebar.pack(
            side="left",
            fill="y",
        )

        v_sidebar.pack_propagate(
            False,
        )

        self._build_sidebar_header(
            v_sidebar,
        )

        self._build_navigation(
            v_sidebar,
        )

        self._build_sidebar_footer(
            v_sidebar,
        )

    def _build_sidebar_header(self, p_parent):
        """Construit l'en-tête de la barre latérale."""

        v_header = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
        )

        v_header.pack(
            fill="x",
            padx=18,
            pady=20,
        )

        v_logo = tk.Label(
            v_header,
            text="RV",
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            font=("Segoe UI", 18, "bold"),
            width=3,
            height=1,
        )

        v_logo.pack(
            side="left",
        )

        v_title_frame = tk.Frame(
            v_header,
            bg=COLOR_SURFACE,
        )

        v_title_frame.pack(
            side="left",
            padx=10,
        )

        v_title = tk.Label(
            v_title_frame,
            text="RV - Web Scraper",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_BUTTON,
            anchor="w",
        )

        v_title.pack(
            fill="x",
        )

        v_subtitle = tk.Label(
            v_title_frame,
            text="Des données utiles,\nsimplement",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            justify="left",
            anchor="w",
        )

        v_subtitle.pack(
            fill="x",
            pady=(3, 0),
        )

    def _build_navigation(self, p_parent):
        """Construit les boutons de navigation."""

        v_navigation_frame = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
        )

        v_navigation_frame.pack(
            fill="x",
            padx=12,
            pady=(10, 0),
        )

        self._add_navigation_button(
            v_navigation_frame,
            "⌂",
            "Accueil",
            self._show_home,
            "home",
        )

        self._add_navigation_button(
            v_navigation_frame,
            "▣",
            "Offres d'emploi",
            self._show_jobs,
            "jobs",
        )

        self._add_navigation_button(
            v_navigation_frame,
            "▤",
            "Livres",
            self._show_books,
            "books",
        )

        v_separator = tk.Frame(
            p_parent,
            bg=COLOR_BORDER,
            height=1,
        )

        v_separator.pack(
            fill="x",
            padx=18,
            pady=20,
        )

        self._add_navigation_button(
            p_parent,
            "⚙",
            "Paramètres",
            self._show_settings,
            "settings",
        )

    def _add_navigation_button(
        self,
        p_parent,
        p_icon,
        p_text,
        p_command,
        p_key,
    ):
        """Ajoute un bouton à la navigation."""

        v_button = tk.Button(
            p_parent,
            text=f"{p_icon}   {p_text}",
            command=p_command,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            activebackground=COLOR_PRIMARY_LIGHT,
            activeforeground=COLOR_PRIMARY,
            font=FONT_BUTTON,
            relief="flat",
            bd=0,
            anchor="w",
            padx=14,
            pady=12,
            cursor="hand2",
        )

        v_button.pack(
            fill="x",
            pady=2,
        )

        self.a_navigation_buttons[p_key] = v_button

    def _build_content_area(self, p_parent):
        """Construit la zone principale destinée aux différentes vues."""

        self.a_content_frame = tk.Frame(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        self.a_content_frame.pack(
            side="left",
            fill="both",
            expand=True,
        )

    def _build_sidebar_footer(self, p_parent):
        """Construit le pied de la barre latérale."""

        v_footer = tk.Frame(
            p_parent,
            bg=COLOR_SURFACE,
        )

        v_footer.pack(
            side="bottom",
            fill="x",
            padx=18,
            pady=18,
        )

        v_version = tk.Label(
            v_footer,
            text="v1.0.0",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        )

        v_version.pack(
            fill="x",
        )

        v_status_frame = tk.Frame(
            v_footer,
            bg=COLOR_SURFACE,
        )

        v_status_frame.pack(
            fill="x",
            pady=(8, 0),
        )

        v_status = tk.Label(
            v_status_frame,
            text="●",
            bg=COLOR_SURFACE,
            fg=COLOR_SUCCESS,
            font=("Segoe UI", 10, "bold"),
        )

        v_status.pack(
            side="left",
        )

        v_status_text = tk.Label(
            v_status_frame,
            text="Prêt",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=FONT_NORMAL,
        )

        v_status_text.pack(
            side="left",
            padx=(6, 0),
        )

    # ========================================================================
    # Gestion des vues
    # ========================================================================

    def _show_view(self, p_view):
        """Affiche une nouvelle vue dans la zone de contenu."""

        if self.a_current_view is not None:
            self.a_current_view.destroy()

        self.a_current_view = p_view

        self.a_current_view.pack(
            fill="both",
            expand=True,
        )

    def _clear_content(self):
        """Supprime le contenu actuellement affiché."""

        for v_widget in self.a_content_frame.winfo_children():
            v_widget.destroy()

        self.a_current_view = None

    # ========================================================================
    # Navigation
    # ========================================================================

    def _show_home(self):
        """Affiche la vue d'accueil."""

        v_view = HomeView(
            self.a_content_frame,
            self,
        )

        self._show_view(
            v_view,
        )

        self._set_active_navigation(
            "home",
        )

    def _show_jobs(self):
        """Affiche la vue des offres d'emploi."""

        from gui.jobs_view import JobsView

        self._clear_content()

        JobsView(
            self.a_content_frame,
            self._show_home,
        )

        self._set_active_navigation(
            "jobs",
        )

    def _show_books(self):
        """Affiche la vue des livres."""

        from gui.books_view import BooksView

        self._clear_content()

        BooksView(
            self.a_content_frame,
            self._show_home,
        )

        self._set_active_navigation(
            "books",
        )

    def _show_settings(self):
        """Affiche temporairement la vue des paramètres."""

        self._clear_content()

        v_view = tk.Frame(
            self.a_content_frame,
            bg=COLOR_BACKGROUND,
        )

        v_view.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=30,
        )

        v_title = tk.Label(
            v_view,
            text="Paramètres",
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT,
            font=FONT_TITLE,
            anchor="w",
        )

        v_title.pack(
            fill="x",
        )

        v_subtitle = tk.Label(
            v_view,
            text="La configuration de l'application sera disponible ici",
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_NORMAL,
            anchor="w",
        )

        v_subtitle.pack(
            fill="x",
            pady=(8, 0),
        )

        self.a_current_view = v_view

        self._set_active_navigation(
            "settings",
        )

    def _set_active_navigation(self, p_key):
        """Met en évidence le bouton de navigation actif."""

        for v_key, v_button in self.a_navigation_buttons.items():

            if v_key == p_key:
                v_button.configure(
                    bg=COLOR_PRIMARY,
                    fg=COLOR_WHITE,
                    activebackground=COLOR_PRIMARY,
                    activeforeground=COLOR_WHITE,
                )

            else:
                v_button.configure(
                    bg=COLOR_SURFACE,
                    fg=COLOR_TEXT,
                    activebackground=COLOR_PRIMARY_LIGHT,
                    activeforeground=COLOR_PRIMARY,
                )

    # ========================================================================
    # Méthodes publiques
    # ========================================================================

    def show_home(self):
        """Permet de revenir à l'accueil."""

        self._show_home()
