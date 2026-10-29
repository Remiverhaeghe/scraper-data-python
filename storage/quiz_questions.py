"""Questions de révision importées, rangées dans la base avec les autres données"""

import json
from functools import lru_cache
from pathlib import Path

from config import QUIZ_DIRECTORY
from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def save_imported_questions(pDatabaseFile, pThemeKey, pThemeLabel, pQuestions, pNow):
    """Enregistre des questions déjà vérifiées dans un thème.

    Une question déjà importée est remplacée par sa version corrigée et garde
    sa date d'ajout.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO quiz_question (question_id, theme, theme_label, content, added_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
                theme_label = excluded.theme_label,
                content = excluded.content
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


# Schémas livrés avec les thèmes de l'application, un fichier SVG chacun
SHIPPED_SCHEMAS_DIRECTORY = Path(QUIZ_DIRECTORY) / "schemas"


@lru_cache
def load_shipped_assets(pDirectory=SHIPPED_SCHEMAS_DIRECTORY):
    """Retourne les schémas livrés : contenu par nom de fichier."""

    rAssets = {
        vFile.name: vFile.read_text(encoding="utf-8")
        for vFile in sorted(Path(pDirectory).glob("*.svg"))
    }

    return rAssets


def get_quiz_asset(pDatabaseFile, pName):
    """Retourne le contenu d'un schéma, ou None s'il est inconnu.

    Un schéma importé remplace le schéma livré du même nom.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vRow = vConnection.execute(
            "SELECT content FROM quiz_asset WHERE name = ?", (pName,)
        ).fetchone()

    finally:
        vConnection.close()

    rContent = vRow[0] if vRow else load_shipped_assets().get(pName)

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


# Guides livrés avec l'application, un fichier Markdown par thème : le nom du
# fichier est celui du thème, le titre la première ligne « # ».
SHIPPED_GUIDES_DIRECTORY = Path(QUIZ_DIRECTORY) / "guides"


@lru_cache
def load_shipped_guides(pDirectory=SHIPPED_GUIDES_DIRECTORY):
    """Retourne les guides livrés, par nom : thème, titre et contenu."""

    rGuides = {}

    for vFile in sorted(Path(pDirectory).glob("*.md")):
        vContent = vFile.read_text(encoding="utf-8")
        vTitle = next(
            (
                vLine[2:].strip()
                for vLine in vContent.splitlines()
                if vLine.startswith("# ")
            ),
            vFile.stem,
        )
        rGuides[vFile.stem] = {
            "name": vFile.stem,
            "theme": vFile.stem,
            "title": vTitle,
            "content": vContent,
        }

    return rGuides


def get_quiz_guides(pDatabaseFile, pShipped=True):
    """Retourne les guides : nom, thème et titre, sans leur contenu.

    Un guide importé remplace le guide livré du même nom. Sans pShipped, seuls
    les guides importés sont rendus, pour un export par exemple.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vImported = [
            {"name": vName, "theme": vTheme, "title": vTitle}
            for vName, vTheme, vTitle in vConnection.execute(
                "SELECT name, theme, title FROM quiz_guide ORDER BY title"
            )
        ]

    finally:
        vConnection.close()

    vNames = {vGuide["name"] for vGuide in vImported}
    rGuides = sorted(
        vImported
        + [
            {vKey: vGuide[vKey] for vKey in ("name", "theme", "title")}
            for vName, vGuide in load_shipped_guides().items()
            if pShipped and vName not in vNames
        ],
        key=lambda pGuide: pGuide["title"].casefold(),
    )

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

    rGuide = (
        dict(zip(("name", "theme", "title", "content"), vRow))
        if vRow
        else load_shipped_guides().get(pName)
    )

    return rGuide


def get_quiz_assets(pDatabaseFile, pShipped=True):
    """Retourne les schémas : contenu par nom, livrés puis importés.

    Sans pShipped, seuls les schémas importés sont rendus, pour un export.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vImported = dict(
            vConnection.execute("SELECT name, content FROM quiz_asset ORDER BY name")
        )

    finally:
        vConnection.close()

    rAssets = {**(load_shipped_assets() if pShipped else {}), **vImported}

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
