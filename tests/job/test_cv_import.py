"""Tests de l'import d'un CV dans le profil"""

import io
import zipfile

import pytest

from job.cv_import import (
    MAX_CV_BYTES,
    build_cv_prompt,
    extract_profile,
    merge_profile_texts,
    read_cv_text,
)

CV_TEXT = (
    "Rémi Verhaeghe\n"
    "Développeur Java confirmé\n"
    "remi@example.com · 06 12 34 56 78\n"
    "Compétences\n"
    "Java, Spring Boot, SQL, Docker\n"
    "Expériences\n"
    "Développeur backend chez Acme : API Spring, réduit de 40 % le temps de réponse"
)


def build_pdf(pText):
    """Construit un PDF minimal d'une page contenant une ligne de texte."""

    vStream = f"BT /F1 12 Tf 72 720 Td ({pText}) Tj ET".encode("latin-1")
    vObjects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(vStream) + vStream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    rPdf = b"%PDF-1.4\n"
    vOffsets = []

    for vIndex, vObject in enumerate(vObjects, start=1):
        vOffsets.append(len(rPdf))
        rPdf += b"%d 0 obj\n" % vIndex + vObject + b"\nendobj\n"

    vXref = len(rPdf)
    rPdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(vObjects) + 1)
    rPdf += b"".join(b"%010d 00000 n \n" % vOffset for vOffset in vOffsets)
    rPdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(vObjects) + 1,
        vXref,
    )

    return rPdf


def build_docx(pParagraphs):
    """Construit un document Word minimal, un paragraphe par élément."""

    vBody = "".join(
        f"<w:p><w:r><w:t>{vParagraph}</w:t></w:r></w:p>" for vParagraph in pParagraphs
    )
    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        vArchive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="w"><w:body>' + vBody + "</w:body></w:document>",
        )

    rContent = vBuffer.getvalue()

    return rContent


def test_read_cv_text_from_each_format():
    """Vérifie la lecture d'un PDF, d'un document Word et d'un texte."""

    assert "Java Spring SQL" in read_cv_text("cv.pdf", build_pdf("Java Spring SQL"))
    assert read_cv_text("CV.DOCX", build_docx(["Rémi V.", "Java &amp; SQL"])) == (
        "Rémi V.\nJava & SQL\n"
    )
    assert read_cv_text("cv.txt", CV_TEXT.encode()) == CV_TEXT


@pytest.mark.parametrize(
    "pFileName, pContent, pMessage",
    [
        ("cv.odt", b"x", "formats acceptés"),
        ("cv.pdf", b"", "vide"),
        ("cv.pdf", b"x" * (MAX_CV_BYTES + 1), "20 Mo au maximum"),
        ("cv.pdf", b"pas un pdf", "endommagé"),
        ("cv.docx", b"pas un zip", "endommagé"),
        ("cv.txt", b"  \n ", "sans texte lisible"),
    ],
    ids=["format", "vide", "trop-gros", "pdf-abime", "docx-abime", "sans-texte"],
)
def test_read_cv_text_refuses_invalid_files(pFileName, pContent, pMessage):
    """Vérifie le refus d'un format inconnu, d'un fichier vide, trop gros ou abîmé."""

    with pytest.raises(ValueError, match=pMessage):
        read_cv_text(pFileName, pContent)


def test_extract_profile_finds_name_headline_and_skills():
    """Vérifie le nom en tête, la présentation qui suit et les compétences."""

    vProfile = extract_profile(CV_TEXT)

    assert vProfile["name"] == "Rémi Verhaeghe"
    assert vProfile["headline"] == "Développeur Java confirmé"
    assert {"Java", "Spring", "SQL", "Docker"} <= set(vProfile["skills"])


def test_extract_profile_skips_contact_and_section_lines():
    """Vérifie qu'une coordonnée ou un titre de rubrique n'est pas une présentation."""

    vProfile = extract_profile("CV\nremi@example.com\nCompétences\nPython")

    assert vProfile["name"] == ""
    assert vProfile["headline"] == ""


def test_merge_keeps_typed_texts_and_adds_skills():
    """Vérifie que la saisie est gardée et que les compétences sont fusionnées."""

    vTexts = merge_profile_texts(
        {"name": "Moi", "headline": "", "skills": "Java, Kafka", "experiences": "x"},
        {"name": "Autre", "headline": "Dev", "skills": ["java", "SQL"]},
    )

    assert vTexts == {
        "name": "Moi",
        "headline": "Dev",
        "skills": "Java, Kafka, SQL",
        "experiences": "x",
    }


def test_build_cv_prompt_asks_for_profile_format_and_truncates():
    """Vérifie le format demandé à ChatGPT et la coupe d'un texte trop long."""

    vPrompt = build_cv_prompt("x" * 9000)

    assert "Poste | compétences" in vPrompt
    assert "sans rien inventer" in vPrompt
    assert vPrompt.endswith("x […]")


def test_read_docx_skips_text_box_copies_and_drawing_positions():
    """Vérifie qu'une zone de texte n'est lue qu'une fois, sans les positions."""

    vXml = (
        '<w:document xmlns:w="w"><w:body><w:p><w:r>'
        "<wp:positionH><wp:posOffset>-567479</wp:posOffset></wp:positionH>"
        "<mc:AlternateContent><mc:Choice><w:txbxContent><w:p><w:r>"
        '<w:t xml:space="preserve">Rémi </w:t><w:tab/><w:t>Martin</w:t>'
        "</w:r></w:p></w:txbxContent></mc:Choice>"
        "<mc:Fallback><w:txbxContent><w:p><w:r><w:t>Rémi Martin</w:t></w:r></w:p>"
        "</w:txbxContent></mc:Fallback></mc:AlternateContent>"
        "</w:r></w:p></w:body></w:document>"
    )
    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        vArchive.writestr("word/document.xml", vXml)
        vArchive.writestr("word/media/photo.png", b"x" * 1024)

    assert read_cv_text("cv.docx", vBuffer.getvalue()).split() == ["Rémi", "Martin"]


def test_extract_profile_finds_the_name_after_contact_lines():
    """Vérifie le nom placé après les coordonnées, sans prendre « Permis B »."""

    vProfile = extract_profile(
        "remi@example.com\nRoubaix (59)\nPermis B\nDéveloppeur Java\n"
        "Rémi Martin\nProfil technique et industriel\nGMAO"
    )

    assert vProfile["name"] == "Rémi Martin"
    assert vProfile["headline"] == "Profil technique et industriel"
