"""Méthodes utilitaires générales"""

import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup


def html_to_text(pHtml):
    """Convertit un contenu HTML en texte brut."""

    rText = None

    if pHtml:
        rText = BeautifulSoup(pHtml, "html.parser").get_text(" ", strip=True)

        # Certaines sources envoient du HTML échappé (&lt;p&gt;) : le premier
        # passage le décode, le second retire les balises ainsi révélées.
        if re.search(r"<[a-zA-Z/][^>]*>", rText):
            rText = BeautifulSoup(rText, "html.parser").get_text(" ", strip=True)

    return rText


def timestamp_to_iso(pTimestamp):
    """Convertit un horodatage Unix en date ISO au fuseau UTC."""

    rDate = None

    if pTimestamp not in (None, ""):
        rDate = datetime.fromtimestamp(int(pTimestamp), UTC).isoformat()

    return rDate


def join_values(pValues):
    """Regroupe une liste de valeurs en texte, ou retourne la valeur telle quelle."""

    rText = pValues or None

    if isinstance(pValues, list):
        rText = ", ".join(str(vValue) for vValue in pValues) or None

    return rText


def decode_unicode_escapes(pText):
    """Remplace les séquences \\uXXXX laissées telles quelles par leur caractère."""

    rText = pText

    # Les demi-codets (D800-DFFF) sont ignorés : seuls, ils rendraient le texte
    # impossible à encoder en UTF-8.
    if pText:
        rText = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda pMatch: (
                pMatch.group(0)
                if 0xD800 <= int(pMatch.group(1), 16) <= 0xDFFF
                else chr(int(pMatch.group(1), 16))
            ),
            pText,
        )

    return rText
