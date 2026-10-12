"""Questions de révision importées, rangées dans la base avec les autres données"""

import json

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def save_imported_questions(pDatabaseFile, pThemeKey, pThemeLabel, pQuestions, pNow):
    """Enregistre des questions déjà vérifiées dans un thème."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO quiz_question (question_id, theme, theme_label, content, added_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    vQuestion["id"],
                    pThemeKey,
                    pThemeLabel,
                    json.dumps(vQuestion, ensure_ascii=False),
                    pNow.isoformat(),
                )
                for vQuestion in pQuestions
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info(
        "Révision : %s question(s) importée(s) dans le thème %s",
        len(pQuestions),
        pThemeLabel,
    )


def get_imported_questions(pDatabaseFile):
    """Retourne les questions importées : (clé du thème, libellé, question)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT theme, theme_label, content FROM quiz_question ORDER BY added_at"
        ).fetchall()

    finally:
        vConnection.close()

    rQuestions = [
        (vTheme, vLabel, json.loads(vContent)) for vTheme, vLabel, vContent in vRows
    ]

    return rQuestions


def save_quiz_theme(pDatabaseFile, pThemeKey, pLabel, pSkills, pDomain=None):
    """Enregistre le libellé, les compétences et le domaine d'un thème importé.

    pDomain est (domaine, sous-domaine), ou None pour un classement automatique.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO quiz_theme (theme, label, skills, domain, subdomain)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(theme) DO UPDATE SET
                label = excluded.label, skills = excluded.skills,
                domain = excluded.domain, subdomain = excluded.subdomain
            """,
            (
                pThemeKey,
                pLabel,
                json.dumps(pSkills, ensure_ascii=False),
                *(pDomain or (None, None)),
            ),
        )
        vConnection.commit()

    finally:
        vConnection.close()


def get_quiz_themes(pDatabaseFile):
    """Retourne les thèmes importés : libellé et compétences, par clé."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT theme, label, skills, domain, subdomain FROM quiz_theme"
        ).fetchall()

    finally:
        vConnection.close()

    rThemes = {
        vTheme: {
            "label": vLabel,
            "skills": json.loads(vSkills),
            "domain": (vDomain, vSubdomain) if vDomain else None,
        }
        for vTheme, vLabel, vSkills, vDomain, vSubdomain in vRows
    }

    return rThemes


def save_quiz_assets(pDatabaseFile, pAssets, pNow):
    """Enregistre des schémas SVG, par nom ; un schéma du même nom est remplacé."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO quiz_asset (name, content, added_at) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                content = excluded.content, added_at = excluded.added_at
            """,
            [
                (vName, vContent, pNow.isoformat())
                for vName, vContent in pAssets.items()
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()


def get_quiz_asset(pDatabaseFile, pName):
    """Retourne le contenu d'un schéma, ou None s'il est inconnu."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRow = vConnection.execute(
            "SELECT content FROM quiz_asset WHERE name = ?", (pName,)
        ).fetchone()

    finally:
        vConnection.close()

    rContent = vRow[0] if vRow else None

    return rContent


def save_quiz_guides(pDatabaseFile, pGuides, pNow):
    """Enregistre des guides : (nom, thème ou None, titre, contenu Markdown)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO quiz_guide (name, theme, title, content, added_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                theme = excluded.theme, title = excluded.title,
                content = excluded.content, added_at = excluded.added_at
            """,
            [(*vGuide, pNow.isoformat()) for vGuide in pGuides],
        )
        vConnection.commit()

    finally:
        vConnection.close()


def get_quiz_guides(pDatabaseFile):
    """Retourne les guides : nom, thème et titre, sans leur contenu."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rGuides = [
            {"name": vName, "theme": vTheme, "title": vTitle}
            for vName, vTheme, vTitle in vConnection.execute(
                "SELECT name, theme, title FROM quiz_guide ORDER BY title"
            )
        ]

    finally:
        vConnection.close()

    return rGuides


def get_quiz_guide(pDatabaseFile, pName):
    """Retourne un guide avec son contenu, ou None s'il est inconnu."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRow = vConnection.execute(
            "SELECT name, theme, title, content FROM quiz_guide WHERE name = ?",
            (pName,),
        ).fetchone()

    finally:
        vConnection.close()

    rGuide = dict(zip(("name", "theme", "title", "content"), vRow)) if vRow else None

    return rGuide


def get_quiz_assets(pDatabaseFile):
    """Retourne tous les schémas enregistrés : contenu par nom."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rAssets = dict(
            vConnection.execute("SELECT name, content FROM quiz_asset ORDER BY name")
        )

    finally:
        vConnection.close()

    return rAssets


def delete_imported_content(pDatabaseFile):
    """Efface les questions importées, leurs réponses, thèmes, schémas et guides.

    Les questions livrées avec l'application et leurs réponses sont gardées.
    Retourne le nombre de questions effacées.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        rCount = vConnection.execute("SELECT COUNT(*) FROM quiz_question").fetchone()[0]

        # Réponses aux questions importées d'abord : elles n'auraient plus de sens.
        vConnection.execute(
            "DELETE FROM quiz_answer "
            "WHERE question_id IN (SELECT question_id FROM quiz_question)"
        )

        for vTable in ("quiz_question", "quiz_theme", "quiz_asset", "quiz_guide"):
            # Nom de table issu de la liste ci-dessus, une constante du code.
            vConnection.execute(f"DELETE FROM {vTable}")  # nosec B608

        vConnection.commit()

    finally:
        vConnection.close()

    return rCount
