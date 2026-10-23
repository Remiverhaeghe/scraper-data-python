"""Tests de l'import des packs de révision : schémas, guides et format enrichi"""

import io
import json
import zipfile
from datetime import datetime

import pytest

from job.quiz import (
    answer_question,
    build_quiz_overview,
    flag_question,
    load_active_quiz,
    load_quiz,
)
from job.quiz_export import export_quiz_pack
from job.quiz_import import (
    clear_imported_questions,
    is_safe_reference,
    describe_quiz_import,
    import_questions,
    import_questions_file,
    normalize_question,
)
from storage.database import initialize_database
from storage.quiz_answers import get_last_answers
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
    assert "type inconnu" in " ".join(vReport["rejected"])
    assert describe_quiz_import(vReport) == (
        "2 question(s) ajoutée(s) : Analyse RAM et JVM · 1 schéma(s) · 2 guide(s) "
        "· 2 écartée(s)."
    )
    assert (
        describe_quiz_import(
            {"added": 5, "themes": ["A", "B"], "rejected": [], "assets": 0, "guides": 0}
        )
        == "5 question(s) ajoutée(s) dans 2 thèmes."
    )

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


def test_export_pack_round_trip(database_file, tmp_path):
    """Vérifie l'export puis le réimport dans une base vide, sans les signalées."""

    import_questions_file(database_file, "", "pack.zip", build_pack(), NOW)
    flag_question(database_file, "ram-jvm-002")
    vPack = tmp_path / "export.zip"

    assert export_quiz_pack(database_file, vPack) == 1

    with zipfile.ZipFile(vPack) as vArchive:
        vManifest = json.loads(vArchive.read("manifest.json"))
        vNames = vArchive.namelist()

    assert vManifest["themes"][0]["file"] == "questions/ram-jvm.json"
    assert "assets/schemas/ram.svg" in vNames
    assert "guides/ram-jvm-analyse.md" in vNames

    vTarget = tmp_path / "autre.db"
    initialize_database(vTarget)

    vReport = import_questions_file(vTarget, "", "export.zip", vPack.read_bytes(), NOW)
    vQuestion = load_active_quiz(vTarget)["ram-jvm"]["questions"][0]

    assert (vReport["added"], vReport["assets"], vReport["guides"]) == (1, 1, 2)
    assert vReport["rejected"] == []
    assert vQuestion["visual"] == {"asset": "ram.svg", "alt": "RAM"}
    assert load_active_quiz(vTarget)["ram-jvm"]["skills"] == ["JVM", "GC"]


def test_export_pack_without_imported_questions(database_file, tmp_path):
    """Vérifie le message quand aucune question n'a été importée."""

    with pytest.raises(ValueError, match="Aucune question importée"):
        export_quiz_pack(database_file, tmp_path / "export.zip")


@pytest.mark.parametrize(
    "pUrl, pSafe",
    [
        ("https://docs.oracle.com/en/java/", True),
        ("https://developer.mozilla.org/fr/docs/Web/HTTP?x=1", True),
        ("http://docs.oracle.com/", False),
        ("https://bit.ly/abc", False),
        ("https://www.tinyurl.com/abc", False),
        ("https://user:secret@docs.oracle.com/", False),
        ("https://192.168.1.10/admin", False),
        ("https://docs.oracle.com:8443/", False),
        ("https://example.org/outil.EXE", False),
        ("https://localhost/", False),
        ("https://exemple.org:99999/", False),
        ("https://" + "a" * 500 + ".org/", False),
    ],
)
def test_is_safe_reference(pUrl, pSafe):
    """Vérifie les liens de référence gardés et ceux écartés pour la sécurité."""

    assert is_safe_reference(pUrl) is pSafe


def build_lot(pFolder, pThemeId):
    """Construit un lot au format des envois de ChatGPT : manifest sans liste."""

    rFiles = {
        f"{pFolder}/manifest.json": json.dumps({"id": pThemeId, "name": "Lot"}),
        f"{pFolder}/README.md": "# Lot",
        f"{pFolder}/questions/{pThemeId}.json": json.dumps(
            {
                "theme": f"Thème {pThemeId}",
                "questions": [build_pack_question(f"{pThemeId}-001", visual=None)],
            }
        ),
    }

    return rFiles


def write_zip(pFiles):
    """Écrit une archive en mémoire à partir de {nom: contenu}."""

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        for vName, vContent in pFiles.items():
            vArchive.writestr(vName, vContent)

    rContent = vBuffer.getvalue()

    return rContent


def test_import_archive_of_several_packs(database_file):
    """Vérifie une archive qui réunit plusieurs lots, chacun avec son manifest."""

    vContent = write_zip(
        {**build_lot("lots/lot-38", "git"), **build_lot("lots/lot-39", "python-bases")}
    )

    vReport = import_questions_file(database_file, "", "lots.zip", vContent, NOW)

    assert vReport["added"] == 2
    assert vReport["themes"] == ["Thème git", "Thème python-bases"]


def test_import_archive_of_archives(database_file):
    """Vérifie une archive qui contient d'autres archives, sur un niveau seulement."""

    vInner = write_zip(build_lot("lot-18", "linux"))
    vDeep = write_zip({"niveau-2.zip": write_zip(build_lot("lot-19", "bash"))})

    vReport = import_questions_file(
        database_file,
        "",
        "lots.zip",
        write_zip({"lot-18.zip": vInner, "profond.zip": vDeep, "casse.zip": b"x"}),
        NOW,
    )

    assert vReport["added"] == 1
    assert vReport["themes"] == ["Thème linux"]
    assert any("profond.zip" in vReason for vReason in vReport["rejected"])
    assert any("casse.zip" in vReason for vReason in vReport["rejected"])


def test_clear_imported_questions_keeps_shipped_ones(database_file):
    """Vérifie l'effacement : importées parties, livrées et leurs réponses gardées."""

    import_questions_file(database_file, "", "pack.zip", build_pack(), NOW)
    answer_question(database_file, load_quiz(), "sql-null", 1, NOW)
    answer_question(
        database_file, load_active_quiz(database_file), "ram-jvm-001", 0, NOW
    )
    flag_question(database_file, "ram-jvm-002")

    vCount, vBackupFile = clear_imported_questions(database_file, NOW)
    vQuiz = load_active_quiz(database_file)

    assert vCount == 2
    assert "avant-effacement-questions" in vBackupFile.name
    assert "ram-jvm" not in vQuiz
    assert len(vQuiz) == len(load_quiz())
    assert get_last_answers(database_file) == {"sql-null": True}
    assert get_quiz_guides(database_file) == []
    assert get_quiz_asset(database_file, "ram.svg") is None
