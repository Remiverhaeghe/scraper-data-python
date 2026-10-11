"""Couleurs, thèmes clair et sombre et feuille de style de l'interface"""

from pathlib import Path
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from gui.icons import stylesheet_path

THEME_FILE = Path(__file__).with_name("theme.qss")

THEME_CHOICES = {"light": "Clair", "dark": "Sombre"}

THEMES = {
    "light": {
        "background": "#F4F7FB",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFD",
        "border": "#DDE6F1",
        "heading": "#0F172A",
        "text": "#1E293B",
        "muted": "#52658A",
        "on_primary": "#FFFFFF",
        "primary": "#1769E0",
        "primary_dark": "#0F56BE",
        "primary_light": "#E8F1FF",
        "primary_gradient": "#4F8DF5",
        "banner_text": "#DCE9FF",
        "success": "#16A34A",
        "success_light": "#E7F7EC",
        "warning": "#D97706",
        "warning_light": "#FEF3E2",
        "danger": "#DC2626",
    },
    "dark": {
        "background": "#0F141C",
        "surface": "#171E29",
        "surface_alt": "#1B2330",
        "border": "#273244",
        "heading": "#F1F5F9",
        "text": "#D9E1EC",
        "muted": "#8FA0BA",
        "on_primary": "#FFFFFF",
        "primary": "#3B82F6",
        "primary_dark": "#2563EB",
        "primary_light": "#1C2C47",
        "primary_gradient": "#1D4ED8",
        "banner_text": "#C9DBFF",
        "success": "#22C55E",
        "success_light": "#132A1F",
        "warning": "#F59E0B",
        "warning_light": "#2E2310",
        "danger": "#EF4444",
    },
}

# Couleur principale et fond des cartes statistiques, par thème
THEME_ACCENTS = {
    "light": {
        "blue": ("#1769E0", "#E8F1FF"),
        "green": ("#16A34A", "#E7F7EC"),
        "amber": ("#D97706", "#FFF4E0"),
        "purple": ("#7C3AED", "#F1EAFE"),
    },
    "dark": {
        "blue": ("#60A5FA", "#16243B"),
        "green": ("#4ADE80", "#132A1F"),
        "amber": ("#FBBF24", "#2E2412"),
        "purple": ("#C084FC", "#251A3A"),
    },
}

# Couleurs du thème actif, mises à jour sur place par apply_theme pour que
# les modules qui les ont importées voient toujours les bonnes valeurs.
COLORS = dict(THEMES["light"])
ACCENTS = dict(THEME_ACCENTS["light"])


def is_dark_theme():
    """Indique si le thème actif est le thème sombre."""

    rIsDark = COLORS == THEMES["dark"]

    return rIsDark


def resolve_theme(pChoice):
    """Traduit un choix de thème en thème réel ; system suit Windows."""

    rTheme = pChoice

    if pChoice not in THEMES:
        vScheme = QGuiApplication.styleHints().colorScheme()
        rTheme = "dark" if vScheme == Qt.ColorScheme.Dark else "light"

    return rTheme


def build_stylesheet():
    """Retourne la feuille de style, ses variables remplacées par les couleurs."""

    # Dépannage : une variable $nom de theme.qss absente de COLORS lève KeyError
    # au démarrage ; une propriété CSS inconnue de Qt est ignorée sans erreur.
    rStylesheet = Template(THEME_FILE.read_text(encoding="utf-8")).substitute(
        COLORS,
        chevron_up=stylesheet_path("chevron-up"),
        chevron_down=stylesheet_path("chevron-down"),
    )

    return rStylesheet


def build_palette():
    """Retourne la palette Qt correspondant aux couleurs du thème actif."""

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
        (QPalette.ColorRole.HighlightedText, COLORS["on_primary"]),
        (QPalette.ColorRole.Link, COLORS["primary"]),
        (QPalette.ColorRole.Mid, COLORS["border"]),
        (QPalette.ColorRole.ToolTipBase, COLORS["heading"]),
        (QPalette.ColorRole.ToolTipText, COLORS["surface"]),
    ):
        rPalette.setColor(vRole, QColor(vColor))

    return rPalette


def apply_theme(pApplication, pChoice):
    """Applique un thème à l'application et retourne le thème réellement utilisé."""

    rTheme = resolve_theme(pChoice)

    COLORS.clear()
    COLORS.update(THEMES[rTheme])
    ACCENTS.clear()
    ACCENTS.update(THEME_ACCENTS[rTheme])

    pApplication.setPalette(build_palette())
    pApplication.setStyleSheet(build_stylesheet())

    return rTheme
