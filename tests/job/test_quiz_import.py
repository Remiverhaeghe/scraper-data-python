"""Tests de l'import des packs de révision : schémas, guides et format enrichi"""

import io
import json
import zipfile
from datetime import datetime

import pytest

from job.quiz import build_quiz_overview, load_active_quiz
from job.quiz_import import (
    describe_quiz_import,
    import_questions,
    import_questions_file,
    normalize_question,
)
from storage.database import initialize_database
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from utils.markdown import render_markdown

NOW = datetime(2026, 10, 12, 10, 0)

SAFE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def build_pack_question(pId, **pValues):
    """Construit une question au format enrichi des packs."""

    rQuestion = {
        "id": pId,
        "level": "intermediaire",
        "type": "qcm",
        "question": f"Que montre {pId} ?",
        "choices": ["Le heap", "Le disque"],
        "answer": 0,
        "expectedAnswer": "Le heap",
        "explanation": "Parce que.",
        "tags": ["JVM", "GC"],
        "visual": {"type": "svg", "path": "../assets/schemas/ram.svg", "alt": "RAM"},
        "references": [
            {"title": "Oracle", "url": "https://docs.oracle.com/"},
            {"title": "Piège", "url": "javascript:alert(1)"},
        ],
    }
    rQuestion.update(pValues)

    return rQuestion


def build_pack(pExtraFiles=None):
    """Construit un pack .zip : manifest, thème, exemple ignoré, schéma et guide."""

    vFiles = {
        "pack/manifest.json": json.dumps(
            {"themes": [{"id": "ram-jvm", "file": "questions/ram-jvm.json"}]}
        ),
        "pack/schema-question-exemple.json": json.dumps(
            {"theme": "Exemple", "questions": [build_pack_question("theme-001")]}
        ),
        "pack/questions/ram-jvm.json": json.dumps(
            {
                "theme": "Analyse RAM et JVM",
                "skills": ["JVM", "GC"],
                "questions": [
                    build_pack_question("ram-jvm-001"),
                    build_pack_question("ram-jvm-002", level="expert", visual=None),
                    build_pack_question("ram-jvm-003", expectedAnswer="Le disque"),
                    build_pack_question("ram-jvm-004", type="ouverte"),
                ],
            }
        ),
        "pack/assets/schemas/ram.svg": SAFE_SVG,
        "pack/guides/ram-jvm-analyse.md": "# Guide — analyser la RAM\n- Heap",
        "pack/guides/rapport.md": "# Modèle de rapport\nTexte",
        "pack/README.md": "# Lisez-moi",
    }
    vFiles.update(pExtraFiles or {})

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        for vName, vContent in vFiles.items():
            vArchive.writestr(vName, vContent)

    rContent = vBuffer.getvalue()

    return rContent


def test_import_pack_reads_manifest_visuals_and_guides(database_file):
    """Vérifie l'import d'un pack : questions, schéma, guides et rejets motivés."""

    vReport = import_questions_file(database_file, "", "pack.zip", build_pack(), NOW)
    vTheme = load_active_quiz(database_file)["ram-jvm"]
    vFirst = vTheme["questions"][0]

    assert vReport["added"] == 2
    assert (vReport["assets"], vReport["guides"]) == (1, 2)
    assert vTheme["label"] == "Analyse RAM et JVM"
    assert vTheme["skills"] == ["JVM", "GC"]
    assert vFirst["level"] == "intermédiaire"
    assert vFirst["visual"] == {"asset": "ram.svg", "alt": "RAM"}
    assert vFirst["references"] == [
        {"title": "Oracle", "url": "https://docs.oracle.com/"}
    ]
    assert vFirst["tags"] == ["JVM", "GC"]
    assert "visual" not in vTheme["questions"][1]
    assert get_quiz_asset(database_file, "ram.svg") == SAFE_SVG
    assert "theme-001" not in str(load_active_quiz(database_file))
    assert "réponse attendue incohérente" in " ".join(vReport["rejected"])
    assert "seul le type qcm" in " ".join(vReport["rejected"])
    assert "1 schéma(s) et 2 guide(s)" in describe_quiz_import(vReport)

    vGuides = {vGuide["name"]: vGuide for vGuide in get_quiz_guides(database_file)}

    assert vGuides["ram-jvm-analyse"]["theme"] == "ram-jvm"
    assert vGuides["ram-jvm-analyse"]["title"] == "Analyser la RAM"
    assert vGuides["rapport"]["theme"] is None
    assert get_quiz_guide(database_file, "rapport")["content"].endswith("Texte")
    assert [
        vItem["guide"]
        for vItem in build_quiz_overview(database_file, load_active_quiz(database_file))
        if vItem["key"] == "ram-jvm"
    ] == ["ram-jvm-analyse"]


@pytest.mark.parametrize(
    "pSvg",
    [
        "<svg><script>alert(1)</script></svg>",
        '<svg><rect onload="alert(1)"/></svg>',
        '<svg><image href="https://pistage.example/x.png"/></svg>',
        "pas un svg",
    ],
)
def test_import_pack_refuses_unsafe_visuals(database_file, pSvg):
    """Vérifie qu'un schéma porteur de script, externe ou invalide est écarté."""

    vReport = import_questions_file(
        database_file,
        "",
        "pack.zip",
        build_pack({"pack/assets/schemas/ram.svg": pSvg}),
        NOW,
    )

    assert vReport["assets"] == 0
    assert "schéma refusé" in " ".join(vReport["rejected"])
    assert "visual" not in load_active_quiz(database_file)["ram-jvm"]["questions"][0]


def test_import_pack_reports_missing_files(database_file):
    """Vérifie les fichiers cités mais absents : thème et schéma."""

    vContent = build_pack(
        {
            "pack/manifest.json": json.dumps(
                {
                    "themes": [
                        {"id": "ram-jvm", "file": "questions/ram-jvm.json"},
                        {"id": "absent", "file": "questions/absent.json"},
                    ]
                }
            ),
            "pack/questions/ram-jvm.json": json.dumps(
                {
                    "questions": [
                        build_pack_question(
                            "ram-jvm-001",
                            visual={"type": "svg", "path": "../assets/absent.svg"},
                        )
                    ]
                }
            ),
        }
    )

    vReport = import_questions_file(database_file, "", "pack.zip", vContent, NOW)

    assert vReport["added"] == 1
    assert any("absent.json" in vReason for vReason in vReport["rejected"])
    assert any("schéma introuvable" in vReason for vReason in vReport["rejected"])


def test_import_pack_refuses_unreadable_manifest(database_file):
    """Vérifie le message d'un manifest.json illisible."""

    with pytest.raises(ValueError, match="manifest.json illisible"):
        import_questions_file(
            database_file,
            "",
            "pack.zip",
            build_pack({"pack/manifest.json": "{"}),
            NOW,
        )


def test_normalize_question_keeps_plain_questions(database_file):
    """Vérifie qu'une question simple, sans champ enrichi, reste inchangée."""

    vQuestion = {
        "id": "kafka-topic",
        "level": "Débutant",
        "question": "Topic ?",
        "choices": ["a", "b"],
        "answer": 1,
        "explanation": "x",
    }

    assert normalize_question(vQuestion, "question 1", {}) == {
        **vQuestion,
        "level": "débutant",
    }
    assert (
        import_questions(database_file, "Kafka", json.dumps([vQuestion]), NOW)["added"]
        == 1
    )


def test_render_markdown_escapes_and_formats():
    """Vérifie titres, listes, code, gras et liens, sans HTML du texte."""

    vHtml = render_markdown(
        "# Guide\n## Étapes\n1. Lancer `jcmd <pid>`\n2. **Analyser**\n"
        "- voir https://docs.oracle.com/x et [doc](https://a.org)\n"
        "<script>alert(1)</script> [piège](javascript:alert(1))"
    )

    assert vHtml.startswith("<h2>Guide</h2>\n<h3>Étapes</h3>\n<ol>")
    assert "<code>jcmd &lt;pid&gt;</code>" in vHtml
    assert "<strong>Analyser</strong>" in vHtml
    assert '<a href="https://a.org"' in vHtml
    assert '<a href="https://docs.oracle.com/x"' in vHtml
    assert "<script>" not in vHtml
    assert 'href="javascript' not in vHtml
