"""Tests du document PDF écrit sans bibliothèque"""

import io

from pypdf import PdfReader

from job.pdf_document import measure, wrap, write_pdf


def test_pdf_is_readable_with_french_text_and_title():
    """Vérifie un PDF valide, lisible, accents et guillemets compris."""

    vContent = write_pdf(
        [
            ("Camille Martin", 16, True, 0),
            ("Électricité « (B2V) » \\ œuvre", 10.5, False, 6),
        ],
        "CV de Camille",
    )
    vReader = PdfReader(io.BytesIO(vContent), strict=True)

    assert vContent.startswith(b"%PDF-1.4") and vContent.endswith(b"%%EOF\n")
    assert vReader.metadata.title == "CV de Camille"
    assert vReader.pages[0].extract_text() == (
        "Camille Martin\nÉlectricité « (B2V) » \\ œuvre"
    )


def test_unknown_characters_and_french_spaces_are_replaced():
    """Vérifie les espaces fines remplacées et un caractère hors WinAnsi devenu « ? »."""

    vText = PdfReader(io.BytesIO(write_pdf([("Prix : 10 → 12", 10, False, 0)])))

    assert vText.pages[0].extract_text() == "Prix : 10 ? 12"


def test_long_text_is_wrapped_and_spread_over_pages():
    """Vérifie le texte coupé à la largeur et les pages ajoutées quand il déborde."""

    vLines = wrap("mot " * 200, 10)
    vReader = PdfReader(
        io.BytesIO(write_pdf([("ligne", 12, False, 0)] * 70 + [("", 12, False, 0)]))
    )

    assert all(measure(vLine, 10) <= 483 for vLine in vLines)
    assert len(vLines) > 5
    assert len(vReader.pages) == 2


def test_word_wider_than_the_page_is_cut():
    """Vérifie qu'un mot plus large que la page est coupé plutôt que débordant."""

    vLines = wrap("début " + "x" * 200 + " fin", 10)

    assert vLines[0] == "début"
    assert all(measure(vLine, 10) <= 483 for vLine in vLines)
    assert "".join(vLines[1:-1]) + vLines[-1].split()[0] == "x" * 200
    assert wrap("", 10) == [""]
    assert measure("a", 10, True) > measure("a", 10)
