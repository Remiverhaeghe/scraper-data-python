"""Tests de la production et du contrôle des lots de révision"""

import io
import json
import zipfile
from collections import Counter

import pytest

import tools.quiz_lot as quiz_lot
from tools.quiz_lot import (
    LEVEL_LAYOUT,
    LOT_SIZE,
    LOTS_DIRECTORY,
    build_pack,
    build_questions,
    check_pack,
    load_lot,
    main,
    parse_lot_text,
)

QUESTION_TEXT = """@001
Q: Que vaut `X` ?
C: TRUE
W: FALSE
W: 0
W: 1
E: Explication détaillée de la notion et des erreurs courantes du candidat.
```
X := TRUE;
```

@002
Q: Seconde question ?
C: Bonne
W: Mauvaise un
W: Mauvaise deux
W: Mauvaise trois
E: Explication détaillée de la notion et des erreurs courantes du candidat.
"""


def write_lot(pFolder, pTheme, pQuestionCount=LOT_SIZE):
    """Écrit un lot de questions simples dans pFolder et retourne son dossier."""

    rFolder = pFolder / pTheme
    rFolder.mkdir(parents=True)
    vBlocks = [
        f"@{vNumber:03d}\nQ: Question {vNumber} ?\nC: Réponse juste {vNumber}\n"
        f"W: Réponse fausse {vNumber}\nW: Autre erreur {vNumber}\n"
        f"W: Dernière erreur {vNumber}\nE: Explication de la question {vNumber}, "
        "assez longue pour décrire la notion et chacune des erreurs proposées.\n"
        for vNumber in range(1, pQuestionCount + 1)
    ]
    (rFolder / "part1.txt").write_text("\n".join(vBlocks), encoding="utf-8")
    (rFolder / "lot.json").write_text(
        json.dumps(
            {
                "lot": 2,
                "seed": 7,
                "skills": ["Grafcet"],
                "schemas": [
                    {
                        "name": "test.svg",
                        "questions": ["001", "002"],
                        "diagram": {"title": "Test", "nodes": ["A", "B"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    return rFolder


def test_parse_lot_text_reads_fields_and_code():
    """Vérifie la lecture du format compact, extrait de code compris."""

    vQuestions = parse_lot_text(QUESTION_TEXT)

    assert sorted(vQuestions) == ["001", "002"]
    assert vQuestions["001"]["code"] == "X := TRUE;"
    assert vQuestions["001"]["W"] == ["FALSE", "0", "1"]
    assert vQuestions["002"]["code"] is None


@pytest.mark.parametrize(
    ("pText", "pMessage"),
    [
        ("@001\nQ: Énoncé ?\nC: Oui\nW: Non\nE: Explication.", "champs incomplets"),
        ("@001\nQ: Énoncé ?\nréponse sans champ", "ligne illisible"),
    ],
)
def test_parse_lot_text_refuses_incomplete_questions(pText, pMessage):
    """Vérifie le refus d'une question incomplète ou mal écrite."""

    with pytest.raises(ValueError, match=pMessage):
        parse_lot_text(pText)


def test_load_lot_requires_every_question(tmp_path):
    """Vérifie qu'un lot incomplet est refusé."""

    write_lot(tmp_path, "grafcet", pQuestionCount=3)

    with pytest.raises(ValueError, match="questions manquantes"):
        load_lot("grafcet", tmp_path)


def test_build_questions_spreads_answers_and_levels(tmp_path):
    """Vérifie les identifiants, les niveaux et la répartition des bonnes réponses."""

    write_lot(tmp_path, "grafcet")
    vConfig, vSource = load_lot("grafcet", tmp_path)

    vQuestions = build_questions("grafcet", vConfig, vSource)

    assert vQuestions[0]["id"] == "grafcet-l2-001"
    assert Counter(vQuestion["level"] for vQuestion in vQuestions) == dict(LEVEL_LAYOUT)
    assert set(Counter(vQuestion["answer"] for vQuestion in vQuestions).values()) == {
        LOT_SIZE // 4
    }
    assert all(
        vQuestion["choices"][vQuestion["answer"]] == vQuestion["expectedAnswer"]
        for vQuestion in vQuestions
    )
    assert vQuestions[1]["visual"]["path"] == "../assets/schemas/test.svg"
    assert build_questions("grafcet", vConfig, vSource) == vQuestions


def test_build_pack_refuses_a_theme_outside_the_catalog(tmp_path):
    """Vérifie qu'un lot doit appartenir au catalogue des thèmes."""

    write_lot(tmp_path, "theme-inconnu")

    with pytest.raises(ValueError, match="absent du catalogue"):
        build_pack("theme-inconnu", tmp_path)


@pytest.mark.parametrize(
    "pTheme", sorted(vFolder.name for vFolder in LOTS_DIRECTORY.iterdir())
)
def test_every_written_lot_passes_the_quality_check(pTheme):
    """Vérifie que chaque lot du dépôt s'importe en entier, sans alerte."""

    vFileName, vContent = build_pack(pTheme)

    vReport = check_pack(vFileName, vContent)

    assert (vReport["added"], vReport["rejected"]) == (LOT_SIZE, [])
    assert vReport["warnings"] == []
    assert vReport["assets"] == len(
        load_lot(pTheme)[0]["schemas"]
    ), "chaque schéma doit être importé"


def test_main_builds_then_checks_an_archive(tmp_path, monkeypatch, capsys):
    """Vérifie les commandes build et check, et le code de retour d'un lot douteux."""

    monkeypatch.setattr(quiz_lot, "QUIZ_PACKS_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(quiz_lot, "DATABASE_FILE", str(tmp_path / "absente.db"))

    assert main(["build", "grafcet"]) == 0
    assert "Archive écrite" in capsys.readouterr().out

    vArchive = tmp_path / "grafcet-l1-valide.zip"

    assert main(["check", str(vArchive)]) == 0

    vBiased = tmp_path / "biaise.zip"
    vPack = json.loads(
        zipfile.ZipFile(io.BytesIO(vArchive.read_bytes())).read(
            "questions/grafcet.json"
        )
    )

    for vQuestion in vPack["questions"]:
        vQuestion["choices"][vQuestion["answer"]] += " avec une précision superflue"
        vQuestion["expectedAnswer"] = vQuestion["choices"][vQuestion["answer"]]

    with zipfile.ZipFile(vBiased, "w") as vZip:
        vZip.writestr("questions/grafcet.json", json.dumps(vPack))

    assert main(["check", str(vBiased)]) == 1
    assert "la plus longue" in capsys.readouterr().out
