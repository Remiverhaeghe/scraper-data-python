"""Conversion d'un Markdown simple en HTML, pour les guides de révision

Seuls les titres, listes, paragraphes, code en ligne, gras et liens https sont
pris en charge : c'est ce qu'utilisent les guides. Tout le texte est échappé
avant la mise en forme, aucun HTML du fichier n'est donc interprété.
"""

import re
from html import escape

HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.*)$")
UNORDERED_PATTERN = re.compile(r"^[-*]\s+(.*)$")
ORDERED_PATTERN = re.compile(r"^\d+[.)]\s+(.*)$")
CODE_PATTERN = re.compile(r"`([^`]+)`")
BOLD_PATTERN = re.compile(r"\*\*([^*]+)\*\*")
# Lien Markdown [texte](https://...) ou adresse https:// seule
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https://[^\s)]+)\)")
URL_PATTERN = re.compile(r"(?<![\"'>])(https://[^\s<)]+)")


def render_inline(pText):
    """Met en forme le texte d'une ligne : code, gras et liens."""

    vText = escape(pText, quote=False)
    vCodes = []

    # Le code est mis de côté : son contenu ne doit pas être reformaté.
    def keep_code(pMatch):
        vCodes.append(f"<code>{pMatch.group(1)}</code>")

        rPlaceholder = f"\0{len(vCodes) - 1}\0"

        return rPlaceholder

    vText = CODE_PATTERN.sub(keep_code, vText)
    vText = BOLD_PATTERN.sub(r"<strong>\1</strong>", vText)
    vText = LINK_PATTERN.sub(
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', vText
    )
    vText = URL_PATTERN.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', vText
    )

    rHtml = re.sub(r"\0(\d+)\0", lambda pMatch: vCodes[int(pMatch.group(1))], vText)

    return rHtml


def render_markdown(pText):
    """Convertit un texte Markdown simple en HTML sûr."""

    vHtml = []
    vList = None

    def close_list():
        if vList:
            vHtml.append(f"</{vList}>")

    for vLine in str(pText or "").splitlines():
        vLine = vLine.strip()
        vHeading = HEADING_PATTERN.match(vLine)
        vItem = UNORDERED_PATTERN.match(vLine) or ORDERED_PATTERN.match(vLine)
        vKind = (
            None if not vItem else ("ul" if UNORDERED_PATTERN.match(vLine) else "ol")
        )

        if vKind != vList:
            close_list()
            vList = vKind

            if vKind:
                vHtml.append(f"<{vKind}>")

        if vItem:
            vHtml.append(f"<li>{render_inline(vItem.group(1))}</li>")
        elif vHeading:
            # Un niveau de moins : le titre de la page reste le seul h1.
            vLevel = len(vHeading.group(1)) + 1
            vHtml.append(f"<h{vLevel}>{render_inline(vHeading.group(2))}</h{vLevel}>")
        elif vLine:
            vHtml.append(f"<p>{render_inline(vLine)}</p>")

    close_list()

    rHtml = "\n".join(vHtml)

    return rHtml
