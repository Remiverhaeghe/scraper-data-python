"""Tests des fiches projet et des questions d'entretien sur un projet"""

from io import BytesIO

import pytest
from pypdf import PdfReader

from job.portfolio_projects import (
    PROJECTS,
    THEMES,
    get_facts,
    get_project,
    rank_projects,
)
from job.portfolio_sheet import (
    build_cv_line,
    build_letter_paragraph,
    build_portfolio_sheet,
    render_sheet_text,
    write_sheet_pdf,
)
from job.project_interview import (
    NUMBERS_NOTICE,
    build_project_questions,
    collect_hints,
    render_questions_text,
)


def test_projects_are_public_github_repositories_with_known_themes():
    """Vérifie que chaque projet pointe vers un dépôt public et classe ses faits."""

    assert [vProject["id"] for vProject in PROJECTS] == [
        "atelier",
        "kalkul",
        "tremplin",
    ]

    for vProject in PROJECTS:
        assert vProject["url"].startswith("https://github.com/Remiverhaeghe/")
        assert {vTheme for vTheme, _ in vProject["facts"]} <= set(THEMES)
        assert vProject["stack"] and vProject["features"] and vProject["code_tour"]


def test_get_project_and_facts():
    """Vérifie la recherche d'un projet et le tri de ses faits par thème."""

    vAtelier = get_project("atelier")

    assert any("permission Internet" in vFact for vFact in get_facts(vAtelier, "data"))
    assert get_facts(get_project("kalkul"), "data") == []

    with pytest.raises(KeyError):
        get_project("inconnu")


def test_rank_projects_by_common_skills():
    """Vérifie le classement des projets selon les compétences d'une offre."""

    vRanked = rank_projects(["python", " Docker ", "Java", "Git"])

    assert vRanked[0]["project"]["id"] == "tremplin"
    assert vRanked[0]["common"] == ["Python", "Docker", "Git"]
    assert [vItem["project"]["id"] for vItem in vRanked[1:]] == ["kalkul", "atelier"]
    assert rank_projects(["COBOL"]) == []
    assert rank_projects(None) == []


def test_sheet_reuses_readme_facts_only():
    """Vérifie la fiche : rubriques, faits du README et source datée."""

    vSheet = build_portfolio_sheet(get_project("kalkul"))
    vHeadings = [vHeading for vHeading, _ in vSheet["sections"]]

    assert vHeadings[:3] == ["En bref", "Technologies", "Ce que fait le projet"]
    assert "Données et confidentialité" not in vHeadings
    assert "À montrer dans le code" in vHeadings
    assert vHeadings[-1] == "Suite prévue"
    assert "relevés le 19/11/2026" in vSheet["source"]
    assert "Licence : MIT" in vSheet["source"]

    # Sans suite prévue, la rubrique disparaît.
    assert "Suite prévue" not in [
        vHeading
        for vHeading, _ in build_portfolio_sheet(get_project("tremplin"))["sections"]
    ]


def test_texts_for_cv_and_letter():
    """Vérifie la ligne du CV et le paragraphe de lettre, avec le lien public."""

    vAtelier = get_project("atelier")

    assert build_cv_line(vAtelier).startswith("Atelier (Flutter, Dart, Android) : ")
    assert build_cv_line(vAtelier).endswith(vAtelier["url"])

    vParagraph = build_letter_paragraph(vAtelier)

    assert vParagraph.startswith("Sur mon temps personnel, j'ai développé Atelier, ")
    assert "couvertes à 95 %" in vParagraph
    assert vParagraph.endswith(f"Le code est public : {vAtelier['url']}.")


def test_letter_falls_back_on_architecture_without_test_fact():
    """Vérifie qu'un projet sans fait de test cite son organisation."""

    vProject = {
        **get_project("kalkul"),
        "facts": (("architecture", "Logique séparée de l'interface."),),
    }

    assert "Logique séparée de l'interface." in build_letter_paragraph(vProject)


def test_sheet_text_and_pdf():
    """Vérifie l'export en texte puis en PDF lisible."""

    vSheet = build_portfolio_sheet(get_project("tremplin"))
    vText = render_sheet_text(vSheet)

    assert vText.startswith("Tremplin - Outil de recherche d'emploi en Python\n")
    assert "- Python 3, FastAPI" in vText
    assert vText.endswith(vSheet["source"])

    vReader = PdfReader(BytesIO(write_sheet_pdf(vSheet)))
    vContent = " ".join(vPage.extract_text() for vPage in vReader.pages)

    assert vReader.metadata.title == "Tremplin - fiche projet"
    assert "21 sources" in vContent


def test_questions_have_hints_from_the_project():
    """Vérifie les questions : pistes tirées des faits, question sans fait écartée."""

    vKalkul = get_project("kalkul")
    vQuestions = build_project_questions(vKalkul)
    vByQuestion = {vItem["question"]: vItem for vItem in vQuestions}

    assert "Où sont les données, et comment les protégez-vous ?" not in vByQuestion
    assert vByQuestion["Présentez-moi ce projet en deux minutes."]["hints"] == [
        vKalkul["summary"]
    ]
    assert "MoteurCalcul.java : Logique de l'écran, testée sans interface." in (
        vByQuestion["Comment le code est-il organisé ?"]["hints"]
    )
    assert vByQuestion["Qu'est-ce qui vient ensuite ?"]["hints"] == list(
        vKalkul["next"]
    )
    assert all(vItem["reason"] and vItem["advice"] for vItem in vQuestions)
    assert collect_hints(vKalkul, ("stack",)) == [
        "Technologies : Java 17, Maven, JUnit 5, Swing."
    ]


def test_questions_text_lists_hints_and_notice():
    """Vérifie l'export des questions en texte, avec le rappel sur les chiffres."""

    vAtelier = get_project("atelier")
    vText = render_questions_text(vAtelier, build_project_questions(vAtelier))

    assert vText.startswith("Entretien : questions probables sur Atelier\n")
    assert "1. Présentez-moi ce projet en deux minutes." in vText
    assert "   Conseil : " in vText
    assert vText.endswith(NUMBERS_NOTICE)
