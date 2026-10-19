"""Entraînement à l'oral : questions d'entretien revues par répétition espacée"""

import hashlib
from datetime import timedelta

from job.interview_journal import collect_asked_questions
from job.quiz import LEITNER_INTERVALS
from job.star_answers import (
    BEHAVIORAL_QUESTIONS,
    format_star_answer,
    load_star_answers,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# État de chaque carte : boîte de Leitner et date de la prochaine révision
DRILL_KEY = "interview_drill"


def get_card_id(pQuestion):
    """Retourne l'identifiant stable d'une question, tirée de son texte."""

    rCardId = hashlib.sha256(pQuestion.strip().lower().encode("utf-8")).hexdigest()[:16]

    return rCardId


def build_deck(pDatabaseFile):
    """Retourne les cartes : réponses STAR préparées, puis questions vécues."""

    vCards = {}

    for vKey, vAnswer in load_star_answers(pDatabaseFile).items():
        vQuestion = BEHAVIORAL_QUESTIONS[vKey]
        vCards[get_card_id(vQuestion)] = {
            "question": vQuestion,
            "answer": format_star_answer(vAnswer),
            "origin": "Réponse STAR",
        }

    for vItem in collect_asked_questions(pDatabaseFile):
        vCards.setdefault(
            get_card_id(vItem["question"]),
            {
                "question": vItem["question"],
                "answer": "",
                "origin": f"Posée en entretien : {vItem['context']}",
            },
        )

    rDeck = [{"id": vCardId, **vCard} for vCardId, vCard in vCards.items()]

    return rDeck


def get_due_cards(pDatabaseFile, pNow):
    """Retourne les cartes à revoir maintenant, les jamais vues comprises."""

    vStates = load_json_setting(pDatabaseFile, DRILL_KEY, {}, dict)
    vNow = pNow.isoformat(timespec="seconds")

    rCards = [
        vCard
        for vCard in build_deck(pDatabaseFile)
        if vStates.get(vCard["id"], {}).get("due", "") <= vNow
    ]

    return rCards


def grade_card(pDatabaseFile, pCardId, pKnown, pNow):
    """Note une carte : sue, elle monte d'une boîte ; sinon, elle revient demain."""

    vStates = load_json_setting(pDatabaseFile, DRILL_KEY, {}, dict)
    vBox = vStates.get(pCardId, {}).get("box", 0)

    vBox = min(vBox + 1, len(LEITNER_INTERVALS)) if pKnown else 1
    vStates[pCardId] = {
        "box": vBox,
        "due": (pNow + timedelta(days=LEITNER_INTERVALS[vBox - 1])).isoformat(
            timespec="seconds"
        ),
    }

    save_json_setting(pDatabaseFile, DRILL_KEY, vStates)

    logger.info(
        "Question d'entretien %s : boîte %s", "sue" if pKnown else "à revoir", vBox
    )
