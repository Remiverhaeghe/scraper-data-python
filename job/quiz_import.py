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
    COMMON_FIELDS,
    FLAGGED_KEY,
    QUIZ_LEVELS,
    check_question,
    find_theme,
    get_flagged_questions,
    load_active_quiz,
    load_quiz,
    slugify,
)
from job.quiz_domains import DOMAIN_ORDER, classify_theme
from job.quiz_types import (
    DEFAULT_TYPE,
    OPTIONAL_FIELDS,
    QUESTION_TYPES,
    TYPE_FIELDS,
    get_type,
)
from job.quiz_exam import EXAM_KEY
from job.quiz_generation import apply_lot_quality, find_catalog_theme
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

IMPORT_EXTENSIONS = (".json", ".txt", ".zip")
MAX_ZIP_FILES = 300
MAX_ZIP_BYTES = 20 * 1024 * 1024

# Archives contenues dans l'archive importée : un seul niveau est ouvert.
MAX_ZIP_DEPTH = 1
MAX_SVG_BYTES = 300 * 1024
# Schéma montré avec l'énoncé, et non avec la correction
VISUAL_ON_QUESTION = "question"
MAX_GUIDE_BYTES = 200 * 1024

# Dossier des schémas dans un pack exporté, comme dans ceux de ChatGPT
EXPORT_SCHEMA_DIRECTORY = "assets/schemas"

# Niveaux écrits sans accent dans certains fichiers : « debutant », « confirme »
LEVEL_ALIASES = {
    unicodedata.normalize("NFKD", vLevel).encode("ascii", "ignore").decode(): vLevel
    for vLevel in QUIZ_LEVELS
}

# Seul le QCM est affichable : une question ouverte n'a pas de choix à cocher.

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
    vKnown = vDomain[1] in DOMAIN_ORDER.get(vDomain[0], ())

    rParsed = {
        "theme": vTheme.strip() if isinstance(vTheme, str) and vTheme.strip() else None,
        "skills": (
            [vSkill for vSkill in vSkills if isinstance(vSkill, str) and vSkill.strip()]
            if isinstance(vSkills, list)
            else []
        ),
        "questions": vQuestions,
        # Domaine retenu seulement s'il fait partie du classement de l'application
        "domain": vDomain if vKnown else None,
        "unknown_domain": vDomain if any(vDomain) and not vKnown else None,
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

    vType = get_type(vQuestion)

    if vType not in QUESTION_TYPES:
        raise ValueError(
            f"{pLabel}, question {vId} : type inconnu "
            f"({', '.join(QUESTION_TYPES)} attendu)"
        )

    if isinstance(vQuestion.get("level"), str):
        vLevel = vQuestion["level"].strip().lower()
        vQuestion["level"] = LEVEL_ALIASES.get(vLevel, vLevel)

    check_question(vQuestion, pLabel)

    # Champ redondant des packs : un écart signale une question à ne pas croire.
    vExpected = vQuestion.get("expectedAnswer")

    if (
        vType == DEFAULT_TYPE
        and vExpected is not None
        and str(vExpected).strip() != vQuestion["choices"][vQuestion["answer"]].strip()
    ):
        raise ValueError(f"{pLabel}, question {vId} : réponse attendue incohérente")

    rQuestion = {
        vField: vQuestion[vField]
        for vField in (*COMMON_FIELDS, *TYPE_FIELDS[vType], *OPTIONAL_FIELDS)
        if vField in vQuestion
    }

    # Le type par défaut n'est pas écrit : les questions déjà enregistrées n'en ont pas.
    if vType != DEFAULT_TYPE:
        rQuestion["type"] = vType

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

        # Un symbole à reconnaître, ou un schéma où cliquer, se montre avec la
        # question et non à la correction.
        if vVisual.get("show") == VISUAL_ON_QUESTION or vType == "zone":
            rQuestion["visual"]["show"] = VISUAL_ON_QUESTION

    if vType == "zone" and "visual" not in rQuestion:
        raise ValueError(f"{pLabel}, question {vId} : schéma où cliquer manquant")

    return rQuestion


def import_questions(
    pDatabaseFile, pThemeLabel, pText, pNow, pThemeKey=None, pVisuals=None
):
    """Vérifie, enregistre puis contrôle des questions ; retourne le bilan.

    Le thème indiqué dans le JSON l'emporte sur pThemeLabel ; pThemeKey impose
    la clé du thème, celle d'un pack. Lève ValueError si rien n'est lisible.
    """

    rReport = save_question_file(
        pDatabaseFile, pThemeLabel, pText, pNow, pThemeKey, pVisuals
    )
    apply_lot_quality(pDatabaseFile, rReport)

    return rReport


def save_question_file(
    pDatabaseFile, pThemeLabel, pText, pNow, pThemeKey=None, pVisuals=None
):
    """Vérifie puis enregistre les questions d'un fichier, sans contrôler le lot.

    Le bilan garde le lot touché : le contrôle se fait une fois tous les
    fichiers enregistrés, pour mesurer chaque lot en entier.
    """

    vParsed = parse_questions_text(pText)
    vRequestedTheme = vParsed["theme"] or str(pThemeLabel or "").strip()

    if not vRequestedTheme:
        raise ValueError("Indiquez le thème des questions.")

    vQuiz = load_active_quiz(pDatabaseFile)
    vCatalogTheme = find_catalog_theme(vRequestedTheme)

    # Un thème du catalogue garde sa clé, même collé sans manifest.
    if not pThemeKey and vCatalogTheme:
        pThemeKey = vCatalogTheme["id"]

    vThemeKey, vThemeLabel = find_theme(vQuiz, pThemeKey or vRequestedTheme)

    if pThemeKey and vThemeKey not in vQuiz:
        vThemeLabel = vRequestedTheme

    # Une question livrée ne se remplace pas ; une question importée dans le même
    # thème, signalée ou non, est remplacée par sa version corrigée.
    vImported = {
        vQuestion["id"]: (vKey, vQuestion)
        for vKey, _, vQuestion in get_imported_questions(pDatabaseFile)
    }
    vShippedIds = {
        vQuestion["id"]
        for vTheme in load_quiz().values()
        for vQuestion in vTheme["questions"]
    }
    vTexts = {
        get_question_text(vQuestion): vQuestion["id"]
        for vQuestion in vQuiz.get(vThemeKey, {}).get("questions", [])
    }

    vAdded = []
    vReplaced = []
    vUnchanged = []
    rRejected = []

    for vIndex, vQuestion in enumerate(vParsed["questions"], start=1):
        try:
            vClean = normalize_question(vQuestion, f"question {vIndex}", pVisuals or {})
            vId = vClean["id"]
            vPrevious = vImported.get(vId)

            check_question_place(vClean, vPrevious, vThemeKey, vShippedIds, vTexts)

        except ValueError as vException:
            rRejected.append(str(vException))

        else:
            # Une correction livrée sans ses schémas garde ceux déjà importés.
            if vPrevious and "visual" in vPrevious[1] and "visual" not in vClean:
                vClean["visual"] = vPrevious[1]["visual"]

            # Une question identique n'est ni réenregistrée ni retirée des signalements.
            if vPrevious and vClean == vPrevious[1]:
                vUnchanged.append(vClean)
            else:
                (vReplaced if vPrevious else vAdded).append(vClean)

            vImported[vId] = (vThemeKey, None)
            vTexts[get_question_text(vClean)] = vId

    if vReplaced:
        unflag_questions(pDatabaseFile, {vQuestion["id"] for vQuestion in vReplaced})

    vAdded += vReplaced
    vDomain = (
        vParsed["domain"]
        or (
            (vCatalogTheme["domain"], vCatalogTheme["subdomain"])
            if vCatalogTheme
            else None
        )
        or vQuiz.get(vThemeKey, {}).get("domain")
    )

    if vAdded:
        # Un thème livré garde ses compétences ; un nouveau prend celles du fichier.
        if vThemeKey not in load_quiz():
            save_quiz_theme(
                pDatabaseFile,
                vThemeKey,
                vThemeLabel,
                vParsed["skills"] or [vThemeLabel],
                vDomain,
            )

        save_imported_questions(pDatabaseFile, vThemeKey, vThemeLabel, vAdded, pNow)

    if rRejected:
        logger.warning("Import de révision : %s question(s) écartée(s)", len(rRejected))

    rReport = {
        "themes": [vThemeLabel] if vAdded or vUnchanged else [],
        "added": len(vAdded) - len(vReplaced),
        "replaced": len(vReplaced),
        "unchanged": len(vUnchanged),
        "rejected": rRejected,
        "assets": 0,
        "guides": 0,
        "quality": [],
        "warnings": [],
        "review": [],
        "notes": [],
        "batches": (
            [
                {
                    "key": vThemeKey,
                    "label": vThemeLabel,
                    "domain": vDomain,
                    "ids": [vQuestion["id"] for vQuestion in vAdded],
                    "unknown_domain": vParsed["unknown_domain"],
                    "outside_catalog": not vCatalogTheme
                    and vThemeKey not in load_quiz(),
                }
            ]
            if vAdded
            else []
        ),
    }

    return rReport


def check_question_place(pQuestion, pPrevious, pThemeKey, pShippedIds, pTexts):
    """Lève ValueError si une question ne peut ni s'ajouter ni remplacer l'existante.

    pPrevious est le thème et la version importée de même identifiant ; une
    version vide signale une question déjà lue dans ce lot.
    """

    vId = pQuestion["id"]

    if vId in pShippedIds or (pPrevious and pPrevious[0] != pThemeKey):
        raise ValueError(f"question {vId} : identifiant déjà utilisé")

    if pPrevious and pPrevious[1] is None:
        raise ValueError(f"question {vId} : en double dans le lot")

    if pTexts.get(get_question_text(pQuestion), vId) != vId:
        raise ValueError(f"question {vId} : déjà présente")


def get_question_text(pQuestion):
    """Retourne l'énoncé et le code d'une question, pour repérer un doublon."""

    rText = " ".join(pQuestion["question"].lower().split()) + pQuestion.get("code", "")

    return rText


def unflag_questions(pDatabaseFile, pQuestionIds):
    """Remet dans les tirages des questions signalées, remplacées par leur correction."""

    vFlagged = get_flagged_questions(pDatabaseFile)
    vCleared = vFlagged & pQuestionIds

    if vCleared:
        save_setting_values(
            pDatabaseFile, {FLAGGED_KEY: json.dumps(sorted(vFlagged - vCleared))}
        )

        logger.info(
            "Révision : %s question(s) corrigée(s) remise(s) dans les tirages",
            len(vCleared),
        )


def merge_report(pReport, pFileReport, pFileName):
    """Ajoute le bilan d'un fichier de l'archive au bilan global."""

    pReport["added"] += pFileReport["added"]
    pReport["replaced"] += pFileReport["replaced"]
    pReport["unchanged"] += pFileReport["unchanged"]
    pReport["batches"] += pFileReport["batches"]
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

        rReport = {
            "themes": [],
            "added": 0,
            "replaced": 0,
            "unchanged": 0,
            "rejected": [],
            "assets": 0,
            "guides": 0,
            "quality": [],
            "warnings": [],
            "review": [],
            "notes": [],
            "batches": [],
        }
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

                vReport = save_question_file(
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

    # Une archive incluse est contrôlée avec celle qui la contient.
    if pDepth == 0:
        apply_lot_quality(pDatabaseFile, rReport)

    logger.info(
        "Pack de révision importé : %s question(s), %s remplacée(s), %s schéma(s), "
        "%s guide(s)",
        rReport["added"],
        rReport["replaced"],
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

    if pReport.get("replaced"):
        vParts[0] += f", {pReport['replaced']} remplacée(s)"

    if pReport.get("unchanged"):
        vParts[0] += f", {pReport['unchanged']} inchangée(s)"

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

    if pReport.get("warnings"):
        vParts.append(f"{len(pReport['warnings'])} alerte(s) de qualité")

    rText = " · ".join(vParts) + "."

    return rText


def get_import_tone(pReport):
    """Retourne la couleur du bilan : orange si un lot est à vérifier ou écarté."""

    rTone = "warning" if pReport["rejected"] or pReport["warnings"] else "success"

    return rTone


def describe_import_details(pReport):
    """Détaille un import : thèmes, alertes de qualité, mesures et questions écartées."""

    vLines = []

    if pReport["themes"]:
        vLines.append("Thèmes : " + ", ".join(pReport["themes"]) + ".")

    if pReport.get("notes"):
        vLines.append(
            "Hors catalogue, à ajouter au catalogue si le thème doit durer : "
            + ", ".join(pReport["notes"])
            + "."
        )

    if pReport["warnings"]:
        vLines.append("À vérifier, le lot ne respecte pas la demande :")
        vLines += [f"- {vWarning}" for vWarning in pReport["warnings"]]

    if pReport["quality"]:
        vLines.append("Mesures :")
        vLines += [f"- {vLine}" for vLine in pReport["quality"]]

    if pReport["rejected"]:
        vLines.append("Écartées :")
        vLines += [f"- {vReason}" for vReason in pReport["rejected"]]

    rText = "\n".join(vLines)

    return rText


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
