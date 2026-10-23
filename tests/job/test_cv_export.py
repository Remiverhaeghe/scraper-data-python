"""Tests du CV adapté à une offre"""

import io
import zipfile

from job.cv_export import (
    build_file_name,
    build_tailored_cv,
    write_docx,
    write_letter_docx,
)
from job.cv_import import read_docx

PROFILE = {
    "name": "Camille Martin",
    "headline": "Développeur Java",
    "skills": ["PHP", "Java", "SQL", "Git"],
    "experiences": [
        {"title": "Développeur PHP", "skills": "PHP, MySQL", "achievement": "Site"},
        {
            "title": "Développeur Java",
            "skills": "Java, SQL",
            "achievement": "API <REST>",
        },
    ],
}

OFFER = {
    "title": "Développeur Java/SQL",
    "company": "Acme",
    "description": "Java et SQL",
}


def test_cv_puts_the_offer_skills_and_experiences_first():
    """Vérifie l'ordre : compétences de l'offre, puis expériences qui les mobilisent."""

    vCv = build_tailored_cv(PROFILE, OFFER)

    assert vCv["matching_skills"] == ["Java", "SQL"]
    assert vCv["other_skills"] == ["PHP", "Git"]
    assert [vExperience["title"] for vExperience in vCv["experiences"]] == [
        "Développeur Java",
        "Développeur PHP",
    ]
    assert vCv["target"] == "Développeur Java/SQL · Acme"


def test_docx_is_a_valid_word_archive_with_escaped_text():
    """Vérifie l'archive Word : parties attendues et texte échappé."""

    vContent = write_docx(build_tailored_cv(PROFILE, OFFER))

    with zipfile.ZipFile(io.BytesIO(vContent)) as vArchive:
        vNames = set(vArchive.namelist())
        vDocument = vArchive.read("word/document.xml").decode("utf-8")

    assert vNames == {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
    assert "Compétences clés pour ce poste" in vDocument
    assert "API &lt;REST&gt;" in vDocument
    assert vDocument.index("Développeur Java<") < vDocument.index("Développeur PHP<")


def test_file_name_is_safe():
    """Vérifie le nom de fichier : caractères interdits retirés."""

    assert build_file_name(OFFER) == "CV - Acme - Développeur Java SQL.docx"


def test_docx_is_read_back_by_the_cv_import():
    """Vérifie que le CV écrit se relit comme un vrai document Word."""

    vText = read_docx(write_docx(build_tailored_cv(PROFILE, OFFER)))

    assert vText.splitlines()[:2] == ["Camille Martin", "Développeur Java"]
    assert "Java, SQL" in vText


def test_letter_is_written_line_by_line():
    """Vérifie la lettre en Word : une ligne par paragraphe, texte échappé."""

    vText = read_docx(write_letter_docx("Madame, Monsieur,\n\nJe postule <ici>."))

    assert vText.splitlines()[0] == "Madame, Monsieur,"
    assert "Je postule <ici>." in vText
    assert (
        build_file_name(OFFER, "Lettre") == "Lettre - Acme - Développeur Java SQL.docx"
    )
