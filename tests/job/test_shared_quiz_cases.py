"""Cas de correction et de répétition espacée communs au serveur et au téléphone"""

import json
from datetime import date
from pathlib import Path

import pytest

from job.quiz import build_review_schedule
from job.quiz_types import grade_answer

CASES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "fixtures" / "shared_quiz_cases.json"
    ).read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    "pCase", CASES["grading"], ids=[vCase["name"] for vCase in CASES["grading"]]
)
def test_shared_grading_case(pCase):
    """Vérifie la correction attendue, la même que dans mobile/lib/logic/grading.dart."""

    if pCase.get("error"):
        with pytest.raises(ValueError):
            grade_answer(pCase["question"], pCase["response"])
    else:
        vCorrect, _, vExpected = grade_answer(pCase["question"], pCase["response"])

        assert (vCorrect, vExpected) == (pCase["correct"], pCase["expected"])


@pytest.mark.parametrize(
    "pCase", CASES["review"], ids=[vCase["name"] for vCase in CASES["review"]]
)
def test_shared_review_case(pCase):
    """Vérifie la boîte et la date attendues, les mêmes que dans mobile/lib/logic/review.dart."""

    vSchedule = build_review_schedule(
        [
            ("question", vCorrect, vAnsweredAt)
            for vCorrect, vAnsweredAt in pCase["answers"]
        ]
    )

    assert vSchedule["question"] == {
        "box": pCase["box"],
        "due": date.fromisoformat(pCase["due"]),
    }
