"""Couleurs et feuille de style de l'interface"""

from pathlib import Path
from string import Template

from PySide6.QtGui import QColor, QPalette

from gui.icons import stylesheet_path

THEME_FILE = Path(__file__).with_name("theme.qss")

COLORS = {
    "background": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFD",
    "border": "#DDE6F1",
    "heading": "#0F172A",
    "text": "#1E293B",
    "muted": "#52658A",
    "primary": "#1769E0",
    "primary_dark": "#0F56BE",
    "primary_light": "#E8F1FF",
    "primary_gradient": "#4F8DF5",
    "banner_text": "#DCE9FF",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
}

# Couleur principale et fond clair des cartes statistiques
ACCENTS = {
    "blue": ("#1769E0", "#E8F1FF"),
    "green": ("#16A34A", "#E7F7EC"),
    "amber": ("#D97706", "#FFF4E0"),
    "purple": ("#7C3AED", "#F1EAFE"),
}


def build_stylesheet():
    """Retourne la feuille de style, ses variables remplacées par les couleurs."""

    rStylesheet = Template(THEME_FILE.read_text(encoding="utf-8")).substitute(
        COLORS,
        chevron_up=stylesheet_path("chevron-up"),
        chevron_down=stylesheet_path("chevron-down"),
    )

    return rStylesheet


def build_palette():
    """Retourne une palette claire, indépendante du thème de Windows."""

    rPalette = QPalette()

    for vRole, vColor in (
        (QPalette.ColorRole.Window, COLORS["background"]),
        (QPalette.ColorRole.Base, COLORS["surface"]),
        (QPalette.ColorRole.AlternateBase, COLORS["surface_alt"]),
        (QPalette.ColorRole.Button, COLORS["surface"]),
        (QPalette.ColorRole.Text, COLORS["text"]),
        (QPalette.ColorRole.WindowText, COLORS["text"]),
        (QPalette.ColorRole.ButtonText, COLORS["text"]),
        (QPalette.ColorRole.PlaceholderText, COLORS["muted"]),
        (QPalette.ColorRole.Highlight, COLORS["primary"]),
        (QPalette.ColorRole.HighlightedText, COLORS["surface"]),
        (QPalette.ColorRole.Link, COLORS["primary"]),
        (QPalette.ColorRole.Mid, COLORS["border"]),
    ):
        rPalette.setColor(vRole, QColor(vColor))

    return rPalette
