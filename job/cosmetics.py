"""Récompenses cosmétiques : couleurs d'accent et cadres d'avatar débloqués par niveau

Chaque niveau atteint débloque de quoi personnaliser l'interface ; le choix est
gardé en base, partagé par le bureau, le web et le téléphone. Un son court de
réussite accompagne les montées de niveau, et se coupe d'un réglage.
"""

from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

COSMETICS_KEY = "cosmetics"
DEFAULT_ACCENT = "bleu"
DEFAULT_FRAME = "aucun"

# Couleur d'accent : (nom, niveau requis, teintes du thème clair puis sombre)
ACCENTS = {
    "bleu": ("Bleu atelier", 1, {}, {}),
    "vert": (
        "Vert sécurité",
        2,
        {
            "primary": "#15803D",
            "primary_dark": "#166534",
            "primary_light": "#E7F7EC",
            "primary_gradient": "#22C55E",
            "banner_text": "#DCFCE7",
            "banner_start": "#15803D",
            "banner_end": "#166534",
        },
        {
            "primary": "#4ADE80",
            "primary_dark": "#86EFAC",
            "primary_light": "#132A1F",
            "primary_gradient": "#15803D",
            "banner_text": "#DCFCE7",
            "banner_start": "#15803D",
            "banner_end": "#14532D",
        },
    ),
    "violet": (
        "Violet automate",
        4,
        {
            "primary": "#7C3AED",
            "primary_dark": "#6D28D9",
            "primary_light": "#F1EAFE",
            "primary_gradient": "#A78BFA",
            "banner_text": "#EDE9FE",
            "banner_start": "#7C3AED",
            "banner_end": "#5B21B6",
        },
        {
            "primary": "#C084FC",
            "primary_dark": "#D8B4FE",
            "primary_light": "#251A3A",
            "primary_gradient": "#7C3AED",
            "banner_text": "#EDE9FE",
            "banner_start": "#6D28D9",
            "banner_end": "#4C1D95",
        },
    ),
    "orange": (
        "Orange signalisation",
        6,
        {
            "primary": "#C2410C",
            "primary_dark": "#9A3412",
            "primary_light": "#FFF1E6",
            "primary_gradient": "#FB923C",
            "banner_text": "#FFEDD5",
            "banner_start": "#C2410C",
            "banner_end": "#9A3412",
        },
        {
            "primary": "#FB923C",
            "primary_dark": "#FDBA74",
            "primary_light": "#2E1D10",
            "primary_gradient": "#C2410C",
            "banner_text": "#FFEDD5",
            "banner_start": "#C2410C",
            "banner_end": "#7C2D12",
        },
    ),
    "rouge": (
        "Rouge arrêt d'urgence",
        8,
        {
            "primary": "#B91C1C",
            "primary_dark": "#991B1B",
            "primary_light": "#FDECEC",
            "primary_gradient": "#F87171",
            "banner_text": "#FEE2E2",
            "banner_start": "#B91C1C",
            "banner_end": "#7F1D1D",
        },
        {
            "primary": "#F87171",
            "primary_dark": "#FCA5A5",
            "primary_light": "#3A1A1C",
            "primary_gradient": "#B91C1C",
            "banner_text": "#FEE2E2",
            "banner_start": "#B91C1C",
            "banner_end": "#7F1D1D",
        },
    ),
    "or": (
        "Or du technicien expert",
        10,
        {
            "primary": "#A16207",
            "primary_dark": "#854D0E",
            "primary_light": "#FEF9C3",
            "primary_gradient": "#EAB308",
            "banner_text": "#FEF9C3",
            "banner_start": "#A16207",
            "banner_end": "#713F12",
        },
        {
            "primary": "#FACC15",
            "primary_dark": "#FDE047",
            "primary_light": "#2E2810",
            "primary_gradient": "#A16207",
            "banner_text": "#FEF9C3",
            "banner_start": "#A16207",
            "banner_end": "#713F12",
        },
    ),
}

# Cadre d'avatar autour du badge de niveau : (nom, niveau requis, couleur, épaisseur)
FRAMES = {
    "aucun": ("Sans cadre", 1, "", 0),
    "bronze": ("Bronze", 3, "#B45309", 3),
    "argent": ("Argent", 5, "#94A3B8", 3),
    "or": ("Or", 7, "#EAB308", 4),
    "diamant": ("Diamant", 10, "#22D3EE", 4),
}


def load_cosmetics(pDatabaseFile):
    """Retourne les choix enregistrés : accent, cadre et sons, valeurs connues seulement."""

    vData = load_json_setting(pDatabaseFile, COSMETICS_KEY, {}, dict)

    rCosmetics = {
        "accent": (
            vData.get("accent") if vData.get("accent") in ACCENTS else DEFAULT_ACCENT
        ),
        "frame": vData.get("frame") if vData.get("frame") in FRAMES else DEFAULT_FRAME,
        "sounds": vData.get("sounds", True) is not False,
    }

    return rCosmetics


def build_cosmetics_view(pDatabaseFile, pLevel):
    """Retourne les récompenses avec leur état : débloquée, choisie, niveau requis.

    Un choix dont le niveau n'est plus atteint retombe sur la valeur de départ.
    """

    vChosen = load_cosmetics(pDatabaseFile)
    vAccent = (
        vChosen["accent"] if ACCENTS[vChosen["accent"]][1] <= pLevel else DEFAULT_ACCENT
    )
    vFrame = (
        vChosen["frame"] if FRAMES[vChosen["frame"]][1] <= pLevel else DEFAULT_FRAME
    )

    rView = {
        "accent": vAccent,
        "frame": vFrame,
        "frame_color": FRAMES[vFrame][2],
        "frame_width": FRAMES[vFrame][3],
        "sounds": vChosen["sounds"],
        "accents": [
            {
                "id": vId,
                "label": vLabel,
                "level": vLevel,
                "color": vLight.get("primary", "#155FCC"),
                "unlocked": vLevel <= pLevel,
                "chosen": vId == vAccent,
            }
            for vId, (vLabel, vLevel, vLight, _) in ACCENTS.items()
        ],
        "frames": [
            {
                "id": vId,
                "label": vLabel,
                "level": vLevel,
                "color": vColor,
                "unlocked": vLevel <= pLevel,
                "chosen": vId == vFrame,
            }
            for vId, (vLabel, vLevel, vColor, _) in FRAMES.items()
        ],
    }

    return rView


def choose_cosmetic(pDatabaseFile, pKind, pId, pLevel):
    """Choisit une couleur d'accent ou un cadre ; lève ValueError s'il est inconnu ou verrouillé."""

    vCatalog = {"accent": ACCENTS, "frame": FRAMES}.get(pKind)

    if vCatalog is None or pId not in vCatalog:
        raise ValueError("Récompense inconnue.")

    if vCatalog[pId][1] > pLevel:
        raise ValueError(f"Débloqué au niveau {vCatalog[pId][1]}.")

    vData = load_json_setting(pDatabaseFile, COSMETICS_KEY, {}, dict)
    vData[pKind] = pId
    save_json_setting(pDatabaseFile, COSMETICS_KEY, vData)
    logger.info("Récompense choisie : %s %s", pKind, pId)


def set_sounds(pDatabaseFile, pEnabled):
    """Active ou coupe le son de réussite."""

    vData = load_json_setting(pDatabaseFile, COSMETICS_KEY, {}, dict)
    vData["sounds"] = bool(pEnabled)
    save_json_setting(pDatabaseFile, COSMETICS_KEY, vData)


def get_accent_colors(pAccent, pTheme):
    """Retourne les teintes qui remplacent celles du thème pour un accent, ou {}."""

    vAccent = ACCENTS.get(pAccent, ACCENTS[DEFAULT_ACCENT])

    rColors = dict(vAccent[3] if pTheme == "dark" else vAccent[2])

    return rColors
