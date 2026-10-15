"""Tests de la demande de questions à ChatGPT et du contrôle des lots importés"""

import json
import re
from datetime import datetime

import pytest

from job.quiz import (
    QUESTION_ID_PATTERN,
    QUIZ_LEVELS,
    flag_question,
    get_flagged_questions,
    load_active_quiz,
    load_quiz,
)
from job.quiz_domains import DOMAIN_ORDER
from job.quiz_generation import (
    MIN_QUALITY_SAMPLE,
    assess_questions,
    build_correction_prompt,
    build_generation_prompt,
    find_catalog_theme,
    get_next_lot,
    list_generation_themes,
    load_catalog,
    split_levels,
)
from job.quiz_import import (
    describe_import_details,
    describe_quiz_import,
    get_import_tone,
    import_questions,
)
from storage.database import initialize_database
from storage.quiz_answers import get_last_answers, save_quiz_answer
from storage.quiz_questions import get_quiz_themes

NOW = datetime(2026, 10, 12, 10, 0)

EXPLANATION = (
    "La bonne réponse décrit le comportement attendu ; les autres choix "
    "confondent deux notions voisines."
)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def build_question(pIndex, pAnswer=0, pLongest=False, pExplanation=EXPLANATION):
    """Construit une question de lot, bonne réponse plus longue ou non."""

    vChoices = ["Réponse A", "Réponse B", "Réponse C", "Réponse D"]

    if pLongest:
        vChoices[pAnswer] = f"Choix plus long et plus précis, variante {pIndex}"

    rQuestion = {
        "id": f"grafcet-l1-{pIndex:03d}",
        "level": QUIZ_LEVELS[pIndex % len(QUIZ_LEVELS)],
        "question": f"Question numéro {pIndex} sur le grafcet ?",
        "choices": vChoices,
        "answer": pAnswer,
        "explanation": pExplanation,
    }

    return rQuestion


def test_catalog_themes_are_unique_and_classified():
    """Vérifie le catalogue : identifiants valides et uniques, classement connu."""

    vCatalog = load_catalog()
    vIds = [vTheme["id"] for vTheme in vCatalog]
    vShipped = load_quiz()

    assert len(vIds) == len(set(vIds))
    assert all(QUESTION_ID_PATTERN.fullmatch(vId) for vId in vIds)
    assert all(
        vTheme["subdomain"] in DOMAIN_ORDER[vTheme["domain"]] for vTheme in vCatalog
    )
    # Un thème livré garde son libellé : ses questions s'y ajoutent sans doublon.
    assert all(
        vTheme["label"] == vShipped[vTheme["id"]]["label"]
        for vTheme in vCatalog
        if vTheme["id"] in vShipped
    )


def test_find_catalog_theme_and_generation_list():
    """Vérifie la recherche dans le catalogue et la liste des thèmes proposés."""

    assert find_catalog_theme("grafcet")["subdomain"] == "Automatisme"
    assert find_catalog_theme("Grafcet et logique séquentielle")["id"] == "grafcet"
    assert find_catalog_theme("Kafka") is None

    vLabels = list_generation_themes(
        [{"key": "java", "label": "Java"}, {"key": "kafka", "label": "Kafka"}]
    )

    assert vLabels.count("Java") == 1
    assert "Kafka" in vLabels
    assert "Grafcet et logique séquentielle" in vLabels
    assert vLabels == sorted(vLabels, key=str.casefold)


def test_get_next_lot():
    """Vérifie le numéro du lot suivant, d'après les identifiants du thème."""

    vQuestions = [
        {"id": "grafcet-l1-001"},
        {"id": "grafcet-l3-010"},
        {"id": "grafcet-etapes"},
        {"id": "autre-l9-001"},
    ]

    assert get_next_lot(vQuestions, "grafcet") == 4
    assert get_next_lot([], "grafcet") == 1


def test_split_levels():
    """Vérifie la répartition par niveau, total conservé malgré les arrondis."""

    assert split_levels("tous", 100) == [
        ("débutant", 25),
        ("intermédiaire", 40),
        ("confirmé", 20),
        ("expert", 15),
    ]
    assert sum(vCount for _, vCount in split_levels("tous", 10)) == 10
    assert sum(vCount for _, vCount in split_levels("tous", 30)) == 30
    assert split_levels("expert", 20) == [("expert", 20)]


def test_prompt_for_catalog_theme():
    """Vérifie la demande d'un thème du catalogue : classement imposé, voisins, lot."""

    vPrompt = build_generation_prompt({}, "grafcet", "tous", 100)

    assert "Thème : Grafcet et logique séquentielle. Lot n° 1." in vPrompt
    assert "100 questions : 25 débutant, 40 intermédiaire, 20 confirmé, 15 expert." in (
        vPrompt
    )
    assert '"domain" et "subdomain" : exactement "Industrie" et "Automatisme".' in (
        vPrompt
    )
    assert "Robotique industrielle" in vPrompt
    assert "- questions/grafcet.json" in vPrompt
    assert '"id": "grafcet-l1-001"' in vPrompt
    assert not re.search(r"\$[a-z_]", vPrompt)


def test_prompt_follows_imported_lots():
    """Vérifie qu'un thème déjà importé reçoit le lot suivant et garde son libellé."""

    vQuiz = {
        "java": {
            "key": "java",
            "label": "Java",
            "skills": ["Java", "JVM"],
            "questions": [{"id": "java-l1-001"}, {"id": "java-l2-004"}],
        }
    }

    vPrompt = build_generation_prompt(vQuiz, "JAVA", "confirmé", 20)

    assert "Thème : Java. Lot n° 3.\n20 questions : 20 confirmé." in vPrompt
    assert '"skills": [\n    "Java",\n    "JVM"\n  ]' in vPrompt
    assert '"java-l3-001"' in vPrompt


def test_prompt_for_new_theme_lets_chatgpt_choose_the_domain():
    """Vérifie qu'un thème hors catalogue et non classé laisse choisir le domaine."""

    vPrompt = build_generation_prompt({}, "Zzz inconnu", "tous", 10)

    assert '"domain": "à choisir (règle 2)"' in vPrompt
    assert "Industrie : Maintenance" in vPrompt
    assert '"compétence 1"' in vPrompt
    assert "Reste dans le périmètre du thème." in vPrompt


def test_prompt_asks_for_explanations_schemas_and_safe_links():
    """Vérifie que la demande exige explications, schémas SVG sûrs et liens officiels."""

    vPrompt = build_generation_prompt({}, "Kafka", "tous", 10)

    assert "pourquoi chacun des autres choix est faux" in vPrompt
    assert "longueur comparable" in vPrompt
    assert "Uniquement du SVG" in vPrompt
    assert "ni raccourcisseur" in vPrompt


def test_assess_questions_flags_a_biased_lot(caplog):
    """Vérifie les alertes d'un lot où la bonne réponse se devine."""

    vQuestions = [
        build_question(vIndex, pAnswer=1, pLongest=True, pExplanation="Court.")
        for vIndex in range(MIN_QUALITY_SAMPLE)
    ]

    vQuality = assess_questions(vQuestions)

    assert vQuality["warnings"] == [
        "bonne réponse la plus longue dans 100 % des questions : elle se devine",
        "bonne réponse en position B dans 100 % des questions",
        "20 explication(s) de moins de 80 caractères",
    ]
    assert vQuality["summary"].startswith(
        "20 question(s), bonne réponse la plus longue 100 %, la plus courte 0 %, "
        "positions A 0 % B 100 %"
    )
    assert "Lot de révision à vérifier" in caplog.text


def test_assess_questions_accepts_a_balanced_or_small_lot():
    """Vérifie qu'un lot équilibré, ou trop petit pour conclure, n'a pas d'alerte."""

    vBalanced = [
        build_question(vIndex, pAnswer=vIndex % 4, pLongest=vIndex % 4 == 0)
        for vIndex in range(MIN_QUALITY_SAMPLE)
    ]
    vSmall = [
        build_question(vIndex, pAnswer=0, pLongest=True, pExplanation="Court.")
        for vIndex in range(MIN_QUALITY_SAMPLE - 1)
    ]

    assert assess_questions(vBalanced)["warnings"] == []
    assert assess_questions(vSmall)["warnings"] == []
    assert "niveaux 5/5/5/5" in assess_questions(vBalanced)["summary"]


def test_pasted_catalog_theme_keeps_its_key_and_reports_quality(database_file):
    """Vérifie l'import collé d'un thème du catalogue : clé, classement et alertes."""

    vText = json.dumps(
        {
            "theme": "Grafcet et logique séquentielle",
            "skills": ["Grafcet"],
            "questions": [
                build_question(vIndex, pAnswer=2, pLongest=True)
                for vIndex in range(1, MIN_QUALITY_SAMPLE + 1)
            ],
        }
    )

    vReport = import_questions(database_file, "", vText, NOW)

    assert vReport["added"] == MIN_QUALITY_SAMPLE
    assert "grafcet" in load_active_quiz(database_file)
    assert get_quiz_themes(database_file)["grafcet"]["domain"] == (
        "Industrie",
        "Automatisme",
    )
    assert get_import_tone(vReport) == "warning"
    assert describe_quiz_import(vReport).endswith("3 alerte(s) de qualité.")

    vDetails = describe_import_details(vReport)

    assert "À vérifier, le lot ne respecte pas la demande :" in vDetails
    assert (
        "- Grafcet et logique séquentielle (lot 1) : bonne réponse en position C"
        in (vDetails)
    )
    assert "Mesures :" in vDetails


def build_lot_text(pQuestions):
    """Construit le JSON d'un lot du thème grafcet."""

    rText = json.dumps(
        {"theme": "Grafcet et logique séquentielle", "questions": pQuestions}
    )

    return rText


def test_corrected_lot_replaces_imported_questions(database_file):
    """Vérifie qu'un lot corrigé remplace ses questions, réponses et schémas gardés."""

    vFirst = build_question(1, pAnswer=1, pLongest=True)
    vFirst["visual"] = {"type": "svg", "path": "../schemas/g.svg", "alt": "Grafcet"}
    import_questions(
        database_file,
        "",
        build_lot_text([vFirst]),
        NOW,
        pVisuals={"../schemas/g.svg": "grafcet.svg"},
    )
    save_quiz_answer(database_file, vFirst["id"], "grafcet", True, NOW)
    flag_question(database_file, vFirst["id"])

    vCorrected = build_question(1, pAnswer=3)
    vCorrected["question"] = "Question corrigée sur le grafcet ?"

    vReport = import_questions(database_file, "", build_lot_text([vCorrected]), NOW)

    vQuestion = load_active_quiz(database_file)["grafcet"]["questions"][0]

    assert (vReport["added"], vReport["replaced"]) == (0, 1)
    assert describe_quiz_import(vReport).startswith(
        "0 question(s) ajoutée(s), 1 remplacée(s)"
    )
    assert vQuestion["question"] == "Question corrigée sur le grafcet ?"
    assert vQuestion["answer"] == 3
    # Le lot corrigé arrive sans ses schémas : celui déjà importé reste.
    assert vQuestion["visual"] == {"asset": "grafcet.svg", "alt": "Grafcet"}
    assert vFirst["id"] not in get_flagged_questions(database_file)
    assert vFirst["id"] in get_last_answers(database_file)


def test_replacement_is_refused_outside_its_theme(database_file):
    """Vérifie les identifiants refusés : question livrée, autre thème, doublon du lot."""

    vShippedId = load_quiz()["java"]["questions"][0]["id"]
    import_questions(
        database_file,
        "",
        json.dumps({"theme": "Kafka", "questions": [build_question(7)]}),
        NOW,
    )

    vReport = import_questions(
        database_file,
        "",
        build_lot_text(
            [
                {**build_question(1), "id": vShippedId},
                build_question(7),
                build_question(2),
                {**build_question(2), "question": "Autre énoncé du grafcet ?"},
            ]
        ),
        NOW,
    )

    assert (vReport["added"], vReport["replaced"]) == (1, 0)
    assert vReport["rejected"] == [
        f"question {vShippedId} : identifiant déjà utilisé",
        "question grafcet-l1-007 : identifiant déjà utilisé",
        "question grafcet-l1-002 : en double dans le lot",
    ]


def test_correction_prompt_lists_flagged_questions(database_file):
    """Vérifie la demande de correction : thème, alertes et questions concernées."""

    vReport = import_questions(
        database_file,
        "",
        build_lot_text(
            [
                build_question(vIndex, pAnswer=vIndex % 4, pLongest=vIndex < 15)
                for vIndex in range(MIN_QUALITY_SAMPLE)
            ]
        ),
        NOW,
    )

    assert [vTheme["key"] for vTheme in vReport["review"]] == ["grafcet"]

    vPrompt = build_correction_prompt(vReport["review"])

    assert (
        "Thème « Grafcet et logique séquentielle », fichier questions/grafcet.json :"
        in vPrompt
    )
    assert "- bonne réponse la plus longue dans 75 % des questions" in vPrompt
    assert "Questions concernées : grafcet-l1-000, grafcet-l1-001" in vPrompt
    assert "grafcet-l1-015" not in vPrompt
    assert not re.search(r"\$[a-z_]", vPrompt)


@pytest.mark.parametrize(
    ("pDomain", "pCode", "pAlert"),
    [
        (("Industrie", "Automatisme"), 0, True),
        (("Informatique", "Développement"), 2, True),
        (("Informatique", "Développement"), 3, False),
        (("Informatique", "Outils et méthodes"), 0, False),
        (("Industrie", "Mécanique et fluides"), 0, False),
        (None, 0, False),
    ],
)
def test_assess_questions_asks_for_concrete_cases(pDomain, pCode, pAlert):
    """Vérifie l'alerte des thèmes techniques sans assez d'extraits de code."""

    vQuestions = [
        build_question(vIndex, pAnswer=vIndex % 4)
        for vIndex in range(MIN_QUALITY_SAMPLE)
    ]

    for vQuestion in vQuestions[:pCode]:
        vQuestion["code"] = "IF Marche THEN Moteur := TRUE; END_IF;"
        vQuestion["question"] = f"Que fait cet extrait n° {vQuestion['id']} ?"

    vQuality = assess_questions(vQuestions, pDomain)
    vAlerts = [vWarning for vWarning, _ in vQuality["issues"] if "concrets" in vWarning]

    assert vAlerts == (
        [f"{pCode} question(s) avec code sur 20 : moins de 15 % de cas concrets"]
        if pAlert
        else []
    )

    if pAlert:
        vPrompt = build_correction_prompt(
            [{"key": "grafcet", "label": "Grafcet", "issues": vQuality["issues"]}]
        )

        # L'alerte porte sur tout le lot : aucune question n'est citée.
        assert f"- {vAlerts[0]}\n" in vPrompt
        assert "Questions concernées" not in vPrompt
        assert "pas assez de cas concrets (règle 7)" in vPrompt


def test_assess_questions_flags_truncated_choices_and_unrelated_code():
    """Vérifie les alertes des choix tronqués et des extraits que l'énoncé ignore."""

    vQuestions = [build_question(vIndex, pAnswer=vIndex % 4) for vIndex in range(4)]
    vQuestions[0]["choices"][2] = "Quand elle est validée et que sa…"
    vQuestions[1]["choices"][0] = "Une condition logique de..."

    for vQuestion in vQuestions[:3]:
        vQuestion["code"] = "S1 := FALSE;"

    vQuestions[2]["question"] = "Que fait cet extrait ?"

    assert assess_questions(vQuestions)["issues"] == [
        (
            "2 question(s) aux choix coupés par « … »",
            ["grafcet-l1-000", "grafcet-l1-001"],
        ),
        (
            "2 extrait(s) de code que l'énoncé ne cite pas",
            ["grafcet-l1-000", "grafcet-l1-001"],
        ),
    ]


def test_assess_questions_flags_shortest_answers_and_filler():
    """Vérifie les alertes de réponse la plus courte et de fins de choix répétées."""

    vQuestions = []

    for vIndex in range(MIN_QUALITY_SAMPLE):
        vQuestion = build_question(vIndex, pAnswer=vIndex % 4)
        vQuestion["choices"] = [
            f"Une proposition détaillée numéro {vPosition} dans ce cas"
            for vPosition in range(4)
        ]
        vQuestion["choices"][vIndex % 4] = f"Court {vIndex}"
        vQuestions.append(vQuestion)

    vWarnings = assess_questions(vQuestions)["warnings"]

    assert vWarnings == [
        "bonne réponse la plus courte dans 100 % des questions : elle se devine",
        "60 choix finissent par « dans ce cas » : remplissage probable",
    ]


def test_lot_delivered_in_several_archives_is_assessed_as_a_whole(database_file):
    """Vérifie qu'un lot livré en tranches de 10 questions est mesuré en entier."""

    vTranches = [
        build_lot_text(
            [
                build_question(vIndex, pAnswer=1, pLongest=True)
                for vIndex in range(vStart, vStart + 10)
            ]
        )
        for vStart in (0, 10)
    ]

    vFirst = import_questions(database_file, "", vTranches[0], NOW)
    vSecond = import_questions(database_file, "", vTranches[1], NOW)

    assert vFirst["warnings"] == []
    assert vSecond["quality"][0].startswith(
        "Grafcet et logique séquentielle (lot 1) : 20 question(s)"
    )
    assert "bonne réponse la plus longue dans 100 %" in vSecond["warnings"][0]


def test_unknown_domain_and_outside_catalog_theme_are_reported(database_file):
    """Vérifie l'alerte d'un domaine inventé et la note d'un thème hors catalogue."""

    vText = json.dumps(
        {
            "theme": "Kafka",
            "domain": "Informatique",
            "subdomain": "Backend",
            "questions": [build_question(1)],
        }
    )

    vReport = import_questions(database_file, "", vText, NOW)

    assert vReport["warnings"] == [
        "Kafka : domaine « Informatique / Backend » inconnu : "
        "le thème a été classé par mots-clés"
    ]
    assert vReport["notes"] == ["Kafka"]
    assert "Hors catalogue, à ajouter au catalogue si le thème doit durer : Kafka." in (
        describe_import_details(vReport)
    )
