"""Tests des schémas SVG des lots de révision"""

import xml.etree.ElementTree as ET

from job.quiz_import import UNSAFE_SVG_PATTERN
from tools.quiz_svg import WIDTH, build_chain_svg, wrap_label


def test_wrap_label_cuts_on_words():
    """Vérifie la coupe d'un libellé sans couper les mots."""

    assert wrap_label("Régulateur maître de température", 12) == [
        "Régulateur",
        "maître de",
        "température",
    ]
    assert wrap_label("Court", 12) == ["Court"]


def test_chain_svg_is_valid_and_safe():
    """Vérifie un schéma complet : XML valide, texte échappé, rien de dangereux."""

    vSvg = build_chain_svg(
        "Boucle <fermée> & retour",
        ["Consigne", "Régulateur", "Vanne", "Procédé"],
        (3, 0, "mesure"),
        "Légende",
    )
    vRoot = ET.fromstring(vSvg)
    vTexts = [vElement.text for vElement in vRoot.iter() if vElement.text]

    assert int(vRoot.get("width")) == WIDTH
    assert "Boucle <fermée> & retour" in vTexts
    assert {"mesure", "Légende", "Vanne"} <= set(vTexts)
    assert not UNSAFE_SVG_PATTERN.search(vSvg)


def test_chain_svg_grows_with_feedback_and_note():
    """Vérifie que la hauteur suit les éléments facultatifs."""

    vHeights = [
        int(
            ET.fromstring(build_chain_svg("Titre", ["A", "B"], *vOptions)).get("height")
        )
        for vOptions in ((), ((1, 0, "retour"),), ((1, 0, "retour"), "Note"))
    ]

    assert vHeights == sorted(vHeights)
    assert len(set(vHeights)) == 3
