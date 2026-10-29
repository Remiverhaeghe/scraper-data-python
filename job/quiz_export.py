"""Export des questions importées dans un pack .zip, réimportable tel quel"""

import json
import zipfile

from job.quiz import get_flagged_questions, load_active_quiz
from job.quiz_domains import classify_theme
from storage.quiz_questions import (
    get_imported_questions,
    get_quiz_assets,
    get_quiz_guide,
    get_quiz_guides,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des schémas dans un pack exporté
EXPORT_SCHEMA_DIRECTORY = "assets/schemas"


def export_quiz_pack(pDatabaseFile, pTarget):
    """Écrit les questions importées dans un pack .zip ; retourne leur nombre.

    Le pack reprend le format accepté à l'import (manifest, questions, schémas
    et guides) : il se réimporte tel quel. Les questions livrées avec
    l'application et celles signalées comme douteuses n'y figurent pas.
    """

    vQuiz = load_active_quiz(pDatabaseFile)
    vFlagged = get_flagged_questions(pDatabaseFile)
    vThemes = {}

    for vKey, vLabel, vQuestion in get_imported_questions(pDatabaseFile):
        if vQuestion["id"] in vFlagged:
            continue

        vExported = {**vQuestion, "type": "qcm"}
        vVisual = vExported.pop("visual", None)

        if vVisual:
            # Chemin relatif au fichier du thème, comme dans les packs de ChatGPT
            vExported["visual"] = {
                "type": "svg",
                "path": f"../{EXPORT_SCHEMA_DIRECTORY}/{vVisual['asset']}",
                "alt": vVisual["alt"],
            }

        vTheme = vQuiz.get(vKey, {"label": vLabel, "skills": [vLabel]})
        vDomain = vTheme.get("domain") or classify_theme(
            vTheme["label"], vTheme["skills"]
        )
        vThemes.setdefault(
            vKey,
            {
                "theme": vTheme["label"],
                "domain": vDomain[0],
                "subdomain": vDomain[1],
                "skills": vTheme["skills"],
                "questions": [],
            },
        )["questions"].append(vExported)

    if not vThemes:
        raise ValueError("Aucune question importée à exporter.")

    vManifest = {
        "project": "JobBoard Perso : questions de révision",
        "language": "fr",
        "questionCount": sum(len(vTheme["questions"]) for vTheme in vThemes.values()),
        "themes": [
            {
                "id": vKey,
                "file": f"questions/{vKey}.json",
                "theme": vTheme["theme"],
                "questionCount": len(vTheme["questions"]),
                "skills": vTheme["skills"],
            }
            for vKey, vTheme in vThemes.items()
        ],
    }

    with zipfile.ZipFile(pTarget, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr(
            "manifest.json", json.dumps(vManifest, ensure_ascii=False, indent=2)
        )

        for vKey, vTheme in vThemes.items():
            vArchive.writestr(
                f"questions/{vKey}.json",
                json.dumps(vTheme, ensure_ascii=False, indent=2),
            )

        for vName, vContent in get_quiz_assets(pDatabaseFile, pShipped=False).items():
            vArchive.writestr(f"{EXPORT_SCHEMA_DIRECTORY}/{vName}", vContent)

        # Les guides livrés avec l'application n'y sont pas : réimportés, ils
        # masqueraient leurs mises à jour.
        for vGuide in get_quiz_guides(pDatabaseFile, pShipped=False):
            vArchive.writestr(
                f"guides/{vGuide['name']}.md",
                get_quiz_guide(pDatabaseFile, vGuide["name"])["content"],
            )

    rCount = vManifest["questionCount"]

    logger.info(
        "Questions de révision exportées : %s question(s), %s thème(s)",
        rCount,
        len(vThemes),
    )

    return rCount
