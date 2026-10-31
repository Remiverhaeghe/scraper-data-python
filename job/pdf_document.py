"""Document PDF simple (A4, texte seul) écrit sans bibliothèque externe

Le serveur web n'embarque pas Qt : ce module produit le même PDF sur le bureau
et sur le web. Les polices Helvetica standard, présentes dans tout lecteur PDF,
évitent d'embarquer un fichier de police ; leur encodage WinAnsi couvre le
français, un caractère hors de cet encodage devient « ? ».
"""

import unicodedata

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 56
LINE_SPACING = 1.3
FONTS = {False: "F1", True: "F2"}
# Bloc dont le texte commence une nouvelle page (sans effet en haut de page)
PAGE_BREAK = "\f"

# Largeurs Helvetica (millièmes de corps) des caractères 32 à 126
ASCII_WIDTHS = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
)  # fmt: skip
OTHER_WIDTHS = {"•": 350, "–": 556, "—": 1000, "…": 1000, "’": 222, "«": 556, "»": 556}
DEFAULT_WIDTH = 556
# Le gras est un peu plus large : marge prise sur la largeur estimée
BOLD_FACTOR = 1.12
# Espaces fines de la typographie française, absentes de WinAnsi
SPACES = str.maketrans({" ": " ", " ": " ", " ": " "})


def get_char_width(pChar):
    """Retourne la largeur Helvetica d'un caractère, celle de sa lettre de base si accentué."""

    vBase = unicodedata.normalize("NFD", pChar)[:1] or pChar

    if 32 <= ord(vBase) <= 126:
        return ASCII_WIDTHS[ord(vBase) - 32]

    return OTHER_WIDTHS.get(pChar, DEFAULT_WIDTH)


def measure(pText, pSize, pBold=False):
    """Retourne la largeur d'un texte en points."""

    rWidth = (
        sum(get_char_width(vChar) for vChar in pText)
        * pSize
        / 1000
        * (BOLD_FACTOR if pBold else 1)
    )

    return rWidth


def wrap(pText, pSize, pBold=False, pWidth=PAGE_WIDTH - 2 * MARGIN):
    """Découpe un texte en lignes qui tiennent dans la largeur ; un mot trop long est coupé."""

    rLines = []
    vLine = ""

    for vWord in pText.split():
        while measure(vWord, pSize, pBold) > pWidth:
            vCut = len(vWord) - 1

            while vCut > 1 and measure(vWord[:vCut], pSize, pBold) > pWidth:
                vCut -= 1

            if vLine:
                rLines.append(vLine)
                vLine = ""

            rLines.append(vWord[:vCut])
            vWord = vWord[vCut:]

        vCandidate = f"{vLine} {vWord}" if vLine else vWord

        if vLine and measure(vCandidate, pSize, pBold) > pWidth:
            rLines.append(vLine)
            vLine = vWord
        else:
            vLine = vCandidate

    rLines.append(vLine)

    return rLines


def encode_text(pText):
    """Retourne une chaîne PDF littérale, encodée en WinAnsi et échappée."""

    vBytes = pText.translate(SPACES).encode("cp1252", errors="replace")

    rLiteral = (
        b"("
        + vBytes.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        + b")"
    )

    return rLiteral


def layout_pages(pBlocks):
    """Place les blocs (texte, corps, gras, espace avant) et retourne le contenu de chaque page."""

    rPages = [[]]
    vTop = PAGE_HEIGHT - MARGIN

    for vText, vSize, vBold, vSpaceBefore in pBlocks:
        if vText == PAGE_BREAK:
            if rPages[-1]:
                rPages.append([])
                vTop = PAGE_HEIGHT - MARGIN

            continue

        vTop -= vSpaceBefore if rPages[-1] else 0

        for vLine in wrap(str(vText or ""), vSize, vBold):
            vTop -= vSize * LINE_SPACING

            if vTop < MARGIN:
                rPages.append([])
                vTop = PAGE_HEIGHT - MARGIN - vSize * LINE_SPACING

            if vLine:
                rPages[-1].append(
                    b"BT /%s %g Tf %d %.1f Td %s Tj ET"
                    % (
                        FONTS[vBold].encode(),
                        vSize,
                        MARGIN,
                        vTop,
                        encode_text(vLine),
                    )
                )

    return rPages


def write_pdf(pBlocks, pTitle=""):
    """Retourne les octets d'un PDF A4 fait de blocs (texte, corps, gras, espace avant)."""

    vPages = layout_pages(pBlocks)
    vFirstPage = 5
    vObjects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (
            b" ".join(
                b"%d 0 R" % (vFirstPage + 2 * vIndex) for vIndex in range(len(vPages))
            ),
            len(vPages),
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        b"/Encoding /WinAnsiEncoding >>",
    ]

    for vIndex, vLines in enumerate(vPages):
        vStream = b"\n".join(vLines)
        vObjects += [
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>"
            % (PAGE_WIDTH, PAGE_HEIGHT, vFirstPage + 2 * vIndex + 1),
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(vStream), vStream),
        ]

    vObjects.append(b"<< /Title %s >>" % encode_text(pTitle))

    vContent = bytearray(b"%PDF-1.4\n")
    vOffsets = []

    for vNumber, vObject in enumerate(vObjects, start=1):
        vOffsets.append(len(vContent))
        vContent += b"%d 0 obj\n%s\nendobj\n" % (vNumber, vObject)

    vXref = len(vContent)
    vContent += b"xref\n0 %d\n0000000000 65535 f \n" % (len(vObjects) + 1)
    vContent += b"".join(b"%010d 00000 n \n" % vOffset for vOffset in vOffsets)
    vContent += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\n" % (
        len(vObjects) + 1,
        len(vObjects),
    )
    vContent += b"startxref\n%d\n%%%%EOF\n" % vXref

    rContent = bytes(vContent)

    return rContent
