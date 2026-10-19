"""Rendu partagé des pages : gabarits, icônes, graphiques et messages"""

import re
from functools import lru_cache
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from config import (
    APPLICATION_NAME,
    ASSETS_DIRECTORY,
    CONTACT_URL,
    LICENSE_NAME,
    REPOSITORY_URL,
    TAGLINE,
)
from job.presentation import (
    CHART_PALETTE,
    format_date,
    format_euros,
    safe_url,
    get_score_tone,
)
from job.schema_drawing import (
    GRID_COLUMNS,
    GRID_ROWS,
    build_editor_config,
    render_correction,
)
from job.schema_library import COMPONENTS, build_icon
from web.dependencies import get_csrf_token

WEB_DIRECTORY = Path(__file__).parent


ICONS_DIRECTORY = ASSETS_DIRECTORY / "icons"


ICON_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")


# Icône associée à chaque tonalité d'exécution
TONE_ICONS = {
    "success": "circle-check",
    "warning": "circle-alert",
    "danger": "circle-alert",
}


templates = Jinja2Templates(directory=WEB_DIRECTORY / "templates")


# Fonctions et filtres disponibles dans les gabarits Jinja.
@lru_cache
def render_icon(pName, pSize=18):
    """Retourne le SVG d'une icône à insérer dans la page, ou rien s'il n'existe pas.

    Insérée telle quelle, l'icône prend la couleur du texte grâce à currentColor.
    Seuls les noms simples d'un fichier du dossier d'icônes sont acceptés.
    """

    rIcon = Markup("")

    vPath = ICONS_DIRECTORY / f"{pName}.svg"

    if ICON_NAME_PATTERN.fullmatch(pName) and vPath.is_file():
        vSvg = vPath.read_text(encoding="utf-8")
        vSvg = vSvg[vSvg.index("<svg") :]
        vSvg = vSvg.replace('width="24"', f'width="{pSize}"', 1)
        vSvg = vSvg.replace('height="24"', f'height="{pSize}"', 1)
        vSvg = vSvg.replace("<svg", '<svg aria-hidden="true" focusable="false"', 1)

        # Fichier SVG du projet, au nom validé par ICON_NAME_PATTERN : jamais une
        # donnée saisie ou reçue d'une source.
        rIcon = Markup(vSvg)  # nosec B704

    return rIcon


def render_schema_icon(pType):
    """Retourne l'icône SVG d'un composant de schéma, pour la palette."""

    # Symbole constant de job/schema_library.py, jamais une donnée saisie.
    rIcon = Markup(build_icon(pType))  # nosec B704

    return rIcon


def render_correction_schema(pQuestion, pResponse):
    """Retourne le schéma construit à côté du schéma attendu, à la correction."""

    # Dessin construit par job/schema_drawing.py, libellés échappés : HTML sûr.
    rSchema = Markup(render_correction(pQuestion, pResponse))  # nosec B704

    return rSchema


def get_schema_config(pTypes, pLimits=None):
    """Retourne la géométrie, les symboles et les exemplaires permis de l'éditeur web."""

    rConfig = build_editor_config(pTypes, GRID_COLUMNS, GRID_ROWS, pLimits)

    return rConfig


templates.env.filters["euros"] = format_euros


templates.env.filters["date_fr"] = format_date


templates.env.filters["safe_url"] = safe_url

# Couleur d'un score sur 100, la même qu'au bureau
templates.env.filters["score_tone"] = get_score_tone


templates.env.globals.update(
    icon=render_icon,
    app_name=APPLICATION_NAME,
    tagline=TAGLINE,
    repository_url=REPOSITORY_URL,
    contact_url=CONTACT_URL,
    license_name=LICENSE_NAME,
    csrf_token=get_csrf_token,
    schema_icon=render_schema_icon,
    schema_label=lambda pType: COMPONENTS[pType].label,
    schema_config=get_schema_config,
    correction_schema=render_correction_schema,
)


def get_message_tone(pStatusCode):
    """Retourne la couleur d'un message : réussite, saisie refusée ou panne."""

    if pStatusCode >= 500:
        rTone = "danger"
    elif pStatusCode >= 400:
        rTone = "warning"
    else:
        rTone = "success"

    return rTone


# Préparation des graphiques : le serveur calcule les hauteurs, le dessin est
# entièrement en CSS (pas de bibliothèque JavaScript).
def build_bar_chart(
    pLabels,
    pSeries,
    pIndependentScales=False,
    pAxes=(None, None),
    pEmptyText="",
    pFillWidth=False,
):
    """Prépare un histogramme : pSeries contient des (nom, couleur, valeurs).

    Les hauteurs sont relatives à la plus grande valeur toutes séries confondues,
    ou à celle de chaque série avec pIndependentScales, pour qu'une série de
    faibles valeurs reste visible à côté d'une série de valeurs élevées.
    """

    vCommonMaximum = (
        max((vValue for _, _, vValues in pSeries for vValue in vValues), default=0) or 1
    )

    vSeries = []

    for vName, vColor, vValues in pSeries:
        vMaximum = (
            (max(vValues, default=0) or 1) if pIndependentScales else vCommonMaximum
        )

        vSeries.append(
            {
                "name": vName,
                "color": vColor,
                # Une couleur par barre quand la série en donne une liste
                "bars": [
                    {
                        "value": vValue,
                        "height": max(round(100 * vValue / vMaximum), 2),
                        "color": (
                            vColor[vIndex]
                            if isinstance(vColor, (list, tuple))
                            else vColor
                        ),
                    }
                    for vIndex, vValue in enumerate(vValues)
                ],
            }
        )

    rChart = {
        "labels": pLabels,
        "series": vSeries,
        "x_axis": pAxes[0],
        "y_axis": pAxes[1],
        "fill": pFillWidth,
        # Valeur de la ligne haute : une par série avec des échelles indépendantes
        "scale": (
            [
                {"value": max(vValues), "color": vColor}
                for _, vColor, vValues in pSeries
                if any(vValues)
            ]
            if pIndependentScales
            else [{"value": vCommonMaximum, "color": None}]
        ),
        # Sans aucune valeur, le gabarit affiche ce texte à la place des barres.
        "empty_text": (
            pEmptyText
            if not any(vValue for _, _, vValues in pSeries for vValue in vValues)
            else ""
        ),
    }

    return rChart


def build_pie(pShares):
    """Prépare un camembert CSS : dégradé conique et légende colorée."""

    vItems = [
        {**vShare, "color": CHART_PALETTE[vIndex]}
        for vIndex, vShare in enumerate(pShares)
    ]

    vSegments = []
    vStart = 0
    vTotal = sum(vItem["count"] for vItem in vItems) or 1

    for vItem in vItems:
        vEnd = vStart + 100 * vItem["count"] / vTotal
        vSegments.append(f"{vItem['color']} {vStart:.2f}% {vEnd:.2f}%")
        vStart = vEnd

    rPie = {
        "slices": vItems,
        "total": sum(vItem["count"] for vItem in vItems),
        "gradient": f"conic-gradient({', '.join(vSegments)})" if vSegments else "",
    }

    return rPie
