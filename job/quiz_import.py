"""Import de questions de révision : réponse ChatGPT, fichier JSON ou pack .zip

Un pack .zip peut contenir, en plus des questions, des schémas SVG et des
guides en Markdown. Tout est vérifié avant d'être enregistré : une question
incomplète, incohérente ou en double est écartée avec sa raison.
"""

import json
import posixpath
import re
import unicodedata
import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from job.quiz import (
    QUESTION_FIELDS,
    QUIZ_LEVELS,
    check_question,
    find_theme,
    load_active_quiz,
    load_quiz,
    slugify,
)
from storage.quiz_questions import (
    get_imported_questions,
    save_imported_questions,
    save_quiz_assets,
    save_quiz_guides,
    save_quiz_theme,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, la saisie est une erreur de copier-coller.
MAX_IMPORT_LENGTH = 2_000_000
MAX_IMPORT_QUESTIONS = 200

# Nombre de questions demandées à ChatGPT en une fois : au-delà, la réponse est
# souvent coupée.
GENERATION_COUNTS = (10, 20, 30, 50)

# Identifiants déjà pris envoyés à ChatGPT, pour éviter les doublons
MAX_PROMPT_IDS = 300

IMPORT_EXTENSIONS = (".json", ".txt", ".zip")
MAX_ZIP_FILES = 300
MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_SVG_BYTES = 300 * 1024
MAX_GUIDE_BYTES = 200 * 1024

# Niveaux écrits sans accent dans certains fichiers : « debutant », « confirme »
LEVEL_ALIASES = {
    unicodedata.normalize("NFKD", vLevel).encode("ascii", "ignore").decode(): vLevel
    for vLevel in QUIZ_LEVELS
}

# Seul le QCM est affichable : une question ouverte n'a pas de choix à cocher.
QUESTION_TYPES = ("qcm",)

MAX_TAGS = 10
MAX_REFERENCES = 5

# Un SVG peut porter du script : affiché tel quel, il pourrait agir dans la page.
UNSAFE_SVG_PATTERN = re.compile(
    r"<script|javascript:|<foreignobject|<iframe|<embed|<object|\son[a-z]+\s*="
    r"|href\s*=\s*[\"']\s*(?:https?:|//|data:)",
    re.IGNORECASE,
)


def parse_questions_text(pText):
    """Lit le thème, les compétences et les questions d'un texte JSON.

    Le JSON peut être entouré de texte ou d'un bloc de code : seule la partie
    entre la première accolade ou le premier crochet et le dernier est lue.
    """

    vText = str(pText or "")

    if len(vText) > MAX_IMPORT_LENGTH:
        raise ValueError("Texte trop long pour un import.")

    vStarts = [vIndex for vIndex in (vText.find("{"), vText.find("[")) if vIndex >= 0]
    vEnd = max(vText.rfind("}"), vText.rfind("]"))

    if not vStarts or vEnd < min(vStarts):
        raise ValueError("Aucune question au format JSON n'a été trouvée.")

    try:
        vData = json.loads(vText[min(vStarts) : vEnd + 1])

    except ValueError as vException:
        raise ValueError(
            "JSON illisible : la réponse est peut-être coupée, demandez moins de "
            "questions à la fois."
        ) from vException

    vObject = vData if isinstance(vData, dict) else {}
    vQuestions = vObject.get("questions") if vObject else vData

    if not isinstance(vQuestions, list) or not vQuestions:
        raise ValueError("Aucune question au format JSON n'a été trouvée.")

    if len(vQuestions) > MAX_IMPORT_QUESTIONS:
        raise ValueError(f"{MAX_IMPORT_QUESTIONS} questions au plus par import.")

    vTheme = vObject.get("theme")
    vSkills = vObject.get("skills")

    rParsed = {
        "theme": vTheme.strip() if isinstance(vTheme, str) and vTheme.strip() else None,
        "skills": (
            [vSkill for vSkill in vSkills if isinstance(vSkill, str) and vSkill.strip()]
            if isinstance(vSkills, list)
            else []
        ),
        "questions": vQuestions,
    }

    return rParsed


def clean_references(pReferences):
    """Garde les références au format attendu, et seulement les liens https."""

    rReferences = [
        {"title": vReference["title"].strip()[:150], "url": vReference["url"].strip()}
        for vReference in (pReferences if isinstance(pReferences, list) else [])
        if isinstance(vReference, dict)
        and isinstance(vReference.get("title"), str)
        and isinstance(vReference.get("url"), str)
        and vReference["url"].strip().startswith("https://")
        and len(vReference["url"]) <= 500
    ][:MAX_REFERENCES]

    return rReferences


def normalize_question(pQuestion, pLabel, pVisuals):
    """Vérifie une question et retourne sa version enregistrée ; lève ValueError.

    pVisuals associe le chemin d'un schéma, tel qu'écrit dans la question, au nom
    du schéma enregistré.
    """

    if not isinstance(pQuestion, dict):
        raise ValueError(f"{pLabel} : format inattendu")

    vQuestion = dict(pQuestion)
    vId = vQuestion.get("id", "sans identifiant")

    if vQuestion.get("type", "qcm") not in QUESTION_TYPES:
        raise ValueError(
            f"{pLabel}, question {vId} : seul le type qcm est pris en charge"
        )

    if isinstance(vQuestion.get("level"), str):
        vLevel = vQuestion["level"].strip().lower()
        vQuestion["level"] = LEVEL_ALIASES.get(vLevel, vLevel)

    check_question(vQuestion, pLabel)

    # Champ redondant des packs : un écart signale une question à ne pas croire.
    vExpected = vQuestion.get("expectedAnswer")

    if vExpected is not None and (
        str(vExpected).strip() != vQuestion["choices"][vQuestion["answer"]].strip()
    ):
        raise ValueError(f"{pLabel}, question {vId} : réponse attendue incohérente")

    rQuestion = {
        vField: vQuestion[vField]
        for vField in (*QUESTION_FIELDS, "code")
        if vField in vQuestion
    }

    vTags = vQuestion.get("tags")

    if isinstance(vTags, list):
        rQuestion["tags"] = [
            vTag.strip()[:40]
            for vTag in vTags
            if isinstance(vTag, str) and vTag.strip()
        ][:MAX_TAGS]

    vReferences = clean_references(vQuestion.get("references"))

    if vReferences:
        rQuestion["references"] = vReferences

    vVisual = vQuestion.get("visual")

    if isinstance(vVisual, dict) and vVisual.get("path") in pVisuals:
        rQuestion["visual"] = {
            "asset": pVisuals[vVisual["path"]],
            "alt": str(vVisual.get("alt") or "Schéma de la question")[:200],
        }

    return rQuestion


def import_questions(
    pDatabaseFile, pThemeLabel, pText, pNow, pThemeKey=None, pVisuals=None
):
    """Vérifie puis enregistre des questions ; retourne le bilan de l'import.

    Le thème indiqué dans le JSON l'emporte sur pThemeLabel ; pThemeKey impose
    la clé du thème, celle d'un pack. Lève ValueError si rien n'est lisible.
    """

    vParsed = parse_questions_text(pText)
    vRequestedTheme = vParsed["theme"] or str(pThemeLabel or "").strip()

    if not vRequestedTheme:
        raise ValueError("Indiquez le thème des questions.")

    vQuiz = load_active_quiz(pDatabaseFile)
    vThemeKey, vThemeLabel = find_theme(vQuiz, pThemeKey or vRequestedTheme)

    if pThemeKey and vThemeKey not in vQuiz:
        vThemeLabel = vRequestedTheme

    # Les questions signalées gardent leur identifiant : il reste pris.
    vIds = {
        vQuestion["id"]
        for vTheme in load_quiz().values()
        for vQuestion in vTheme["questions"]
    }
    vIds |= {
        vQuestion["id"] for _, _, vQuestion in get_imported_questions(pDatabaseFile)
    }
    vTexts = {
        " ".join(vQuestion["question"].lower().split()) + vQuestion.get("code", "")
        for vQuestion in vQuiz.get(vThemeKey, {}).get("questions", [])
    }

    vAdded = []
    rRejected = []

    for vIndex, vQuestion in enumerate(vParsed["questions"], start=1):
        try:
            vClean = normalize_question(vQuestion, f"question {vIndex}", pVisuals or {})

            vText = " ".join(vClean["question"].lower().split()) + vClean.get(
                "code", ""
            )

            if vClean["id"] in vIds:
                raise ValueError(f"question {vClean['id']} : identifiant déjà utilisé")

            if vText in vTexts:
                raise ValueError(f"question {vClean['id']} : déjà présente")

        except ValueError as vException:
            rRejected.append(str(vException))

        else:
            vAdded.append(vClean)
            vIds.add(vClean["id"])
            vTexts.add(vText)

    if vAdded:
        # Un thème livré garde ses compétences ; un nouveau prend celles du fichier.
        if vThemeKey not in load_quiz():
            save_quiz_theme(
                pDatabaseFile,
                vThemeKey,
                vThemeLabel,
                vParsed["skills"] or [vThemeLabel],
            )

        save_imported_questions(pDatabaseFile, vThemeKey, vThemeLabel, vAdded, pNow)

    if rRejected:
        logger.warning("Import de révision : %s question(s) écartée(s)", len(rRejected))

    rReport = {
        "themes": [vThemeLabel] if vAdded else [],
        "added": len(vAdded),
        "rejected": rRejected,
        "assets": 0,
        "guides": 0,
    }

    return rReport


def merge_report(pReport, pFileReport, pFileName):
    """Ajoute le bilan d'un fichier de l'archive au bilan global."""

    pReport["added"] += pFileReport["added"]
    pReport["themes"] += [
        vTheme for vTheme in pFileReport["themes"] if vTheme not in pReport["themes"]
    ]
    pReport["rejected"] += [
        f"{pFileName}, {vReason}" for vReason in pFileReport["rejected"]
    ]


def find_theme_files(pArchive, pNames):
    """Retourne les fichiers de questions d'un pack et la clé imposée de chacun.

    Un manifest.json liste les thèmes : les autres JSON, comme un exemple de
    format, sont alors ignorés.
    """

    vManifests = sorted(
        (vName for vName in pNames if PurePosixPath(vName).name == "manifest.json"),
        key=len,
    )

    if vManifests:
        vRoot = posixpath.dirname(vManifests[0])
        vManifest = json.loads(pArchive.read(vManifests[0]).decode("utf-8"))

        rFiles = [
            (
                posixpath.normpath(posixpath.join(vRoot, vTheme["file"])),
                slugify(vTheme.get("id") or PurePosixPath(vTheme["file"]).stem),
            )
            for vTheme in vManifest.get("themes", [])
            if isinstance(vTheme, dict) and isinstance(vTheme.get("file"), str)
        ]
    else:
        rFiles = [
            (vName, None)
            for vName in pNames
            if vName.lower().endswith(".json")
            and not PurePosixPath(vName).name.lower().startswith("schema")
        ]

    return rFiles


def read_visuals(pArchive, pNames, pThemeFile, pText, pRejected):
    """Lit les schémas SVG cités par un fichier de questions.

    Retourne (chemin écrit dans la question -> nom du schéma, schémas à
    enregistrer). Un schéma absent, trop gros ou porteur de script est ignoré.
    """

    try:
        vQuestions = json.loads(pText).get("questions", [])

    except (ValueError, AttributeError):
        vQuestions = []

    vPaths = {
        vQuestion["visual"]["path"]
        for vQuestion in vQuestions
        if isinstance(vQuestion, dict)
        and isinstance(vQuestion.get("visual"), dict)
        and isinstance(vQuestion["visual"].get("path"), str)
    }

    rVisuals = {}
    rAssets = {}

    for vPath in vPaths:
        # Chemin relatif au fichier du thème, comme « ../assets/schemas/x.svg »
        vEntry = posixpath.normpath(
            posixpath.join(posixpath.dirname(pThemeFile), vPath)
        )
        vName = slugify(PurePosixPath(vEntry).stem) + ".svg"

        if not vEntry.lower().endswith(".svg") or vEntry not in pNames:
            pRejected.append(f"schéma introuvable : {vPath}")
        elif pArchive.getinfo(vEntry).file_size > MAX_SVG_BYTES:
            pRejected.append(f"schéma trop volumineux : {vPath}")
        else:
            vContent = pArchive.read(vEntry).decode("utf-8", errors="replace")

            if UNSAFE_SVG_PATTERN.search(vContent) or "<svg" not in vContent:
                pRejected.append(f"schéma refusé (script ou format) : {vPath}")
            else:
                rVisuals[vPath] = vName
                rAssets[vName] = vContent

    return rVisuals, rAssets


def read_guides(pArchive, pNames, pThemeKeys):
    """Lit les guides Markdown d'un dossier guides/ ; retourne leurs lignes."""

    rGuides = []

    for vName in pNames:
        vPath = PurePosixPath(vName)

        if (
            vPath.suffix.lower() != ".md"
            or vPath.parent.name != "guides"
            or pArchive.getinfo(vName).file_size > MAX_GUIDE_BYTES
        ):
            continue

        vContent = pArchive.read(vName).decode("utf-8", errors="replace")
        vKey = slugify(vPath.stem)
        vTitle = next(
            (
                vLine.lstrip("#").strip()
                for vLine in vContent.splitlines()
                if vLine.startswith("# ")
            ),
            vPath.stem,
        )
        # « Guide — analyser… » : le mot Guide est déjà dans la page.
        vTitle = re.sub(r"^guide\s*[—–-]\s*", "", vTitle, flags=re.IGNORECASE)
        # « tomcat-configuration » accompagne le thème « tomcat ».
        vTheme = next(
            (
                vThemeKey
                for vThemeKey in sorted(pThemeKeys, key=len, reverse=True)
                if vKey == vThemeKey or vKey.startswith(vThemeKey + "-")
            ),
            None,
        )

        rGuides.append(
            (vKey, vTheme, (vTitle[:1].upper() + vTitle[1:])[:150], vContent)
        )

    return rGuides


def import_zip(pDatabaseFile, pThemeLabel, pContent, pNow):
    """Importe un pack .zip : questions, schémas et guides."""

    try:
        vArchive = zipfile.ZipFile(BytesIO(pContent))

    except zipfile.BadZipFile as vException:
        raise ValueError("Archive .zip illisible.") from vException

    with vArchive:
        vInfos = [vEntry for vEntry in vArchive.infolist() if not vEntry.is_dir()]

        # Tailles annoncées vérifiées avant lecture : une archive piégée est refusée.
        if len(vInfos) > MAX_ZIP_FILES or (
            sum(vEntry.file_size for vEntry in vInfos) > MAX_ZIP_BYTES
        ):
            raise ValueError(
                f"Archive trop volumineuse : {MAX_ZIP_FILES} fichiers et "
                f"{MAX_ZIP_BYTES // (1024 * 1024)} Mo au plus."
            )

        # Liste plutôt qu'ensemble : les thèmes gardent l'ordre de l'archive.
        vNames = [vEntry.filename for vEntry in vInfos]

        try:
            vThemeFiles = find_theme_files(vArchive, vNames)

        except (ValueError, KeyError, zipfile.BadZipFile) as vException:
            raise ValueError("manifest.json illisible.") from vException

        if not vThemeFiles:
            raise ValueError("L'archive ne contient aucun fichier .json.")

        rReport = {"themes": [], "added": 0, "rejected": [], "assets": 0, "guides": 0}
        vAssets = {}

        for vThemeFile, vThemeKey in vThemeFiles:
            vFileName = PurePosixPath(vThemeFile).name

            try:
                if vThemeFile not in vNames:
                    raise ValueError("fichier cité par manifest.json introuvable")

                vText = vArchive.read(vThemeFile).decode("utf-8", errors="replace")
                vRejected = []
                vVisuals, vFileAssets = read_visuals(
                    vArchive, vNames, vThemeFile, vText, vRejected
                )

                vReport = import_questions(
                    pDatabaseFile,
                    pThemeLabel or PurePosixPath(vThemeFile).stem,
                    vText,
                    pNow,
                    vThemeKey,
                    vVisuals,
                )

            except (ValueError, zipfile.BadZipFile) as vException:
                rReport["rejected"].append(f"{vFileName} : {vException}")

            else:
                vAssets.update(vFileAssets)
                vReport["rejected"] = vRejected + vReport["rejected"]
                merge_report(rReport, vReport, vFileName)

        if vAssets:
            save_quiz_assets(pDatabaseFile, vAssets, pNow)

        vGuides = read_guides(vArchive, vNames, set(load_active_quiz(pDatabaseFile)))

        if vGuides:
            save_quiz_guides(pDatabaseFile, vGuides, pNow)

    rReport["assets"] = len(vAssets)
    rReport["guides"] = len(vGuides)

    logger.info(
        "Pack de révision importé : %s question(s), %s schéma(s), %s guide(s)",
        rReport["added"],
        rReport["assets"],
        rReport["guides"],
    )

    return rReport


def import_questions_file(pDatabaseFile, pThemeLabel, pFileName, pContent, pNow):
    """Importe un fichier .json ou .txt, ou un pack .zip."""

    vExtension = PurePosixPath(str(pFileName or "").replace("\\", "/")).suffix.lower()

    if vExtension not in IMPORT_EXTENSIONS:
        raise ValueError(
            "Fichier refusé : formats acceptés " + ", ".join(IMPORT_EXTENSIONS)
        )

    if vExtension == ".zip":
        rReport = import_zip(pDatabaseFile, pThemeLabel, pContent, pNow)
    else:
        rReport = import_questions(
            pDatabaseFile, pThemeLabel, pContent.decode("utf-8", errors="replace"), pNow
        )

    return rReport


def describe_quiz_import(pReport):
    """Résume un import en une phrase, avec les premières raisons de rejet."""

    rText = f"{pReport['added']} question(s) ajoutée(s)" + (
        f" : {', '.join(pReport['themes'])}." if pReport["themes"] else "."
    )

    if pReport.get("assets") or pReport.get("guides"):
        rText += f" {pReport['assets']} schéma(s) et {pReport['guides']} guide(s)."

    if pReport["rejected"]:
        rText += (
            f" {len(pReport['rejected'])} écartée(s) : "
            + " ; ".join(pReport["rejected"][:5])
            + (" ; …" if len(pReport["rejected"]) > 5 else "")
        )

    return rText


def build_generation_prompt(pQuiz, pThemeLabel, pLevel, pCount):
    """Retourne la demande ChatGPT qui produit des questions au format attendu."""

    vThemeKey, vThemeLabel = find_theme(pQuiz, pThemeLabel)
    vIds = [
        vQuestion["id"] for vQuestion in pQuiz.get(vThemeKey, {}).get("questions", [])
    ]
    vLevel = pLevel if pLevel in QUIZ_LEVELS else QUIZ_LEVELS[0]

    rPrompt = (
        f"Écris {pCount} questions à choix multiple sur « {vThemeLabel} », niveau "
        f"{vLevel}, pour préparer un entretien technique de développeur.\n"
        "Règles :\n"
        "1. Une seule bonne réponse par question, vérifiée ; 4 choix plausibles.\n"
        "2. Place la bonne réponse à des positions variées.\n"
        "3. Mélange « que fait ce code ? », notions, nouveautés de version et "
        "bonnes pratiques.\n"
        "4. Une explication de 1 à 3 phrases qui justifie la réponse.\n"
        f"5. Identifiants en minuscules et tirets, commençant par « {vThemeKey}- », "
        "jamais parmi ceux déjà pris ci-dessous.\n"
        "6. Une ou deux références officielles en https quand elles existent.\n"
        "7. Tout en français, sauf le code.\n"
        "Réponds uniquement par ce JSON, sans texte autour :\n"
        '{"questions": [{"id": "' + vThemeKey + '-exemple", "level": "' + vLevel + '", '
        '"question": "Que fait ce code ?", "code": "facultatif", '
        '"choices": ["…", "…", "…", "…"], "answer": 0, "explanation": "…", '
        '"references": [{"title": "…", "url": "https://…"}]}]}\n\n'
        "Identifiants déjà pris : " + (", ".join(vIds[-MAX_PROMPT_IDS:]) or "aucun")
    )

    return rPrompt
