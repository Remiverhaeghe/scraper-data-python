"""Composants graphiques réutilisables"""

import tkinter as tk
from tkinter import ttk

from gui.styles import (
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_LIGHT,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_WHITE,
    FONT_BUTTON,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_SMALL,
    FONT_STAT,
    FONT_STAT_LABEL,
    FONT_STATUS,
    SPACING_SMALL,
    SPACING_MEDIUM,
    SPACING_LARGE,
    CARD_PADDING,
)

# Carte


class Card(tk.Frame):
    """Conteneur graphique réutilisable."""

    def __init__(
        self,
        p_parent,
        p_title=None,
        p_width=None,
        p_height=None,
    ):
        super().__init__(
            p_parent,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            bd=0,
        )

        if p_width is not None:
            self.configure(
                width=p_width,
            )

        if p_height is not None:
            self.configure(
                height=p_height,
            )

        if p_title is not None:
            v_title = tk.Label(
                self,
                text=p_title,
                bg=COLOR_SURFACE,
                fg=COLOR_TEXT,
                font=FONT_SECTION,
                anchor="w",
            )

            v_title.pack(
                fill="x",
                padx=CARD_PADDING,
                pady=(
                    CARD_PADDING,
                    SPACING_MEDIUM,
                ),
            )


# Titre de section


class SectionTitle(tk.Frame):
    """Affiche un titre et éventuellement un sous-titre."""

    def __init__(
        self,
        p_parent,
        p_title,
        p_subtitle=None,
    ):
        super().__init__(
            p_parent,
            bg=COLOR_BACKGROUND,
        )

        v_title = tk.Label(
            self,
            text=p_title,
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT,
            font=FONT_SECTION,
            anchor="w",
        )

        v_title.pack(
            fill="x",
        )

        if p_subtitle is not None:
            v_subtitle = tk.Label(
                self,
                text=p_subtitle,
                bg=COLOR_BACKGROUND,
                fg=COLOR_TEXT_SECONDARY,
                font=FONT_SMALL,
                anchor="w",
            )

            v_subtitle.pack(
                fill="x",
                pady=(
                    SPACING_SMALL,
                    0,
                ),
            )


# Bouton principal


class PrimaryButton(tk.Button):
    """Bouton principal."""

    def __init__(
        self,
        p_parent,
        p_text,
        p_command,
        p_width=None,
    ):
        v_width = p_width

        if v_width is None:
            v_width = 20

        super().__init__(
            p_parent,
            text=p_text,
            command=p_command,
            width=v_width,
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground=COLOR_WHITE,
            font=FONT_BUTTON,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=8,
        )


# Bouton secondaire


class SecondaryButton(tk.Button):
    """Bouton secondaire."""

    def __init__(
        self,
        p_parent,
        p_text,
        p_command,
        p_width=None,
    ):
        v_width = p_width

        if v_width is None:
            v_width = 18

        super().__init__(
            p_parent,
            text=p_text,
            command=p_command,
            width=v_width,
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_TEXT,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_PRIMARY,
            font=FONT_BUTTON,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=7,
        )


# Carte statistique


class StatisticCard(tk.Frame):
    """Affiche une statistique."""

    def __init__(
        self,
        p_parent,
        p_value,
        p_label,
        p_color=COLOR_PRIMARY,
        p_background=COLOR_PRIMARY_LIGHT,
    ):
        super().__init__(
            p_parent,
            bg=p_background,
            highlightthickness=0,
            bd=0,
        )

        v_value = tk.Label(
            self,
            text=p_value,
            bg=p_background,
            fg=p_color,
            font=FONT_STAT,
        )

        v_value.pack(
            pady=(
                14,
                2,
            ),
        )

        v_label = tk.Label(
            self,
            text=p_label,
            bg=p_background,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_STAT_LABEL,
        )

        v_label.pack(
            pady=(
                0,
                14,
            ),
        )

        self.value_label = v_value


# Indicateur d'état


class StatusIndicator(tk.Frame):
    """Affiche l'état d'une opération."""

    def __init__(
        self,
        p_parent,
        p_text="Prêt",
        p_status="ready",
    ):
        super().__init__(
            p_parent,
            bg=COLOR_SURFACE,
        )

        self.status_label = tk.Label(
            self,
            text="● " + p_text,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_MUTED,
            font=FONT_STATUS,
        )

        self.status_label.pack(
            anchor="w",
        )

        self.set_status(
            p_status,
            p_text,
        )

    def set_status(
        self,
        p_status,
        p_text,
    ):
        v_color = COLOR_TEXT_MUTED

        if p_status == "running":
            v_color = COLOR_PRIMARY

        elif p_status == "success":
            v_color = COLOR_SUCCESS

        elif p_status == "warning":
            v_color = COLOR_WARNING

        elif p_status == "error":
            v_color = COLOR_ERROR

        self.status_label.configure(
            text="● " + p_text,
            fg=v_color,
        )


# Barre de progression


class ProgressBar(tk.Frame):
    """Barre de progression réutilisable."""

    def __init__(
        self,
        p_parent,
    ):
        super().__init__(
            p_parent,
            bg=COLOR_SURFACE,
        )

        self.progress = ttk.Progressbar(
            self,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )

        self.progress.pack(
            fill="x",
            expand=True,
        )

        self.percent_label = tk.Label(
            self,
            text="0 %",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_SMALL,
        )

        self.percent_label.pack(
            anchor="e",
            pady=(
                SPACING_SMALL,
                0,
            ),
        )

    def set_value(
        self,
        p_value,
    ):
        v_value = max(
            0,
            min(
                100,
                p_value,
            ),
        )

        self.progress["value"] = v_value

        self.percent_label.configure(
            text=f"{int(v_value)} %",
        )


# Affichage des logs


class LogViewer(tk.Frame):
    """Affiche les logs de l'application."""

    def __init__(
        self,
        p_parent,
        p_height=8,
    ):
        super().__init__(
            p_parent,
            bg=COLOR_SURFACE,
        )

        self.text = tk.Text(
            self,
            height=p_height,
            bg="#F8FAFD",
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            wrap="word",
            state="disabled",
        )

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.text.yview,
        )

        self.text.configure(
            yscrollcommand=self.scrollbar.set,
        )

        self.scrollbar.pack(
            side="right",
            fill="y",
        )

        self.text.pack(
            side="left",
            fill="both",
            expand=True,
        )

    def add_log(
        self,
        p_message,
    ):
        self.text.configure(
            state="normal",
        )

        self.text.insert(
            "end",
            p_message + "\n",
        )

        self.text.see(
            "end",
        )

        self.text.configure(
            state="disabled",
        )

    def clear(self):
        self.text.configure(
            state="normal",
        )

        self.text.delete(
            "1.0",
            "end",
        )

        self.text.configure(
            state="disabled",
        )


# Compatibilité avec les anciennes vues


def create_title(
    p_parent,
    p_text,
):
    """Crée un titre de page."""

    v_title = tk.Label(
        p_parent,
        text=p_text,
        bg=COLOR_BACKGROUND,
        fg=COLOR_TEXT,
        font=("Segoe UI", 24, "bold"),
        anchor="w",
    )

    v_title.pack(
        fill="x",
        pady=(0, 5),
    )

    return v_title


def create_subtitle(
    p_parent,
    p_text,
):
    """Crée un sous-titre de page."""

    v_subtitle = tk.Label(
        p_parent,
        text=p_text,
        bg=COLOR_BACKGROUND,
        fg=COLOR_TEXT_SECONDARY,
        font=("Segoe UI", 11),
        anchor="w",
    )

    v_subtitle.pack(
        fill="x",
        pady=(0, 20),
    )

    return v_subtitle


def create_section(
    p_parent,
    p_title,
):
    """Crée une section compatible avec les anciennes vues."""

    v_section = tk.Frame(
        p_parent,
        bg=COLOR_SURFACE,
        highlightbackground=COLOR_BORDER,
        highlightthickness=1,
        bd=0,
    )

    v_section.pack(
        fill="x",
        pady=8,
    )

    v_title = tk.Label(
        v_section,
        text=p_title,
        bg=COLOR_SURFACE,
        fg=COLOR_TEXT,
        font=FONT_SECTION,
        anchor="w",
    )

    v_title.pack(
        fill="x",
        padx=15,
        pady=(15, 5),
    )

    return v_section


def create_progress_bar(
    p_parent,
    p_variable=None,
):
    """Crée une barre de progression compatible avec les anciennes vues."""

    v_progress = ttk.Progressbar(
        p_parent,
        orient="horizontal",
        mode="determinate",
        maximum=100,
    )

    if p_variable is not None:
        v_progress.configure(
            variable=p_variable,
        )

    v_progress.pack(
        fill="x",
        pady=10,
    )

    return v_progress


def create_status_label(
    p_parent,
    p_variable,
):
    """Crée un affichage d'état."""

    v_label = tk.Label(
        p_parent,
        textvariable=p_variable,
        bg=COLOR_SURFACE,
        fg=COLOR_TEXT_SECONDARY,
        font=FONT_STATUS,
        anchor="w",
    )

    v_label.pack(
        fill="x",
        pady=5,
    )

    return v_label


def create_data_count(
    p_parent,
    p_variable,
):
    """Affiche le nombre de données récupérées."""

    v_label = tk.Label(
        p_parent,
        textvariable=p_variable,
        bg=COLOR_SURFACE,
        fg=COLOR_PRIMARY,
        font=FONT_STAT,
        anchor="w",
    )

    v_label.pack(
        fill="x",
        pady=10,
    )

    return v_label


def create_back_button(
    p_parent,
    p_command,
):
    """Crée un bouton de retour."""

    v_button = SecondaryButton(
        p_parent,
        "Retour à l'accueil",
        p_command,
    )

    v_button.pack(
        side="left",
    )

    return v_button
