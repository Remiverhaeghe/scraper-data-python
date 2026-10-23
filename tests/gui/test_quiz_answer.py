"""Tests des saisies de réponse de la révision"""

import random

from PySide6.QtWidgets import QButtonGroup, QVBoxLayout, QWidget

from gui.quiz_answer import add_answer_widgets, read_response
from job.quiz_types import prepare_question
from tests.job.test_quiz_types import REVIEW


def test_code_review_answer_reads_the_checked_findings(qt_application):
    """Vérifie les cases d'une revue de code et les indices d'origine renvoyés."""

    vQuestion = prepare_question(REVIEW, random.Random(1))
    vContainer = QWidget()
    vLayout = QVBoxLayout(vContainer)
    vWidgets = add_answer_widgets(vQuestion, vLayout, QButtonGroup(), lambda: None)

    assert len(vWidgets) == 3
    assert read_response(vQuestion, vWidgets, None, None) is None

    for vCheck in vWidgets:
        vCheck.setChecked(vCheck.property("choice_index") in (0, 2))

    assert sorted(read_response(vQuestion, vWidgets, None, None)) == [0, 2]
