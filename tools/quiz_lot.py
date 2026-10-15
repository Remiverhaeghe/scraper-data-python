"""Production et contrôle des lots de questions de révision

Un lot s'écrit dans tools/quiz_lots/<thème>/ : des fichiers partN.txt au format
compact et un fichier lot.json (compétences, schémas). La commande build en
fait une archive prête à importer ; check mesure une archive quelconque, par
exemple livrée par ChatGPT, en l'important dans une copie de la base.

    python -m tools.quiz_lot build <thème>
    python -m tools.quiz_lot check <archive.zip>
    python -m tools.quiz_lot links <thème ou archive.zip>

Format compact d'une question :

    @001
    Q: Énoncé ?
    C: Bonne réponse
    W: Mauvaise réponse
    W: Mauvaise réponse
    W: Mauvaise réponse
    E: Explication.
    R: Titre de la page officielle | https://…   (facultatif, deux au plus)
    ```
    extrait de code facultatif
    ```
"""

import argparse
import io
import json
import logging
import random
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from config import DATABASE_FILE, QUIZ_PACKS_DIRECTORY
from job.quiz_generation import find_catalog_theme
from job.quiz_import import (
    describe_import_details,
    describe_quiz_import,
    import_questions_file,
)
from storage.database import initialize_database
from tools.quiz_svg import build_chain_svg
from utils.link_checker import check_offer_link

LOTS_DIRECTORY = Path(__file__).parent / "quiz_lots"

# Répartition des niveaux d'un lot de 100 questions, dans l'ordre des numéros
LEVEL_LAYOUT = (
    ("débutant", 25),
    ("intermédiaire", 40),
    ("confirmé", 20),
    ("expert", 15),
)
LOT_SIZE = sum(vCount for _, vCount in LEVEL_LAYOUT)

FIELD_PATTERN = re.compile(r"([QCWER]): (.*)")

# Une référence s'écrit « Titre | adresse » ; le contrôle d'import garde les sûres.
REFERENCE_SEPARATOR = " | "
MAX_REFERENCES = 2

# Libellés des états renvoyés par la vérification d'un lien
LINK_STATUSES = {"available": "en ligne", "expired": "retirée", None: "indéterminée"}


def parse_lot_text(pText):
    """Lit des questions au format compact ; retourne {numéro : champs}.

    Lève ValueError si une question n'a pas exactement trois mauvaises réponses
    ou s'il lui manque un champ.
    """

    rQuestions = {}

    # Seule une ligne « @numéro » ouvre une question : @Override reste dans le code.
    for vBlock in re.split(r"^@(?=\d+\s*$)", pText, flags=re.MULTILINE)[1:]:
        vNumber, vBody = vBlock.split("\n", 1)
        vCode = None

        if "```" in vBody:
            vBody, vCode, _ = vBody.split("```", 2)
            vCode = vCode.strip("\n")

        vFields = {"W": [], "R": [], "code": vCode}

        for vLine in vBody.strip().splitlines():
            vMatch = FIELD_PATTERN.fullmatch(vLine.strip())

            if not vMatch:
                raise ValueError(f"question {vNumber.strip()} : ligne illisible")

            if vMatch.group(1) in "WR":
                vFields[vMatch.group(1)].append(vMatch.group(2).strip())
            else:
                vFields[vMatch.group(1)] = vMatch.group(2).strip()

        if len(vFields["W"]) != 3 or not all(vKey in vFields for vKey in "QCE"):
            raise ValueError(f"question {vNumber.strip()} : champs incomplets")

        if len(vFields["R"]) > MAX_REFERENCES or any(
            REFERENCE_SEPARATOR not in vReference for vReference in vFields["R"]
        ):
            raise ValueError(f"question {vNumber.strip()} : référence mal écrite")

        rQuestions[vNumber.strip()] = vFields

    return rQuestions


def load_lot(pTheme, pDirectory=LOTS_DIRECTORY):
    """Retourne la configuration et les questions d'un lot écrit."""

    vFolder = Path(pDirectory) / pTheme
    vConfig = json.loads((vFolder / "lot.json").read_text(encoding="utf-8"))
    vQuestions = {}

    for vPart in sorted(vFolder.glob("part*.txt")):
        vQuestions.update(parse_lot_text(vPart.read_text(encoding="utf-8")))

    vExpected = [f"{vNumber:03d}" for vNumber in range(1, LOT_SIZE + 1)]

    if sorted(vQuestions) != vExpected:
        vMissing = sorted(set(vExpected) - set(vQuestions))
        raise ValueError(f"{pTheme} : questions manquantes {vMissing[:5]}")

    rLot = (vConfig, vQuestions)

    return rLot


def build_schemas(pTheme, pConfig, pDirectory=LOTS_DIRECTORY):
    """Retourne les schémas du lot : {nom : (contenu SVG, texte alternatif)}."""

    rSchemas = {}

    for vSchema in pConfig.get("schemas", []):
        if "file" in vSchema:
            vSvg = (Path(pDirectory) / pTheme / vSchema["file"]).read_text(
                encoding="utf-8"
            )
            vAlt = vSchema["alt"]
        else:
            vDiagram = vSchema["diagram"]
            vSvg = build_chain_svg(
                vDiagram["title"],
                vDiagram["nodes"],
                vDiagram.get("feedback"),
                vDiagram.get("note"),
            )
            vAlt = vSchema.get("alt", vDiagram["title"])

        rSchemas[vSchema["name"]] = (vSvg, vAlt)

    return rSchemas


def build_questions(pTheme, pConfig, pQuestions):
    """Retourne les questions au format de l'import, bonnes réponses réparties.

    La position de la bonne réponse est tirée avec la graine du lot : la même
    source donne toujours la même archive.
    """

    vLevels = [vLevel for vLevel, vCount in LEVEL_LAYOUT for _ in range(vCount)]
    vPositions = [vIndex % 4 for vIndex in range(LOT_SIZE)]
    random.Random(pConfig["seed"]).shuffle(vPositions)  # nosec B311
    vVisuals = {
        vNumber: vSchema
        for vSchema in pConfig.get("schemas", [])
        for vNumber in vSchema["questions"]
    }
    rQuestions = []

    for vIndex, vNumber in enumerate(sorted(pQuestions)):
        vSource = pQuestions[vNumber]
        vChoices = list(vSource["W"])
        vChoices.insert(vPositions[vIndex], vSource["C"])
        vQuestion = {
            "id": f"{pTheme}-l{pConfig['lot']}-{vNumber}",
            "level": vLevels[vIndex],
            "type": "qcm",
            "question": vSource["Q"],
        }

        if vSource["code"]:
            vQuestion["code"] = vSource["code"]

        vQuestion.update(
            {
                "choices": vChoices,
                "answer": vPositions[vIndex],
                "expectedAnswer": vSource["C"],
                "explanation": vSource["E"],
            }
        )

        if vSource["R"]:
            vQuestion["references"] = [
                dict(zip(("title", "url"), vReference.split(REFERENCE_SEPARATOR, 1)))
                for vReference in vSource["R"]
            ]

        if vNumber in vVisuals:
            vQuestion["visual"] = {
                "type": "svg",
                "path": f"../assets/schemas/{vVisuals[vNumber]['name']}",
            }

        rQuestions.append(vQuestion)

    return rQuestions


def build_pack(pTheme, pDirectory=LOTS_DIRECTORY):
    """Retourne le nom et le contenu de l'archive d'un lot écrit."""

    vConfig, vSource = load_lot(pTheme, pDirectory)
    vCatalogTheme = find_catalog_theme(pTheme)

    if not vCatalogTheme:
        raise ValueError(f"{pTheme} : thème absent du catalogue")

    vSchemas = build_schemas(pTheme, vConfig, pDirectory)
    vQuestions = build_questions(pTheme, vConfig, vSource)

    for vQuestion in vQuestions:
        if "visual" in vQuestion:
            vName = Path(vQuestion["visual"]["path"]).name
            vQuestion["visual"]["alt"] = vSchemas[vName][1]

    vPack = {
        "theme": vCatalogTheme["label"],
        "domain": vCatalogTheme["domain"],
        "subdomain": vCatalogTheme["subdomain"],
        "skills": vConfig["skills"],
        "questions": vQuestions,
    }
    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr(
            "manifest.json",
            json.dumps(
                {"themes": [{"id": pTheme, "file": f"questions/{pTheme}.json"}]},
                ensure_ascii=False,
                indent=2,
            ),
        )
        vArchive.writestr(
            f"questions/{pTheme}.json",
            json.dumps(vPack, ensure_ascii=False, indent=2),
        )

        for vName, (vSvg, _) in vSchemas.items():
            vArchive.writestr(f"assets/schemas/{vName}", vSvg)

    rPack = (f"{pTheme}-l{vConfig['lot']}-valide.zip", vBuffer.getvalue())

    return rPack


def check_pack(pFileName, pContent, pDatabaseFile=None):
    """Importe une archive dans une copie de la base ; retourne le bilan.

    Sans base indiquée, la copie part d'une base vide : seul le contenu de
    l'archive est mesuré. La base réelle n'est jamais modifiée.
    """

    with tempfile.TemporaryDirectory() as vFolder:
        vCopy = Path(vFolder) / "essai.db"

        if pDatabaseFile and Path(pDatabaseFile).exists():
            shutil.copy(pDatabaseFile, vCopy)

        initialize_database(vCopy)

        rReport = import_questions_file(vCopy, "", pFileName, pContent, datetime.now())

    return rReport


def describe_check(pReport):
    """Retourne le bilan d'un contrôle d'archive, à afficher en console."""

    rText = "\n".join(
        vLine
        for vLine in (describe_quiz_import(pReport), describe_import_details(pReport))
        if vLine
    )

    return rText


def read_pack_questions(pContent):
    """Retourne toutes les questions des fichiers de questions d'une archive."""

    rQuestions = []

    with zipfile.ZipFile(io.BytesIO(pContent)) as vArchive:
        for vName in vArchive.namelist():
            if vName.startswith("questions/") and vName.endswith(".json"):
                vData = json.loads(vArchive.read(vName).decode("utf-8"))
                rQuestions += vData.get("questions", [])

    return rQuestions


def collect_references(pQuestions):
    """Retourne les adresses citées en référence et les questions qui les citent."""

    rReferences = {}

    for vQuestion in pQuestions:
        for vReference in vQuestion.get("references", []):
            rReferences.setdefault(vReference["url"], []).append(vQuestion["id"])

    return rReferences


def check_references(pReferences, pChecker=None):
    """Vérifie chaque adresse en ligne ; retourne {adresse : état}.

    pChecker suit les redirections sans jamais viser le réseau interne : une
    page retirée répond 404 ou 410, ou renvoie vers une page parente.
    """

    vChecker = pChecker or check_offer_link

    rStatuses = {vUrl: vChecker(vUrl) for vUrl in pReferences}

    return rStatuses


def describe_references(pReferences, pStatuses):
    """Retourne le bilan des références, pages retirées en premier."""

    vLines = [
        f"{LINK_STATUSES[pStatuses[vUrl]]} : {vUrl} ({', '.join(pReferences[vUrl])})"
        for vUrl in sorted(
            pReferences, key=lambda pUrl: (pStatuses[pUrl] != "expired", pUrl)
        )
    ]
    vExpired = sum(vStatus == "expired" for vStatus in pStatuses.values())

    rText = "\n".join(
        [f"{len(pReferences)} référence(s), {vExpired} retirée(s)", *vLines]
    )

    return rText


def run_links(pTarget):
    """Vérifie les références d'un lot écrit ou d'une archive ; retourne le code."""

    vPath = Path(pTarget)

    if vPath.suffix == ".zip":
        vQuestions = read_pack_questions(vPath.read_bytes())
    else:
        vConfig, vSource = load_lot(pTarget)
        vQuestions = build_questions(pTarget, vConfig, vSource)

    vReferences = collect_references(vQuestions)
    vStatuses = check_references(vReferences)
    print(describe_references(vReferences, vStatuses))

    rStatus = 1 if "expired" in vStatuses.values() else 0

    return rStatus


def main(pArguments=None):
    """Lance la commande demandée ; retourne 1 si le lot n'est pas conforme."""

    vParser = argparse.ArgumentParser(prog="python -m tools.quiz_lot")
    vCommands = vParser.add_subparsers(dest="command", required=True)
    vCommands.add_parser(
        "build", help="construit l'archive d'un lot écrit"
    ).add_argument("theme")
    vCommands.add_parser(
        "check", help="contrôle une archive sans l'importer"
    ).add_argument("archive")
    vCommands.add_parser(
        "links", help="vérifie en ligne les références d'un lot ou d'une archive"
    ).add_argument("target")
    vArguments = vParser.parse_args(pArguments)

    # Ces commandes travaillent sur des copies : leurs journaux ne concernent pas
    # l'application et encombreraient le bilan affiché.
    logging.disable(logging.CRITICAL)

    if vArguments.command == "links":
        return run_links(vArguments.target)

    if vArguments.command == "build":
        vFileName, vContent = build_pack(vArguments.theme)
        vTarget = Path(QUIZ_PACKS_DIRECTORY) / vFileName
        vTarget.parent.mkdir(parents=True, exist_ok=True)
        vTarget.write_bytes(vContent)
        print(f"Archive écrite : {vTarget}")
    else:
        vTarget = Path(vArguments.archive)
        vFileName, vContent = vTarget.name, vTarget.read_bytes()

    vReport = check_pack(vFileName, vContent, DATABASE_FILE)
    print(describe_check(vReport))

    rStatus = 1 if vReport["warnings"] or vReport["rejected"] else 0

    return rStatus


if __name__ == "__main__":
    sys.exit(main())
