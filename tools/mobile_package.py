"""Paquet de révision livré dans l'application mobile

    python -m tools.mobile_package     réécrit mobile/assets/revision/depart.json.gz

Le téléphone s'en sert pour réviser sans jamais avoir vu le PC. Il contient les
thèmes livrés avec Tremplin, sans les questions importées ni les réponses.
Un test vérifie qu'il suit les thèmes livrés : relancer cette commande quand
ils changent.
"""

import gzip
import json
import tempfile
from datetime import datetime
from pathlib import Path

from job.mobile_sync import build_quiz_package
from storage.database import initialize_database

PACKAGE_FILE = (
    Path(__file__).resolve().parent.parent / "mobile/assets/revision/depart.json.gz"
)

# Date fixe : le fichier ne change que si le contenu change
FIXED_DATE = datetime(2026, 1, 1)


def build_starter_package():
    """Retourne le paquet des thèmes livrés, construit sur une base vide."""

    with tempfile.TemporaryDirectory() as vFolder:
        vDatabase = Path(vFolder) / "paquet.db"
        initialize_database(vDatabase)
        rPackage = build_quiz_package(vDatabase, FIXED_DATE)

    return rPackage


def read_starter_package(pFile=PACKAGE_FILE):
    """Retourne le paquet enregistré dans l'application, ou None s'il manque."""

    rPackage = None

    if pFile.exists():
        rPackage = json.loads(gzip.decompress(pFile.read_bytes()).decode("utf-8"))

    return rPackage


def write_starter_package(pFile=PACKAGE_FILE):
    """Écrit le paquet compressé ; mtime à zéro pour un fichier identique d'une fois sur l'autre."""

    vContent = json.dumps(build_starter_package(), ensure_ascii=False, sort_keys=True)
    pFile.parent.mkdir(parents=True, exist_ok=True)
    pFile.write_bytes(gzip.compress(vContent.encode("utf-8"), mtime=0))


if __name__ == "__main__":
    write_starter_package()
    print(f"Paquet écrit : {PACKAGE_FILE}")
