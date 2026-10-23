"""Tests des réponses de recruteurs repérées dans Gmail"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import job.application_replies as application_replies
from job.application_replies import (
    apply_reply,
    build_reply_id,
    classify_reply,
    find_interview_date,
    find_replies,
    load_pending_replies,
    mark_reply_handled,
    run_due_reply_check,
)
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import save_offers
from utils.mail_reader import parse_message

NOW = datetime(2026, 10, 23, 12, 0)


def build_message(pId, pSender, pSubject, pText=""):
    """Construit un message lu, au format de utils/mail_reader.py."""

    rMessage = {
        "message_id": pId,
        "sender": pSender,
        "subject": pSubject,
        "date": NOW,
        "text": pText,
    }

    return rMessage


@pytest.mark.parametrize(
    ("pText", "pExpected"),
    [
        ("Malheureusement, nous ne pouvons pas donner suite", "REJECTED"),
        ("Suite à notre entretien, nous regrettons de vous informer", "REJECTED"),
        ("Unfortunately we are not moving forward", "REJECTED"),
        (
            "Pourriez-vous nous indiquer vos disponibilités pour un entretien ?",
            "INTERVIEW",
        ),
        (
            "Nous avons bien reçu votre candidature et vous contacterons pour un "
            "éventuel entretien",
            None,
        ),
        ("Votre newsletter de la semaine", None),
    ],
)
def test_reply_is_classified(pText, pExpected):
    """Vérifie le statut annoncé : refus d'abord, accusé de réception ignoré."""

    assert classify_reply(pText) == pExpected


@pytest.fixture(name="database_file")
def fixture_database_file(tmp_path):
    """Crée une base avec une candidature envoyée chez Kiabi, notes comprises."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "smartrecruiters",
                    "source_id": "1",
                    "title": "Dev Java",
                    "company": "Kiabi",
                },
                {
                    "source": "smartrecruiters",
                    "source_id": "2",
                    "title": "Dev PHP",
                    "company": "Boulanger",
                },
            ]
        ),
        NOW,
    )
    save_application(
        rDatabaseFile, "smartrecruiters", "1", "APPLIED", pNotes="Relancer RH"
    )
    save_application(rDatabaseFile, "smartrecruiters", "2", "INTERESTED")

    return rDatabaseFile


def test_replies_are_matched_then_applied_once(database_file):
    """Vérifie le rapprochement par l'entreprise, l'application et l'oubli du message."""

    vMessages = [
        build_message(
            "<1>",
            "Recrutement <jobs@kiabi.com>",
            "Votre candidature",
            "Malheureusement...",
        ),
        build_message(
            "<2>", "Boulanger <rh@boulanger.com>", "Entretien", "vos disponibilités"
        ),
        build_message(
            "<3>", "Newsletter <info@exemple.fr>", "Promotions", "entretien de jardin"
        ),
    ]

    vReplies = find_replies(database_file, vMessages)

    # Boulanger : candidature seulement « Intéressé », aucune réponse attendue.
    assert [(vReply["company"], vReply["status"]) for vReply in vReplies] == [
        ("Kiabi", "REJECTED")
    ]

    apply_reply(database_file, vReplies[0], NOW)
    vApplication = get_application(database_file, "smartrecruiters", "1")

    assert vApplication["status"] == "REJECTED"
    assert vApplication["notes"] == "Relancer RH"
    assert find_replies(database_file, vMessages) == []


def test_ignored_reply_is_not_proposed_again(database_file):
    """Vérifie qu'un message ignoré n'est plus proposé."""

    vMessage = build_message("<4>", "Kiabi <rh@kiabi.com>", "Entretien", "rendez-vous")

    assert len(find_replies(database_file, [vMessage])) == 1

    mark_reply_handled(database_file, "<4>")

    assert find_replies(database_file, [vMessage]) == []


def test_raw_message_is_decoded():
    """Vérifie la lecture d'un message brut : en-têtes encodés et texte HTML."""

    vRaw = (
        b"Message-ID: <42@kiabi.com>\r\n"
        b"From: =?utf-8?q?Recrutement_Kiabi?= <rh@kiabi.com>\r\n"
        b"Subject: =?utf-8?q?R=C3=A9ponse_=C3=A0_votre_candidature?=\r\n"
        b"Date: Thu, 22 Oct 2026 10:00:00 +0200\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<p>Nous souhaitons vous <b>rencontrer</b></p>"
    )

    vMessage = parse_message(vRaw)

    assert vMessage["subject"] == "Réponse à votre candidature"
    assert vMessage["sender"].startswith("Recrutement Kiabi")
    assert vMessage["text"] == "Nous souhaitons vous rencontrer"
    assert vMessage["date"].day == 22


@pytest.mark.parametrize(
    ("pText", "pExpected"),
    [
        ("Entretien le mardi 5 novembre à 14h30", datetime(2026, 11, 5, 14, 30)),
        ("rendez-vous le 05/11/2026 à 9 h", datetime(2026, 11, 5, 9, 0)),
        ("le 20 octobre à 10h", None),
        ("pas de date dans ce message", None),
    ],
)
def test_interview_date_is_read_in_the_message(pText, pExpected):
    """Vérifie la date d'entretien lue en toutes lettres ou en chiffres."""

    assert find_interview_date(pText, NOW) == pExpected


def test_date_without_year_in_december_is_next_year():
    """Vérifie qu'un « 3 janvier » lu en décembre désigne l'année suivante."""

    assert find_interview_date("le 3 janvier à 10h", datetime(2026, 12, 20)) == (
        datetime(2027, 1, 3, 10, 0)
    )


def test_dated_interview_is_saved_with_the_status(database_file):
    """Vérifie que l'entretien daté est enregistré, notes gardées."""

    vMessage = build_message(
        "<5>", "Kiabi <rh@kiabi.com>", "Entretien", "Rendez-vous le 5 novembre à 14h"
    )
    vReply = find_replies(database_file, [vMessage])[0]

    apply_reply(database_file, vReply, NOW)
    vApplication = get_application(database_file, "smartrecruiters", "1")

    assert vApplication["status"] == "INTERVIEW"
    assert vApplication["interview_at"] == "2026-11-05T14:00"
    assert vApplication["notes"] == "Relancer RH"


def test_due_check_keeps_replies_without_message_content(database_file, monkeypatch):
    """Vérifie la lecture espacée, sans Gmail rien, et seulement offre et statut gardés."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)

    assert run_due_reply_check(database_file, NOW) is None

    monkeypatch.setenv("GMAIL_ADDRESS", "moi@exemple.fr")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret")
    vMessage = build_message(
        "<9>", "Kiabi <rh@kiabi.com>", "Votre candidature", "Malheureusement..."
    )
    monkeypatch.setattr(
        application_replies, "read_recent_messages", lambda pNow, pDays: [vMessage]
    )

    assert run_due_reply_check(database_file, NOW) == 1
    assert run_due_reply_check(database_file, NOW + timedelta(hours=1)) is None

    vPending = load_pending_replies(database_file)

    assert vPending == [
        {
            "id": build_reply_id("<9>"),
            "title": "Dev Java",
            "company": "Kiabi",
            "status": "REJECTED",
            "interview_at": None,
        }
    ]
