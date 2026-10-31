"""Tests du thème Anglais technique : contenu, classement et détection dans les offres"""

from job.enrichment import detect_skills
from job.quiz import load_quiz
from job.quiz_domains import classify_theme
from job.quiz_types import BLANK, get_type, grade_answer

THEME = "anglais-technique"


def test_each_term_is_asked_both_ways():
    """Vérifie un QCM et une phrase à compléter par terme, plus les associations."""

    vQuestions = load_quiz()[THEME]["questions"]
    vTypes = [get_type(vQuestion) for vQuestion in vQuestions]

    assert vTypes.count("qcm") == vTypes.count("saisie") == 72
    assert vTypes.count("association") == 18
    assert len({vQuestion["id"] for vQuestion in vQuestions}) == len(vQuestions)


def test_sentence_accepts_the_word_with_or_without_capital():
    """Vérifie chaque phrase à trou : un seul trou, le mot attendu accepté."""

    for vQuestion in load_quiz()[THEME]["questions"]:
        if get_type(vQuestion) == "saisie":
            assert vQuestion["code"].count(BLANK) == 1
            assert all(
                grade_answer(vQuestion, vAccepted)[0]
                for vAccepted in vQuestion["accepted"]
            )

    vBearing = next(
        vQuestion
        for vQuestion in load_quiz()[THEME]["questions"]
        if vQuestion["id"] == "anglais-meca-bearing-phrase"
    )

    assert grade_answer(vBearing, "Bearing")[0]
    assert not grade_answer(vBearing, "roulement")[0]


def test_false_friends_offer_the_trap():
    """Vérifie que le QCM d'un faux ami propose le piège parmi les choix."""

    vActually = next(
        vQuestion
        for vQuestion in load_quiz()[THEME]["questions"]
        if vQuestion["id"] == "anglais-fauxamis-actually-sens"
    )

    assert "actuellement" in vActually["choices"]
    assert vActually["choices"][vActually["answer"]] == "en fait"


def test_theme_is_classified_and_english_is_detected_in_offers():
    """Vérifie le domaine Langues et l'anglais repéré dans une annonce."""

    vTheme = load_quiz()[THEME]

    assert classify_theme(vTheme["label"], vTheme["skills"]) == (
        "Langues",
        "Anglais technique",
    )
    assert "Anglais" in detect_skills("Anglais technique apprécié")
    assert "Anglais" in detect_skills("Fluent English required")
    assert "Anglais" not in detect_skills("Technicien de maintenance, GMAO")
