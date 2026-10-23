"""Jeu de CV fictifs aux mises en page difficiles, lus de bout en bout par l'import

Chaque cas reprend une forme rencontrée sur de vrais CV : zones de texte Word
doublées et photo lourde, colonnes en tableau, PDF sur deux colonnes, texte
Windows à tirets. Les personnes et entreprises sont inventées.
"""

import io
import zipfile

import pytest

from job.cv_import import extract_profile, read_cv_text
from tests.job.test_cv_import import build_pdf

PHOTO = b"\x89PNG" + b"0" * (8 * 1024 * 1024)


def build_word(pBody, pPhoto=False):
    """Construit un document Word à partir du corps XML, avec une photo au besoin."""

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="w" xmlns:mc="mc" xmlns:wp="wp"><w:body>'
            + pBody
            + "</w:body></w:document>",
        )

        if pPhoto:
            vArchive.writestr("word/media/image1.png", PHOTO)

    rContent = vBuffer.getvalue()

    return rContent


def paragraphs(*pLines):
    """Retourne un paragraphe Word par ligne."""

    rXml = "".join(f"<w:p><w:r><w:t>{vLine}</w:t></w:r></w:p>" for vLine in pLines)

    return rXml


def text_box(*pLines):
    """Retourne une zone de texte : version moderne, copie de secours et position."""

    vContent = f"<w:txbxContent>{paragraphs(*pLines)}</w:txbxContent>"

    rXml = (
        "<w:p><w:r><wp:positionH><wp:posOffset>-567479</wp:posOffset>"
        f"</wp:positionH><mc:AlternateContent><mc:Choice>{vContent}</mc:Choice>"
        f"<mc:Fallback>{vContent}</mc:Fallback></mc:AlternateContent></w:r></w:p>"
    )

    return rXml


def table(*pColumns):
    """Retourne un tableau d'une ligne, une cellule par colonne de lignes."""

    vCells = "".join(f"<w:tc>{paragraphs(*vLines)}</w:tc>" for vLines in pColumns)

    rXml = f"<w:tbl><w:tr>{vCells}</w:tr></w:tbl>"

    return rXml


CASES = {
    "word-zones-de-texte-et-photo": (
        "cv.docx",
        build_word(
            text_box("claire.martin@example.com", "Lyon (69)", "Permis B")
            + text_box("Claire MARTIN", "Technicienne de maintenance industrielle")
            + text_box(
                "2019 – aujourd'hui",
                "• Maintenance préventive et curative des lignes",
                "• Programmation d'automates Siemens TIA Portal",
                "Technicienne de maintenance - Usine Delta",
            ),
            pPhoto=True,
        ),
    ),
    "word-colonnes-en-tableau": (
        "cv.docx",
        build_word(
            paragraphs("Karim Benali", "Développeur Java confirmé")
            + table(
                ["Compétences", "Java, Spring Boot, PostgreSQL", "Docker et Git"],
                [
                    "Expériences",
                    "mars 2020 - présent",
                    "Développeur backend - Société Epsilon",
                    "- API REST en Java et Spring",
                    "- Migration vers PostgreSQL",
                ],
            )
        ),
    ),
    "pdf-deux-colonnes": ("cv.pdf", build_pdf("Julie Petit   Python Django SQL")),
    "texte-windows-a-tirets": (
        "cv.txt",
        (
            "Marc Leroy\r\nÉlectrotechnicien\r\n\r\n2015 - 2023\r\n"
            "Électricien - Atelier Sigma\r\n- Câblage d'armoires, schémas électriques"
            "\r\n- Habilitation électrique B2V\r\n"
        ).encode("utf-8"),
    ),
}

EXPECTED = {
    "word-zones-de-texte-et-photo": (
        "Claire MARTIN",
        "Technicienne de maintenance industrielle",
        {"Siemens TIA Portal", "Maintenance préventive et curative"},
        ["Technicienne de maintenance - Usine Delta (2019 – aujourd'hui)"],
    ),
    "word-colonnes-en-tableau": (
        "Karim Benali",
        "",
        {"Java", "Spring", "PostgreSQL", "Docker", "Git", "REST"},
        ["Développeur backend - Société Epsilon (mars 2020 - présent)"],
    ),
    "pdf-deux-colonnes": ("", "", {"Python", "Django", "SQL"}, []),
    "texte-windows-a-tirets": (
        "Marc Leroy",
        "Électrotechnicien",
        {"Schémas électriques", "Habilitation électrique"},
        ["Électricien - Atelier Sigma (2015 - 2023)"],
    ),
}


@pytest.mark.parametrize("pCase", CASES, ids=list(CASES))
def test_cv_corpus_is_read_end_to_end(pCase):
    """Vérifie nom, présentation, compétences et expériences de chaque CV fictif."""

    vFileName, vContent = CASES[pCase]
    vName, vHeadline, vSkills, vTitles = EXPECTED[pCase]

    vText = read_cv_text(vFileName, vContent)
    vProfile = extract_profile(vText)

    assert vProfile["name"] == vName
    assert vHeadline in (vProfile["headline"], "")
    assert vSkills <= set(vProfile["skills"])
    assert [vItem["title"] for vItem in vProfile["experiences"]] == vTitles
    # Une zone de texte n'est lue qu'une fois, sans les positions des dessins.
    assert vText.count(vName or "Python") == 1
    assert "-567479" not in vText
