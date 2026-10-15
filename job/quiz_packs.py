"""Lots de révision validés : import groupé des archives de data/packs

Une archive nommée « <thème>-l<lot>-valide.zip » a passé le contrôle des lots.
Elles s'importent toutes d'un coup ; une archive déjà importée ne change rien,
ses questions identiques étant comptées comme inchangées.
"""

import zipfile
from pathlib import Path

from config import QUIZ_PACKS_DIRECTORY
from job.quiz_import import import_questions_file
from utils.logger import get_logger

logger = get_logger(__name__)

VALIDATED_SUFFIX = "-valide.zip"

# Compteurs et listes additionnés d'une archive à l'autre dans le bilan global
REPORT_COUNTS = ("added", "replaced", "unchanged", "assets", "guides")
REPORT_LISTS = ("quality", "warnings", "review", "notes")


def list_validated_packs(pDirectory=None):
    """Retourne les archives validées du dossier, triées par nom."""

    vDirectory = Path(pDirectory or QUIZ_PACKS_DIRECTORY)

    rPacks = (
        sorted(vDirectory.glob(f"*{VALIDATED_SUFFIX}")) if vDirectory.is_dir() else []
    )

    return rPacks


def import_validated_packs(pDatabaseFile, pNow, pDirectory=None):
    """Importe toutes les archives validées ; retourne un bilan global.

    Une archive illisible est écartée avec sa raison, sans bloquer les autres.
    Lève ValueError s'il n'y a aucune archive à importer.
    """

    vPacks = list_validated_packs(pDirectory)

    if not vPacks:
        raise ValueError(
            f"Aucune archive « *{VALIDATED_SUFFIX} » dans "
            f"{pDirectory or QUIZ_PACKS_DIRECTORY}."
        )

    rReport = {
        **{vKey: 0 for vKey in REPORT_COUNTS},
        **{vKey: [] for vKey in REPORT_LISTS},
        "themes": [],
        "rejected": [],
    }

    for vPack in vPacks:
        try:
            vReport = import_questions_file(
                pDatabaseFile, "", vPack.name, vPack.read_bytes(), pNow
            )

        except (ValueError, OSError, zipfile.BadZipFile) as vException:
            rReport["rejected"].append(f"{vPack.name} : {vException}")
            continue

        for vKey in REPORT_COUNTS:
            rReport[vKey] += vReport.get(vKey, 0)

        for vKey in REPORT_LISTS:
            rReport[vKey] += vReport.get(vKey, [])

        rReport["themes"] += [
            vTheme for vTheme in vReport["themes"] if vTheme not in rReport["themes"]
        ]
        rReport["rejected"] += [
            f"{vPack.name}, {vReason}" for vReason in vReport["rejected"]
        ]

    logger.info(
        "Lots validés importés : %s archive(s), %s ajoutée(s), %s remplacée(s), "
        "%s inchangée(s)",
        len(vPacks),
        rReport["added"],
        rReport["replaced"],
        rReport["unchanged"],
    )

    return rReport
