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
from urllib.parse import urlsplit

from job.quiz import (
    FLAGGED_KEY,
    QUESTION_FIELDS,
    QUIZ_LEVELS,
    check_question,
    find_theme,
    get_flagged_questions,
    load_active_quiz,
    load_quiz,
    slugify,
)
from job.quiz_domains import DOMAIN_ORDER, OTHER_DOMAIN, classify_theme
from job.quiz_exam import EXAM_KEY
from storage.backup import backup_database
from storage.quiz_questions import (
    delete_imported_content,
    get_imported_questions,
    get_quiz_assets,
    get_quiz_guide,
    get_quiz_guides,
    save_imported_questions,
    save_quiz_assets,
    save_quiz_guides,
    save_quiz_theme,
)
from storage.settings_repository import save_setting_values
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

# Niveau « tous » de la demande : répartition des questions par niveau, de
# débutant à expert, comme un pack équilibré (30 questions : 10, 10, 7, 3).
MIXED_LEVEL = "tous"
LEVEL_WEIGHTS = (0.34, 0.33, 0.23, 0.10)
GENERATION_LEVELS = {
    MIXED_LEVEL: "Tous les niveaux",
    **{vLevel: vLevel.capitalize() for vLevel in QUIZ_LEVELS},
}

IMPORT_EXTENSIONS = (".json", ".txt", ".zip")
MAX_ZIP_FILES = 300
MAX_ZIP_BYTES = 20 * 1024 * 1024

# Archives contenues dans l'archive importée : un seul niveau est ouvert.
MAX_ZIP_DEPTH = 1
MAX_SVG_BYTES = 300 * 1024
MAX_GUIDE_BYTES = 200 * 1024

# Dossier des schémas dans un pack exporté, comme dans ceux de ChatGPT
EXPORT_SCHEMA_DIRECTORY = "assets/schemas"

# Niveaux écrits sans accent dans certains fichiers : « debutant », « confirme »
LEVEL_ALIASES = {
    unicodedata.normalize("NFKD", vLevel).encode("ascii", "ignore").decode(): vLevel
    for vLevel in QUIZ_LEVELS
}

# Seul le QCM est affichable : une question ouverte n'a pas de choix à cocher.
QUESTION_TYPES = ("qcm",)

MAX_TAGS = 10
MAX_REFERENCES = 5
MAX_REFERENCE_LENGTH = 500

# Raccourcisseurs d'adresse : la destination réelle resterait cachée.
URL_SHORTENERS = frozenset(
    "bit.ly tinyurl.com t.co goo.gl ow.ly is.gd buff.ly cutt.ly rebrand.ly "
    "shorturl.at tiny.cc s.id t.ly".split()
)

# Une référence mène à une page à lire, jamais à un fichier à exécuter.
DOWNLOAD_EXTENSIONS = (
    ".exe",
    ".msi",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".jar",
    ".apk",
    ".dmg",
    ".zip",
    ".rar",
    ".7z",
    ".iso",
    ".scr",
    ".vbs",
    ".js",
)

IP_HOST_PATTERN = re.compile(r"[\d.]+")

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
    vDomain = (vObject.get("domain"), vObject.get("subdomain"))

    rParsed = {
        "theme": vTheme.strip() if isinstance(vTheme, str) and vTheme.strip() else None,
        "skills": (
            [vSkill for vSkill in vSkills if isinstance(vSkill, str) and vSkill.strip()]
            if isinstance(vSkills, list)
            else []
        ),
        "questions": vQuestions,
        # Domaine retenu seulement s'il fait partie du classement de l'application
        "domain": vDomain if vDomain[1] in DOMAIN_ORDER.get(vDomain[0], ()) else None,
    }

    return rParsed


def is_safe_reference(pUrl):
    """Indique si un lien de référence peut être proposé sans risque.

    Seul un lien https direct vers un site nommé est gardé : ni raccourcisseur
    qui masque la destination, ni adresse IP, ni identifiants dans l'adresse,
    ni port inhabituel, ni fichier à télécharger.
    """

    try:
        vUrl = urlsplit(pUrl.strip())
        vPort = vUrl.port

    except ValueError:
        return False

    vHost = (vUrl.hostname or "").lower()

    rSafe = (
        vUrl.scheme == "https"
        and len(pUrl) <= MAX_REFERENCE_LENGTH
        and "." in vHost
        and not vUrl.username
        and not vUrl.password
        and vPort in (None, 443)
        and not IP_HOST_PATTERN.fullmatch(vHost)
        and not vHost.startswith("[")
        and vHost.removeprefix("www.") not in URL_SHORTENERS
        and not vUrl.path.lower().endswith(DOWNLOAD_EXTENSIONS)
    )

    return rSafe


def clean_references(pReferences):
    """Garde les références au format attendu, et seulement les liens sûrs."""

    rReferences = [
        {"title": vReference["title"].strip()[:150], "url": vReference["url"].strip()}
        for vReference in (pReferences if isinstance(pReferences, list) else [])
        if isinstance(vReference, dict)
        and isinstance(vReference.get("title"), str)
        and vReference["title"].strip()
        and isinstance(vReference.get("url"), str)
        and is_safe_reference(vReference["url"])
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
                vParsed["domain"],
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


def is_question_file(pName):
    """Indique si un fichier d'archive peut contenir des questions.

    Le manifest et l'exemple de format (schema-…) décrivent le pack : ils n'en
    contiennent pas.
    """

    vName = PurePosixPath(pName).name.lower()

    rQuestions = (
        vName.endswith(".json")
        and vName != "manifest.json"
        and not vName.startswith("schema")
    )

    return rQuestions


def find_theme_files(pArchive, pNames):
    """Retourne les fichiers de questions d'une archive et la clé imposée de chacun.

    Une archive peut réunir plusieurs packs, chacun dans son dossier avec son
    manifest.json. Un manifest qui liste ses thèmes est suivi à la lettre ; sans
    liste, tous les fichiers de questions de son dossier sont lus. Un fichier
    hors de tout pack est lu aussi.
    """

    vManifests = sorted(
        (vName for vName in pNames if PurePosixPath(vName).name == "manifest.json"),
        key=len,
    )
    vRoots = []
    rFiles = []

    for vManifestName in vManifests:
        vRoot = posixpath.dirname(vManifestName)
        vManifest = json.loads(pArchive.read(vManifestName).decode("utf-8"))
        vThemes = vManifest.get("themes") if isinstance(vManifest, dict) else None
        vRoots.append(vRoot)

        if isinstance(vThemes, list) and vThemes:
            rFiles += [
                (
                    posixpath.normpath(posixpath.join(vRoot, vTheme["file"])),
                    slugify(vTheme.get("id") or PurePosixPath(vTheme["file"]).stem),
                )
                for vTheme in vThemes
                if isinstance(vTheme, dict) and isinstance(vTheme.get("file"), str)
            ]
        else:
            rFiles += [
                (vName, None)
                for vName in pNames
                if is_question_file(vName)
                and vName.startswith(f"{vRoot}/" if vRoot else "")
            ]

    vListed = {vName for vName, _ in rFiles}

    # Fichiers hors de tout pack ; un pack placé dans un autre ne compte qu'une fois.
    rFiles += [
        (vName, None)
        for vName in pNames
        if is_question_file(vName)
        and vName not in vListed
        and not any(vName.startswith(f"{vRoot}/") for vRoot in vRoots if vRoot)
        and not ("" in vRoots and vManifests)
    ]

    rFiles = list(dict.fromkeys(rFiles))

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


def import_zip(pDatabaseFile, pThemeLabel, pContent, pNow, pDepth=0):
    """Importe un pack .zip : questions, schémas et guides.

    Une archive peut en contenir d'autres, ouvertes à leur tour sur un seul
    niveau : au-delà, l'archive est probablement piégée.
    """

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

        vInnerArchives = (
            [vName for vName in vNames if vName.lower().endswith(".zip")]
            if pDepth < MAX_ZIP_DEPTH
            else []
        )

        if not vThemeFiles and not vInnerArchives:
            raise ValueError("L'archive ne contient aucun fichier .json.")

        rReport = {"themes": [], "added": 0, "rejected": [], "assets": 0, "guides": 0}
        vAssets = {}
        vInnerCounts = {"assets": 0, "guides": 0}

        for vInnerName in vInnerArchives:
            vFileName = PurePosixPath(vInnerName).name

            try:
                vInner = import_zip(
                    pDatabaseFile,
                    pThemeLabel,
                    vArchive.read(vInnerName),
                    pNow,
                    pDepth + 1,
                )

            except (ValueError, zipfile.BadZipFile) as vException:
                rReport["rejected"].append(f"{vFileName} : {vException}")

            else:
                merge_report(rReport, vInner, vFileName)
                vInnerCounts["assets"] += vInner["assets"]
                vInnerCounts["guides"] += vInner["guides"]

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

    rReport["assets"] = len(vAssets) + vInnerCounts["assets"]
    rReport["guides"] = len(vGuides) + vInnerCounts["guides"]

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
    """Résume un import en une ligne : chiffres seulement, le détail est à part."""

    vParts = [f"{pReport['added']} question(s) ajoutée(s)"]

    if len(pReport["themes"]) > 1:
        vParts[0] += f" dans {len(pReport['themes'])} thèmes"
    elif pReport["themes"]:
        vParts[0] += f" : {pReport['themes'][0]}"

    if pReport.get("assets"):
        vParts.append(f"{pReport['assets']} schéma(s)")

    if pReport.get("guides"):
        vParts.append(f"{pReport['guides']} guide(s)")

    if pReport["rejected"]:
        vParts.append(f"{len(pReport['rejected'])} écartée(s)")

    rText = " · ".join(vParts) + "."

    return rText


def describe_import_details(pReport):
    """Détaille un import : thèmes concernés, puis chaque question écartée."""

    vLines = []

    if pReport["themes"]:
        vLines.append("Thèmes : " + ", ".join(pReport["themes"]) + ".")

    if pReport["rejected"]:
        vLines.append("Écartées :")
        vLines += [f"- {vReason}" for vReason in pReport["rejected"]]

    rText = "\n".join(vLines)

    return rText


def split_levels(pLevel, pCount):
    """Retourne la répartition des questions par niveau : [(niveau, nombre)]."""

    if pLevel in QUIZ_LEVELS:
        rLevels = [(pLevel, pCount)]
    else:
        vCounts = [round(pCount * vWeight) for vWeight in LEVEL_WEIGHTS]
        # L'arrondi peut décaler le total : l'écart va au premier niveau.
        vCounts[0] += pCount - sum(vCounts)

        rLevels = [
            (vLevel, vCount) for vLevel, vCount in zip(QUIZ_LEVELS, vCounts) if vCount
        ]

    return rLevels


def build_generation_prompt(pQuiz, pThemeLabel, pLevel, pCount):
    """Retourne la demande ChatGPT d'un pack de questions au format de l'import.

    La demande reprend le modèle complet : manifest, fichier de questions,
    schémas et guides facultatifs, domaines admis et identifiants déjà pris.
    """

    vThemeKey, vThemeLabel = find_theme(pQuiz, pThemeLabel)
    vTheme = pQuiz.get(vThemeKey, {})
    vSkills = vTheme.get("skills") or [vThemeLabel]
    vDomain, vSubdomain = vTheme.get("domain") or classify_theme(vThemeLabel, vSkills)

    # Thème nouveau ou non classé : ChatGPT choisit le domaine et les compétences
    # plutôt que de recopier une valeur par défaut.
    if (vDomain, vSubdomain) == OTHER_DOMAIN:
        vDomain, vSubdomain = "à choisir (règle 2)", "à choisir (règle 2)"

    if not vTheme:
        vSkills = ["compétence 1", "compétence 2", "…"]
    vIds = [vQuestion["id"] for vQuestion in vTheme.get("questions", [])]
    vLevels = split_levels(pLevel, pCount)

    vExample = {
        "theme": vThemeLabel,
        "domain": vDomain,
        "subdomain": vSubdomain,
        "skills": vSkills,
        "questions": [
            {
                "id": f"{vThemeKey}-001",
                "level": vLevels[0][0],
                "type": "qcm",
                "question": "Énoncé de la question ?",
                "code": "facultatif : extrait de code ou de configuration",
                "choices": ["…", "…", "…", "…"],
                "answer": 1,
                "expectedAnswer": "texte exact du choix d'indice answer",
                "explanation": (
                    "2 à 5 phrases : la notion expliquée, pourquoi cette réponse "
                    "est juste et pourquoi les autres choix sont faux."
                ),
                "tags": vSkills[:2],
                "visual": {
                    "type": "svg",
                    "path": f"../assets/schemas/{vThemeKey}-schema.svg",
                    "alt": "Description du schéma",
                },
                "references": [
                    {
                        "title": "Page de la documentation officielle qui donne "
                        "la réponse",
                        "url": "https://…",
                    }
                ],
            }
        ],
    }
    vDomains = "\n".join(
        f"   {vName} : {', '.join(vSubdomains)}"
        for vName, vSubdomains in DOMAIN_ORDER.items()
        if vName != OTHER_DOMAIN[0]
    )

    rPrompt = (
        "Crée un pack de questions QCM pour préparer des entretiens techniques, "
        "en français.\n"
        f"Thème : {vThemeLabel}. {pCount} questions : "
        + ", ".join(f"{vCount} {vLevel}" for vLevel, vCount in vLevels)
        + ".\n\n"
        "Livre une archive .zip avec cette arborescence :\n"
        "- manifest.json\n"
        f"- questions/{vThemeKey}.json\n"
        "- assets/schemas/<nom>.svg   (facultatif : schémas simples, sans script "
        "ni image externe)\n"
        f"- guides/{vThemeKey}.md    (facultatif : méthode pratique en Markdown, "
        "titres, listes, liens https)\n"
        "Si tu ne peux pas créer d'archive, donne seulement le contenu de "
        f"questions/{vThemeKey}.json.\n\n"
        "manifest.json :\n"
        + json.dumps(
            {"themes": [{"id": vThemeKey, "file": f"questions/{vThemeKey}.json"}]},
            ensure_ascii=False,
            indent=2,
        )
        + f"\n\nquestions/{vThemeKey}.json :\n"
        + json.dumps(vExample, ensure_ascii=False, indent=2)
        + "\n\nRègles strictes :\n"
        '1. "level" : ' + ", ".join(QUIZ_LEVELS) + ".\n"
        '2. "domain" et "subdomain", à choisir dans cette liste :\n' + vDomains + "\n"
        '3. "answer" est l\'indice du bon choix, à partir de 0 ; varie sa position '
        "d'une question à l'autre.\n"
        '4. "expectedAnswer" recopie exactement choices[answer].\n'
        "5. Identifiants uniques en minuscules et tirets, préfixés par "
        f"« {vThemeKey}- », jamais parmi ceux déjà pris ci-dessous.\n"
        "6. 4 choix plausibles, une seule bonne réponse, vérifiée.\n"
        '7. Seulement le type "qcm".\n'
        '8. Dans "skills", les mots tels qu\'ils apparaissent dans les offres '
        "d'emploi.\n"
        '9. "explanation" doit faire comprendre la notion, pas seulement donner '
        "la réponse : explique pourquoi la bonne réponse est juste et pourquoi "
        "chaque autre choix est faux.\n"
        "10. Schémas : dès qu'un schéma aide à comprendre (architecture, flux, "
        'séquence, couches), fournis un fichier SVG et renseigne "visual". '
        "Uniquement du SVG : pas de PNG ni JPEG. Le SVG ne contient ni script, "
        "ni attribut on…=, ni foreignObject, ni lien, ni image ou police "
        "externe ; texte en français, fond blanc, largeur 900 au plus.\n"
        '11. "references" : 1 ou 2 pages qui contiennent la réponse, sur le site '
        "officiel (documentation de l'éditeur, norme ou RFC, MDN pour le web). "
        "Lien https direct vers la page exacte : ni raccourcisseur, ni adresse "
        "IP, ni identifiant dans l'adresse, ni fichier à télécharger, ni site "
        "personnel. Ne cite qu'une page dont tu es sûr qu'elle existe.\n"
        '12. "code", "tags", "visual" et "references" sont facultatifs : '
        "omets-les plutôt que de les inventer.\n\n"
        "Identifiants déjà pris : " + (", ".join(vIds[-MAX_PROMPT_IDS:]) or "aucun")
    )

    return rPrompt


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

        for vName, vContent in get_quiz_assets(pDatabaseFile).items():
            vArchive.writestr(f"{EXPORT_SCHEMA_DIRECTORY}/{vName}", vContent)

        for vGuide in get_quiz_guides(pDatabaseFile):
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


def clear_imported_questions(pDatabaseFile, pNow):
    """Sauvegarde la base puis efface toutes les questions importées.

    Retourne (nombre de questions effacées, fichier de sauvegarde). Sans
    sauvegarde réussie, rien n'est effacé.
    """

    vBackupFile = backup_database(pDatabaseFile, pNow, "avant-effacement-questions")
    vCount = delete_imported_content(pDatabaseFile)

    # Signalements et examen en cours visaient des questions qui n'existent plus.
    save_setting_values(pDatabaseFile, {FLAGGED_KEY: "", EXAM_KEY: ""})

    logger.warning(
        "Questions de révision importées effacées : %s ; sauvegarde : %s",
        vCount,
        vBackupFile.name,
    )

    rResult = (vCount, vBackupFile)

    return rResult
