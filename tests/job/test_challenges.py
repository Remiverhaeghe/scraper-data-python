"""Tests des défis de programmation : énoncés, données, solutions et réponses"""

import random
from datetime import datetime, timedelta

import pytest

from job.challenges import (
    CHALLENGES,
    build_challenge_list,
    build_challenge_view,
    build_progress,
    get_challenge_input,
    get_expected_answers,
    get_seed,
    submit_answer,
)
from job.settings import save_settings
from storage.challenges import save_challenge_attempt
from storage.database import initialize_database

NOW = datetime(2026, 10, 15, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def expected(pDatabaseFile, pChallengeId):
    """Retourne les réponses attendues des données personnelles d'un défi."""

    rAnswers = get_expected_answers(
        pChallengeId, get_seed(pDatabaseFile, pChallengeId, NOW)
    )

    return rAnswers


@pytest.mark.parametrize("pChallenge", CHALLENGES, ids=lambda pModule: pModule.ID)
def test_challenge_is_complete_and_solvable(pChallenge):
    """Vérifie un défi : contenu complet, exemple juste et données reproductibles."""

    assert pChallenge.TITLE and pChallenge.SERIES and pChallenge.LEVEL
    assert len(pChallenge.STATEMENTS) == 2
    assert pChallenge.HINTS and pChallenge.NOTE
    assert pChallenge.solve(pChallenge.EXAMPLE) == pChallenge.EXAMPLE_ANSWERS

    vInput = pChallenge.generate(random.Random(7))
    vAnswers = pChallenge.solve(vInput)

    assert vInput == pChallenge.generate(random.Random(7))
    assert vInput != pChallenge.generate(random.Random(8))
    assert len(vAnswers) == 2 and all(vAnswers)
    # Des données bien plus grandes que l'exemple : on ne les résout pas à la main.
    assert len(vInput) > 3 * len(pChallenge.EXAMPLE)


def test_challenge_identifiers_are_unique():
    """Vérifie que deux défis ne partagent pas le même identifiant."""

    vIds = [vChallenge.ID for vChallenge in CHALLENGES]

    assert len(vIds) == len(set(vIds))


def test_personal_input_stays_the_same(database_file):
    """Vérifie que les données d'un défi ne changent pas d'un appel à l'autre."""

    vFirst = get_challenge_input(database_file, "engrenages", NOW)

    assert get_challenge_input(database_file, "engrenages", NOW) == vFirst
    assert get_challenge_input(database_file, "sous-reseaux", NOW) != vFirst


def test_answers_unlock_parts_and_wait_after_a_mistake(database_file):
    """Vérifie le parcours d'un défi : verrou, erreur, attente, puis réussite."""

    vFirst, vSecond = expected(database_file, "engrenages")

    assert submit_answer(database_file, "engrenages", 2, vSecond, NOW) == (
        False,
        "Réussissez d'abord la première partie.",
        "warning",
    )

    vCorrect, vMessage, vTone = submit_answer(
        database_file, "engrenages", 1, str(int(vFirst) + 1), NOW
    )

    assert (vCorrect, vTone) == (False, "danger")
    assert "Elle est trop haute." in vMessage

    vLater = NOW + timedelta(seconds=10)

    assert submit_answer(database_file, "engrenages", 1, vFirst, vLater)[1] == (
        "Patientez encore 21 s avant de réessayer."
    )

    vAfter = NOW + timedelta(seconds=30)

    assert submit_answer(database_file, "engrenages", 1, f" {vFirst} ", vAfter)[0]
    assert build_challenge_view(database_file, "engrenages", vAfter)["note"] == ""
    assert submit_answer(database_file, "engrenages", 2, vSecond, vAfter)[0]

    vView = build_challenge_view(database_file, "engrenages", vAfter)

    assert vView["next_part"] is None
    assert vView["note"].startswith("Après t tours")
    assert submit_answer(database_file, "engrenages", 2, "0", vAfter) == (
        True,
        "Cette partie est déjà réussie.",
        "success",
    )


def test_wrong_answer_delay_follows_the_setting(database_file):
    """Vérifie que l'attente après une erreur suit le réglage, sans jamais être nulle."""

    vFirst, _ = expected(database_file, "engrenages")
    save_settings(database_file, {"challenge_wait_seconds": "5"})

    vMessage = submit_answer(database_file, "engrenages", 1, "0", NOW)[1]

    assert vMessage.endswith("Nouvel essai possible dans 5 s.")
    assert submit_answer(
        database_file, "engrenages", 1, vFirst, NOW + timedelta(seconds=5)
    )[0]

    with pytest.raises(ValueError, match="entre 5 et 600"):
        save_settings(database_file, {"challenge_wait_seconds": "0"})


def test_text_answers_ignore_case_and_spaces(database_file):
    """Vérifie qu'une réponse texte se compare sans la casse ni les espaces."""

    vFirst, vSecond = expected(database_file, "arrets-ligne")
    submit_answer(database_file, "arrets-ligne", 1, vFirst, NOW)

    vCorrect, vMessage, _ = submit_answer(
        database_file, "arrets-ligne", 2, f"  {vSecond.upper()}  ", NOW
    )

    assert vCorrect, vMessage

    vWrong = submit_answer(database_file, "pieces-bonnes", 1, "beaucoup", NOW)

    assert vWrong[1].startswith("Ce n'est pas la bonne réponse. Nouvel essai")


@pytest.mark.parametrize(
    ("pChallengeId", "pPart", "pAnswer", "pMessage"),
    [
        ("inconnu", 1, "1", "Défi inconnu."),
        ("engrenages", 3, "1", "Défi inconnu."),
        ("engrenages", 1, "   ", "Saisissez une réponse."),
    ],
)
def test_submit_answer_refuses_bad_requests(
    database_file, pChallengeId, pPart, pAnswer, pMessage
):
    """Vérifie le refus d'un défi inconnu, d'une partie inconnue et d'une réponse vide."""

    with pytest.raises(ValueError, match=pMessage):
        submit_answer(database_file, pChallengeId, pPart, pAnswer, NOW)


def test_list_and_progress_follow_the_attempts(database_file):
    """Vérifie les étoiles, les essais et l'oubli d'un défi qui n'existe plus."""

    save_challenge_attempt(database_file, "ancien-defi", 1, "1", True, NOW)
    save_challenge_attempt(database_file, "tampon-production", 1, "1", True, NOW)
    save_challenge_attempt(database_file, "tampon-production", 2, "9", False, NOW)

    vList = {vItem["id"]: vItem for vItem in build_challenge_list(database_file, NOW)}
    vProgress = build_progress(database_file, NOW)

    assert "ancien-defi" not in vList
    assert (
        vList["tampon-production"]["stars"],
        vList["tampon-production"]["attempts"],
    ) == (1, 2)
    assert 2 in vProgress["tampon-production"]["wait_until"]

    with pytest.raises(ValueError, match="Défi inconnu"):
        build_challenge_view(database_file, "ancien-defi", NOW)
