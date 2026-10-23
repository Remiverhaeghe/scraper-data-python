"""Préparation et contrôle du test d'intégration téléphone ↔ serveur

    python -m tools.mobile_integration prepare   base neuve, jeton affiché
    python -m tools.mobile_integration check     vérifie ce que le téléphone a envoyé

Utilisé par la CI autour de mobile/test/integration/server_sync_test.dart.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import DATABASE_FILE
from job.interview_simulation import get_history
from job.mobile_sync import renew_mobile_token
from job.profile import load_profile, save_profile
from job.quiz import get_flagged_questions
from job.quiz_exam import load_exam_results
from storage.database import initialize_database
from storage.job_applications import get_application
from storage.job_offers import save_offers
from storage.quiz_answers import get_last_answers

# Offre de la base de test, que le téléphone reçoit puis retient
TEST_OFFER = {
    "source": "adzuna",
    "source_id": "integration",
    "title": "Développeur Java",
    "company": "Entreprise de test",
    "location": "Lille",
    "url": "https://www.adzuna.fr/details/integration",
    "contract": "CDI",
    "description": "Java, SQL et Docker",
}


def prepare():
    """Crée une base neuve et affiche le jeton ; retourne 1 si la base existe déjà.

    Renouveler le jeton d'une vraie base déconnecterait le téléphone : seule une
    base neuve, celle de la CI ou d'un dossier de test, est préparée.
    """

    if Path(DATABASE_FILE).exists():
        print(f"{DATABASE_FILE} existe déjà : lancer depuis un dossier de test vide.")
        return 1

    initialize_database(DATABASE_FILE)
    save_profile(
        DATABASE_FILE, {**load_profile(DATABASE_FILE), "skills": ["Java", "SQL"]}
    )
    save_offers(DATABASE_FILE, pd.DataFrame([TEST_OFFER]), datetime.now())
    print(renew_mobile_token(DATABASE_FILE))

    return 0


def check():
    """Vérifie tout ce que le téléphone a envoyé ; retourne 1 s'il manque un élément."""

    vProblems = []

    if len(get_last_answers(DATABASE_FILE)) != 1:
        vProblems.append("réponse du téléphone absente")

    if len(get_flagged_questions(DATABASE_FILE)) != 1:
        vProblems.append("question signalée absente")

    if not any(
        vResult.get("device") == "téléphone"
        for vResult in load_exam_results(DATABASE_FILE)
    ):
        vProblems.append("examen blanc du téléphone absent")

    if not get_history(DATABASE_FILE):
        vProblems.append("série de simulation d'entretien absente")

    if not load_profile(DATABASE_FILE).get("skill_levels"):
        vProblems.append("auto-évaluation absente")

    vApplication = get_application(
        DATABASE_FILE, TEST_OFFER["source"], TEST_OFFER["source_id"]
    )

    if (vApplication or {}).get("status") != "INTERESTED":
        vProblems.append("statut de l'offre absent")

    print(
        "; ".join(vProblems)
        or "Synchronisation reçue : réponse, signalement, examen, entretien, "
        "auto-évaluation et statut d'offre"
    )

    rStatus = 1 if vProblems else 0

    return rStatus


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        sys.exit(prepare())

    sys.exit(check())
