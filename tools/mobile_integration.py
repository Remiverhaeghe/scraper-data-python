"""Préparation et contrôle du test d'intégration téléphone ↔ serveur

    python -m tools.mobile_integration prepare   base neuve, jeton affiché
    python -m tools.mobile_integration check     vérifie ce que le téléphone a envoyé

Utilisé par la CI autour de mobile/test/integration/server_sync_test.dart.
"""

import sys
from pathlib import Path

from config import DATABASE_FILE
from job.mobile_sync import renew_mobile_token
from job.quiz import get_flagged_questions
from job.quiz_exam import load_exam_results
from storage.database import initialize_database
from storage.quiz_answers import get_last_answers


def prepare():
    """Crée une base neuve et affiche le jeton ; retourne 1 si la base existe déjà.

    Renouveler le jeton d'une vraie base déconnecterait le téléphone : seule une
    base neuve, celle de la CI ou d'un dossier de test, est préparée.
    """

    if Path(DATABASE_FILE).exists():
        print(f"{DATABASE_FILE} existe déjà : lancer depuis un dossier de test vide.")
        return 1

    initialize_database(DATABASE_FILE)
    print(renew_mobile_token(DATABASE_FILE))

    return 0


def check():
    """Vérifie la réponse, le signalement et l'examen envoyés ; retourne 1 sinon."""

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

    print(
        "; ".join(vProblems) or "Synchronisation reçue : réponse, signalement, examen"
    )

    rStatus = 1 if vProblems else 0

    return rStatus


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        sys.exit(prepare())

    sys.exit(check())
