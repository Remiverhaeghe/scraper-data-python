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
    collect_references,
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


def test_references_are_read_and_built(tmp_path):
    """Vérifie les références du format compact et leur place dans la question."""

    vQuestions = parse_lot_text(
        QUESTION_TEXT.replace(
            "E: Explication détaillée de la notion et des erreurs courantes du "
            "candidat.\n```",
            "E: Explication détaillée de la notion et des erreurs courantes du "
            "candidat.\nR: Documentation | https://docs.example.org/page\n```",
            1,
        )
    )

    assert vQuestions["001"]["R"] == ["Documentation | https://docs.example.org/page"]

    with pytest.raises(ValueError, match="référence mal écrite"):
        parse_lot_text(
            QUESTION_TEXT.replace(
                "E: Explication", "R: sans adresse\nE: Explication", 1
            )
        )

    write_lot(tmp_path, "grafcet")
    vConfig, vSource = load_lot("grafcet", tmp_path)
    vSource["001"]["R"] = ["Guide | https://docs.example.org/guide"]

    assert build_questions("grafcet", vConfig, vSource)[0]["references"] == [
        {"title": "Guide", "url": "https://docs.example.org/guide"}
    ]


def test_links_command_reports_removed_pages(tmp_path, monkeypatch, capsys):
    """Vérifie la vérification des références d'une archive, sans réseau."""

    vQuestions = [
        {"id": "q1", "references": [{"title": "A", "url": "https://a.example.org"}]},
        {"id": "q2", "references": [{"title": "B", "url": "https://b.example.org"}]},
        {"id": "q3", "references": [{"title": "A", "url": "https://a.example.org"}]},
    ]
    vArchive = tmp_path / "lot.zip"

    with zipfile.ZipFile(vArchive, "w") as vZip:
        vZip.writestr("questions/lot.json", json.dumps({"questions": vQuestions}))

    assert collect_references(vQuestions) == {
        "https://a.example.org": ["q1", "q3"],
        "https://b.example.org": ["q2"],
    }

    vStatuses = {
        "https://a.example.org": "available",
        "https://b.example.org": "expired",
    }
    monkeypatch.setattr(quiz_lot, "check_offer_link", vStatuses.get)

    assert main(["links", str(vArchive)]) == 1

    vLines = capsys.readouterr().out.splitlines()

    assert vLines == [
        "2 référence(s), 1 retirée(s)",
        "retirée : https://b.example.org (q2)",
        "en ligne : https://a.example.org (q1, q3)",
    ]

    monkeypatch.setattr(quiz_lot, "check_offer_link", lambda _: None)

    assert main(["links", "grafcet"]) == 0


TYPED_TEXT = """@001
Q: Courant dans 100 ohms sous 0,23 V ?
N: 0,0023
U: A
T: 2
E: I = U / R.

@002
Q: Ordre de la consignation ?
O: Séparer
O: Condamner
O: Vérifier
E: Dans cet ordre.

@003
Q: Associer grandeur et unité.
P: Tension => V
P: Courant => A
P: Puissance => W
E: Volt, ampère, watt.

@004
Q: Compléter la boucle.
A: length
A: length()
E: Un tableau expose length.
```
for (int i = 0; i < tab.____; i++) {}
```
"""


def test_typed_questions_are_read_and_built():
    """Vérifie la lecture et la construction des questions qui ne sont pas des QCM."""

    vSource = parse_lot_text(TYPED_TEXT)
    vQuestions = build_questions(
        "electricite", {"lot": 1, "seed": 3}, {**vSource, "005": vSource["004"]}
    )

    assert [vQuestion["type"] for vQuestion in vQuestions] == [
        "numerique",
        "ordre",
        "association",
        "saisie",
        "saisie",
    ]
    assert (vQuestions[0]["value"], vQuestions[0]["unit"]) == (0.0023, "A")
    assert vQuestions[0]["tolerance"] == 2.0
    assert vQuestions[1]["items"] == ["Séparer", "Condamner", "Vérifier"]
    assert vQuestions[2]["pairs"][0] == ["Tension", "V"]
    assert vQuestions[3]["accepted"] == ["length", "length()"]
    assert "choices" not in vQuestions[3]


@pytest.mark.parametrize(
    ("pText", "pMessage"),
    [
        ("@001\nQ: Ordre ?\nO: A\nO: B\nW: C\nE: Explication.", "champs incomplets"),
        ("@001\nQ: Paires ?\nP: A -> 1\nE: Explication.", "paire mal écrite"),
    ],
)
def test_typed_questions_refuse_mixed_or_malformed_fields(pText, pMessage):
    """Vérifie le refus d'un type mêlé à des choix ou d'une paire mal écrite."""

    with pytest.raises(ValueError, match=pMessage):
        parse_lot_text(pText)


def test_zone_question_is_read_and_built():
    """Vérifie la lecture d'une zone à désigner et le refus d'une zone mal écrite."""

    vSource = parse_lot_text(
        "@001\nQ: Cliquez sur le fusible.\nK: Fusible | 55 45 50 140\n"
        "Z: Moteur | 515 45 70 140\nE: Le fusible est un rectangle traversé.\n"
    )
    vQuestion = build_questions("electricite", {"lot": 1, "seed": 3}, vSource)[0]

    assert vQuestion["type"] == "zone" and vQuestion["answer"] == 0
    assert vQuestion["zones"][1] == {
        "label": "Moteur",
        "rect": [515.0, 45.0, 70.0, 140.0],
    }

    for vText in (
        "@001\nQ: Zone ?\nK: Fusible 55 45 50 140\nE: Explication.",
        "@001\nQ: Zone ?\nK: Fusible | 55 45 50\nE: Explication.",
    ):
        with pytest.raises(ValueError, match="zone mal écrite"):
            parse_lot_text(vText)

    with pytest.raises(ValueError, match="champs incomplets"):
        parse_lot_text(
            "@001\nQ: Ordre ?\nO: A\nO: B\nO: C\nZ: Moteur | 1 1 2 2\nE: Explication."
        )


def test_construction_question_is_read_and_built():
    """Vérifie la lecture d'un schéma à construire et le refus d'un schéma mal écrit."""

    vSource = parse_lot_text(
        "@001\nQ: Construire.\nS: reseau @ 0 0\nS: fusible @ 0 1\n"
        "L: reseau.sortie - fusible.1\nD: moteur\nE: Le fusible protège la ligne.\n"
    )
    vQuestion = build_questions("electricite", {"lot": 1, "seed": 3}, vSource)[0]

    assert vQuestion["type"] == "construction"
    assert vQuestion["components"][1] == {"type": "fusible", "x": 0, "y": 1}
    assert vQuestion["connections"] == [["reseau", "sortie", "fusible", "1"]]
    assert vQuestion["distractors"] == ["moteur"]

    for vText in (
        "@001\nQ: Construire.\nS: reseau 0 0\nL: reseau.sortie - fusible.1\nE: E.",
        "@001\nQ: Construire.\nS: reseau @ 0 0\nE: Explication.",
        "@001\nQ: Construire.\nS: reseau @ 0 0\nL: reseau sortie fusible 1\nE: E.",
    ):
        with pytest.raises(ValueError, match="schéma mal écrit"):
            parse_lot_text(vText)

    with pytest.raises(ValueError, match="champs incomplets"):
        parse_lot_text("@001\nQ: QCM ?\nC: Oui\nW: A\nW: B\nW: C\nD: moteur\nE: E.")
