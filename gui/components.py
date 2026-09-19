"""
Composants graphiques communs aux différentes vues.
"""

import tkinter as tk
from tkinter import ttk

from gui.styles import (
    BUTTON_HEIGHT,
    BUTTON_WIDTH,
    COLOR_BACKGROUND,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_SECONDARY,
    COLOR_WHITE,
    FONT_BUTTON,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_STATUS,
    FONT_SUBTITLE,
    FONT_TITLE,
    PROGRESS_WIDTH
)


def create_title(p_parent, p_text):
    """Crée le titre principal d'une vue."""

    title_label = tk.Label(
        p_parent,
        text=p_text,
        font=FONT_TITLE,
        fg=COLOR_TEXT,
        bg=COLOR_BACKGROUND
    )

    title_label.pack(
        pady=(20, 5)
    )

    return title_label


def create_subtitle(p_parent, p_text):
    """Crée le sous-titre d'une vue."""

    subtitle_label = tk.Label(
        p_parent,
        text=p_text,
        font=FONT_SUBTITLE,
        fg=COLOR_TEXT_SECONDARY,
        bg=COLOR_BACKGROUND
    )

    subtitle_label.pack(
        pady=(0, 20)
    )

    return subtitle_label


def create_section(p_parent, p_title):
    """Crée une section visuelle destinée à contenir plusieurs composants."""

    section_frame = tk.LabelFrame(
        p_parent,
        text=p_title,
        font=FONT_SECTION,
        fg=COLOR_TEXT,
        bg=COLOR_SURFACE,
        bd=1,
        relief="solid",
        padx=25,
        pady=15
    )

    section_frame.pack(
        fill="x",
        padx=100,
        pady=10
    )

    return section_frame


def create_progress_bar(p_parent):
    """Crée une barre de progression."""

    progress_bar = ttk.Progressbar(
        p_parent,
        orient="horizontal",
        mode="determinate",
        length=PROGRESS_WIDTH
    )

    progress_bar.pack(
        pady=10
    )

    return progress_bar


def create_data_count(p_parent):
    """Crée l'indicateur du nombre de données trouvées."""

    data_count_label = tk.Label(
        p_parent,
        text="Données trouvées : 0",
        font=FONT_STATUS,
        fg=COLOR_TEXT,
        bg=COLOR_SURFACE
    )

    data_count_label.pack(
        pady=5
    )

    return data_count_label


def create_result_label(p_parent):
    """Crée une zone destinée à afficher un résultat."""

    result_label = tk.Label(
        p_parent,
        text="",
        font=FONT_STATUS,
        fg=COLOR_TEXT,
        bg=COLOR_SURFACE
    )

    result_label.pack(
        pady=5
    )

    return result_label


def create_status_label(p_parent):
    """Crée l'indicateur d'état du traitement."""

    status_label = tk.Label(
        p_parent,
        text="● Prêt",
        font=FONT_STATUS,
        fg=COLOR_TEXT_SECONDARY,
        bg=COLOR_SURFACE
    )

    status_label.pack(
        pady=5
    )

    return status_label


def create_download_button(p_parent, p_text, p_command):
    """Crée un bouton permettant d'accéder à un fichier."""

    download_button = tk.Button(
        p_parent,
        text=p_text,
        command=p_command,
        width=BUTTON_WIDTH,
        height=BUTTON_HEIGHT,
        font=FONT_BUTTON,
        bg=COLOR_PRIMARY,
        fg=COLOR_WHITE,
        relief="flat",
        cursor="hand2"
    )

    download_button.pack(
        side="left",
        padx=5,
        pady=10
    )

    return download_button


def create_back_button(p_parent, p_command):
    """Crée un bouton permettant de revenir à l'accueil."""

    back_button = tk.Button(
        p_parent,
        text="← Retour",
        command=p_command,
        width=BUTTON_WIDTH,
        height=BUTTON_HEIGHT,
        font=FONT_BUTTON,
        bg=COLOR_SURFACE,
        fg=COLOR_TEXT,
        relief="solid",
        cursor="hand2"
    )

    back_button.pack(
        pady=15
    )

    return back_button