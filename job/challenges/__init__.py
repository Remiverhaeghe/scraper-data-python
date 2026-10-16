"""Défis de programmation : énoncé, données personnelles et réponse à trouver

Chaque défi est un module qui fournit son énoncé en deux parties, un exemple, des
indices, une note de solution, un générateur de données et sa solution de
référence. On résout un défi avec son propre code, dans le langage de son choix :
l'application ne vérifie que la réponse et n'exécute jamais de code saisi.
"""

import random
import secrets
from datetime import datetime, timedelta
from functools import lru_cache

from job.challenges import (
    arrets_ligne,
    chemin_atelier,
    courbe_charge,
    demarrages_moteur,
    engrenages,
    grafcet_rejeu,
    journal_http,
    mesures_4_20,
    pieces_bonnes,
    sous_reseaux,
    tampon_production,
    tracabilite_lots,
    trames_modbus,
)
from job.settings import load_settings
from storage.challenges import (
    get_challenge_attempts,
    get_challenge_seed,
    save_challenge_attempt,
)

# Ordre d'affichage : du plus accessible au plus difficile
CHALLENGES = (
    arrets_ligne,
    pieces_bonnes,
    journal_http,
    demarrages_moteur,
    tampon_production,
    mesures_4_20,
    courbe_charge,
    sous_reseaux,
    grafcet_rejeu,
    engrenages,
    chemin_atelier,
    tracabilite_lots,
    trames_modbus,
)
PARTS = (1, 2)

# Icône de chaque série, et icône des niveaux dans l'ordre de difficulté
SERIES_ICONS = {
    "Algorithmique": "code",
    "Automatisme": "cpu",
    "Électricité": "zap",
    "Exploitation": "server",
    "Industrie": "settings",
    "Instrumentation": "timer",
    "Maintenance": "wrench",
    "Mathématiques": "scale",
    "Réseau": "network",
    "Réseaux industriels": "network",
}
LEVEL_ICONS = {
    "débutant": "sparkles",
    "intermédiaire": "zap",
    "confirmé": "trophy",
}

MAX_SEED = 2**31


def get_challenge(pChallengeId):
    """Retourne le module d'un défi, ou None s'il n'existe pas."""

    rChallenge = next(
        (vChallenge for vChallenge in CHALLENGES if vChallenge.ID == pChallengeId),
        None,
    )

    return rChallenge


@lru_cache(maxsize=64)
def generate_input(pChallengeId, pSeed):
    """Retourne les données d'un défi pour une graine ; mémorisées entre deux appels."""

    # Tirage reproductible de données d'exercice, sans usage cryptographique.
    vRandom = random.Random(pSeed)  # nosec B311
    rInput = get_challenge(pChallengeId).generate(vRandom)

    return rInput


@lru_cache(maxsize=64)
def get_expected_answers(pChallengeId, pSeed):
    """Retourne les réponses attendues d'un défi pour une graine."""

    rAnswers = get_challenge(pChallengeId).solve(generate_input(pChallengeId, pSeed))

    return rAnswers


def get_seed(pDatabaseFile, pChallengeId, pNow):
    """Retourne la graine des données personnelles d'un défi, créée au premier accès."""

    rSeed = get_challenge_seed(
        pDatabaseFile, pChallengeId, secrets.randbelow(MAX_SEED), pNow
    )

    return rSeed


def get_challenge_input(pDatabaseFile, pChallengeId, pNow):
    """Retourne les données personnelles d'un défi."""

    rInput = generate_input(pChallengeId, get_seed(pDatabaseFile, pChallengeId, pNow))

    return rInput


def normalize_answer(pAnswer):
    """Retourne une réponse comparable : espaces réduits, casse ignorée."""

    rAnswer = " ".join(str(pAnswer).split()).casefold()

    return rAnswer


def build_progress(pDatabaseFile, pNow):
    """Retourne, par défi, les parties réussies, le nombre d'essais et l'attente."""

    vDelay = get_wrong_answer_delay(pDatabaseFile)
    rProgress = {
        vChallenge.ID: {"solved": set(), "attempts": 0, "wait_until": {}}
        for vChallenge in CHALLENGES
    }

    for vChallengeId, vPart, _, vCorrect, vAnsweredAt in get_challenge_attempts(
        pDatabaseFile
    ):
        vProgress = rProgress.get(vChallengeId)

        if vProgress is None:
            continue

        vProgress["attempts"] += 1

        if vCorrect:
            vProgress["solved"].add(vPart)
        else:
            vProgress["wait_until"][vPart] = (
                datetime.fromisoformat(vAnsweredAt) + vDelay
            )

    for vProgress in rProgress.values():
        vProgress["wait_until"] = {
            vPart: vUntil
            for vPart, vUntil in vProgress["wait_until"].items()
            if vUntil > pNow and vPart not in vProgress["solved"]
        }

    return rProgress


def get_wrong_answer_delay(pDatabaseFile):
    """Retourne l'attente imposée après une réponse fausse, réglable mais jamais nulle."""

    rDelay = timedelta(seconds=load_settings(pDatabaseFile)["challenge_wait_seconds"])

    return rDelay


def compare_numbers(pAnswer, pExpected):
    """Retourne « trop haute » ou « trop basse » pour deux nombres entiers, sinon ""."""

    try:
        vAnswer, vExpected = int(pAnswer), int(pExpected)

    except ValueError:
        return ""

    rHint = " Elle est trop haute." if vAnswer > vExpected else " Elle est trop basse."

    return rHint


def submit_answer(pDatabaseFile, pChallengeId, pPart, pAnswer, pNow):
    """Vérifie une réponse ; retourne (juste, message, couleur du message).

    Lève ValueError si le défi ou la partie n'existe pas, ou si la réponse est
    vide. Une partie déjà réussie, verrouillée ou en attente n'enregistre rien.
    """

    vChallenge = get_challenge(pChallengeId)
    vAnswer = str(pAnswer or "").strip()

    if vChallenge is None or pPart not in PARTS:
        raise ValueError("Défi inconnu.")

    if not vAnswer:
        raise ValueError("Saisissez une réponse.")

    vProgress = build_progress(pDatabaseFile, pNow)[pChallengeId]

    if pPart in vProgress["solved"]:
        return (True, "Cette partie est déjà réussie.", "success")

    if pPart == 2 and 1 not in vProgress["solved"]:
        return (False, "Réussissez d'abord la première partie.", "warning")

    if pPart in vProgress["wait_until"]:
        vSeconds = int((vProgress["wait_until"][pPart] - pNow).total_seconds()) + 1

        return (False, f"Patientez encore {vSeconds} s avant de réessayer.", "warning")

    vExpected = get_expected_answers(
        pChallengeId, get_seed(pDatabaseFile, pChallengeId, pNow)
    )[pPart - 1]
    vCorrect = normalize_answer(vAnswer) == normalize_answer(vExpected)

    save_challenge_attempt(
        pDatabaseFile, pChallengeId, pPart, vAnswer[:200], vCorrect, pNow
    )

    if vCorrect:
        rResult = (
            True,
            (
                "Bonne réponse : première étoile gagnée, la seconde partie est ouverte."
                if pPart == 1
                else "Bonne réponse : défi terminé, la solution commentée est ouverte."
            ),
            "success",
        )
    else:
        rResult = (
            False,
            "Ce n'est pas la bonne réponse."
            + compare_numbers(vAnswer, vExpected)
            + " Nouvel essai possible dans "
            + f"{int(get_wrong_answer_delay(pDatabaseFile).total_seconds())} s.",
            "danger",
        )

    return rResult


def build_challenge_list(pDatabaseFile, pNow):
    """Retourne les défis à afficher, avec leurs étoiles et leur nombre d'essais."""

    vProgress = build_progress(pDatabaseFile, pNow)

    rChallenges = [
        {
            "id": vChallenge.ID,
            "title": vChallenge.TITLE,
            "series": vChallenge.SERIES,
            "level": vChallenge.LEVEL,
            "icon": SERIES_ICONS.get(vChallenge.SERIES, "trophy"),
            "stars": len(vProgress[vChallenge.ID]["solved"]),
            "attempts": vProgress[vChallenge.ID]["attempts"],
        }
        for vChallenge in CHALLENGES
    ]

    return rChallenges


def group_challenges(pChallenges):
    """Regroupe les défis par niveau de difficulté, du plus facile au plus dur."""

    rGroups = [
        {
            "label": vLevel,
            "icon": vIcon,
            "challenges": vChallenges,
            "done": sum(1 for vItem in vChallenges if vItem["stars"] == len(PARTS)),
        }
        for vLevel, vIcon in LEVEL_ICONS.items()
        if (vChallenges := [vItem for vItem in pChallenges if vItem["level"] == vLevel])
    ]

    return rGroups


def build_challenge_view(pDatabaseFile, pChallengeId, pNow):
    """Retourne ce qu'affiche la page d'un défi, selon les parties déjà réussies.

    La seconde partie n'apparaît qu'après la première ; la note de solution,
    qu'une fois le défi terminé. Lève ValueError si le défi n'existe pas.
    """

    vChallenge = get_challenge(pChallengeId)

    if vChallenge is None:
        raise ValueError("Défi inconnu.")

    vSolved = build_progress(pDatabaseFile, pNow)[pChallengeId]["solved"]

    rView = {
        "id": vChallenge.ID,
        "title": vChallenge.TITLE,
        "series": vChallenge.SERIES,
        "level": vChallenge.LEVEL,
        "statements": vChallenge.STATEMENTS[: 2 if 1 in vSolved else 1],
        "example": vChallenge.EXAMPLE,
        "example_answers": vChallenge.EXAMPLE_ANSWERS[: 2 if 1 in vSolved else 1],
        "hints": vChallenge.HINTS,
        "note": vChallenge.NOTE if {1, 2} <= vSolved else "",
        "solved": vSolved,
        "next_part": next((vPart for vPart in PARTS if vPart not in vSolved), None),
    }

    return rView
