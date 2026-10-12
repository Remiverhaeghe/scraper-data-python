"""Demande de questions à ChatGPT et contrôle du respect de ses règles

Le catalogue des thèmes et le texte de la demande sont des fichiers de
assets/quiz_generation : ils évoluent sans toucher au code. Chaque lot importé
est ensuite mesuré, pour repérer un lot qui ne respecte pas la demande.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from string import Template

from config import QUIZ_GENERATION_DIRECTORY
from job.quiz import QUIZ_LEVELS, find_theme, slugify
from job.quiz_domains import DOMAIN_ORDER, OTHER_DOMAIN, classify_theme
from utils.logger import get_logger

logger = get_logger(__name__)

CATALOG_FILE = QUIZ_GENERATION_DIRECTORY / "catalog.json"
PROMPT_FILE = QUIZ_GENERATION_DIRECTORY / "prompt.txt"
CORRECTION_FILE = QUIZ_GENERATION_DIRECTORY / "correction.txt"

# Nombre de questions demandées à ChatGPT en une fois : 100 remplissent une
# réponse, ChatGPT continue sur demande si elle est coupée.
GENERATION_COUNTS = (10, 20, 30, 50, 100)
DEFAULT_GENERATION_COUNT = 100

# Niveau « tous » de la demande : répartition des questions par niveau, de
# débutant à expert (100 questions : 25, 40, 20, 15).
MIXED_LEVEL = "tous"
LEVEL_WEIGHTS = (0.25, 0.40, 0.20, 0.15)
GENERATION_LEVELS = {
    MIXED_LEVEL: "Tous les niveaux",
    **{vLevel: vLevel.capitalize() for vLevel in QUIZ_LEVELS},
}

# En dessous de ce nombre de questions, une proportion ne prouve rien.
MIN_QUALITY_SAMPLE = 20

# Au hasard, la bonne réponse est la plus longue ou à une position donnée une
# fois sur quatre : au-delà de ces parts, elle se devine.
MAX_LONGEST_SHARE = 0.4
MAX_POSITION_SHARE = 0.4

# Une explication plus courte ne détaille pas pourquoi les autres choix sont faux.
MIN_EXPLANATION_LENGTH = 80
MAX_SHORT_EXPLANATION_SHARE = 0.2

# Thèmes où un tiers des questions doit porter sur un extrait de code, de
# commande ou de programme automate : en dessous de cette part, le lot reste
# théorique.
CODE_SUBDOMAINS = (
    "Développement",
    "Données",
    "Exploitation et DevOps",
    "Réseau",
    "Automatisme",
)
MIN_CODE_SHARE = 0.15

POSITION_LABELS = "ABCD"


@lru_cache
def load_catalog(pFile=CATALOG_FILE):
    """Retourne les thèmes du catalogue, chacun avec son domaine et sous-domaine."""

    vData = json.loads(Path(pFile).read_text(encoding="utf-8"))

    rThemes = tuple(
        {
            "id": vTheme["id"],
            "label": vTheme["label"],
            "domain": vDomain,
            "subdomain": vSubdomain,
        }
        for vDomain, vSubdomains in vData.items()
        for vSubdomain, vThemes in vSubdomains.items()
        for vTheme in vThemes
    )

    return rThemes


def find_catalog_theme(pTheme):
    """Retourne le thème du catalogue nommé par son identifiant ou son libellé."""

    vKey = slugify(pTheme)

    rTheme = next(
        (
            vTheme
            for vTheme in load_catalog()
            if vKey in (vTheme["id"], slugify(vTheme["label"]))
        ),
        None,
    )

    return rTheme


def list_generation_themes(pThemes):
    """Retourne les libellés proposés pour une demande : thèmes existants et catalogue."""

    vLabels = {vTheme["label"] for vTheme in pThemes}
    vKeys = {vTheme["key"] for vTheme in pThemes}
    vLabels |= {
        vTheme["label"] for vTheme in load_catalog() if vTheme["id"] not in vKeys
    }

    rLabels = sorted(vLabels, key=str.casefold)

    return rLabels


def get_next_lot(pQuestions, pThemeKey):
    """Retourne le numéro du prochain lot d'un thème, d'après ses identifiants."""

    vPattern = re.compile(rf"{re.escape(pThemeKey)}-l(\d+)-\d+")
    vLots = [
        int(vMatch.group(1))
        for vQuestion in pQuestions
        if (vMatch := vPattern.fullmatch(vQuestion["id"]))
    ]

    rLot = max(vLots, default=0) + 1

    return rLot


def split_levels(pLevel, pCount):
    """Retourne la répartition des questions par niveau : [(niveau, nombre)]."""

    if pLevel in QUIZ_LEVELS:
        rLevels = [(pLevel, pCount)]
    else:
        vCounts = [round(pCount * vWeight) for vWeight in LEVEL_WEIGHTS]
        # L'arrondi peut décaler le total : l'écart va au niveau intermédiaire.
        vCounts[1] += pCount - sum(vCounts)

        rLevels = [
            (vLevel, vCount) for vLevel, vCount in zip(QUIZ_LEVELS, vCounts) if vCount
        ]

    return rLevels


def resolve_generation_theme(pQuiz, pThemeLabel):
    """Retourne la clé, le libellé, le domaine et le sous-domaine d'un thème demandé.

    Le catalogue fixe la clé et le classement ; un thème hors catalogue garde
    son classement, ou (None, None) s'il reste à choisir.
    """

    vCatalogTheme = find_catalog_theme(pThemeLabel)

    if vCatalogTheme:
        vThemeKey = vCatalogTheme["id"]
        vThemeLabel = pQuiz.get(vThemeKey, {}).get("label", vCatalogTheme["label"])
        vDomain = (vCatalogTheme["domain"], vCatalogTheme["subdomain"])
    else:
        vThemeKey, vThemeLabel = find_theme(pQuiz, pThemeLabel)
        vTheme = pQuiz.get(vThemeKey, {})
        vDomain = vTheme.get("domain") or classify_theme(
            vThemeLabel, vTheme.get("skills") or [vThemeLabel]
        )

    if tuple(vDomain) == OTHER_DOMAIN:
        vDomain = (None, None)

    rTheme = (vThemeKey, vThemeLabel, *vDomain)

    return rTheme


def build_generation_prompt(pQuiz, pThemeLabel, pLevel, pCount):
    """Retourne la demande ChatGPT d'un lot de questions au format de l'import.

    Le lot suit les lots déjà importés du thème : ses identifiants ne peuvent
    pas reprendre ceux d'un lot précédent.
    """

    vThemeKey, vThemeLabel, vDomain, vSubdomain = resolve_generation_theme(
        pQuiz, pThemeLabel
    )
    vTheme = pQuiz.get(vThemeKey, {})
    vLot = get_next_lot(vTheme.get("questions", []), vThemeKey)
    vLevels = split_levels(pLevel, pCount)
    vNeighbours = [
        vCatalogTheme["label"]
        for vCatalogTheme in load_catalog()
        if (vCatalogTheme["domain"], vCatalogTheme["subdomain"])
        == (vDomain, vSubdomain)
        and vCatalogTheme["id"] != vThemeKey
    ]

    if vDomain:
        vDomainRule = f'exactement "{vDomain}" et "{vSubdomain}".'
    else:
        vDomain = vSubdomain = "à choisir (règle 2)"
        vDomainRule = "à choisir dans cette liste :\n" + "\n".join(
            f"   {vName} : {', '.join(vSubdomains)}"
            for vName, vSubdomains in DOMAIN_ORDER.items()
            if vName != OTHER_DOMAIN[0]
        )

    vExample = {
        "theme": vThemeLabel,
        "domain": vDomain,
        "subdomain": vSubdomain,
        "skills": vTheme.get("skills") or ["compétence 1", "compétence 2", "…"],
        "questions": [
            {
                "id": f"{vThemeKey}-l{vLot}-001",
                "level": vLevels[0][0],
                "type": "qcm",
                "question": "Énoncé de la question ?",
                "code": "facultatif : extrait de code, de configuration ou de "
                "programme automate",
                "choices": ["…", "…", "…", "…"],
                "answer": 2,
                "expectedAnswer": "texte exact de choices[answer]",
                "explanation": "3 à 5 phrases (règle 8)",
                "tags": ["…"],
                "visual": {
                    "type": "svg",
                    "path": f"../assets/schemas/{vThemeKey}-schema.svg",
                    "alt": "Description du schéma",
                },
                "references": [
                    {"title": "Titre exact de la page officielle", "url": "https://…"}
                ],
            }
        ],
    }

    rPrompt = Template(PROMPT_FILE.read_text(encoding="utf-8")).substitute(
        theme=vThemeLabel,
        key=vThemeKey,
        lot=vLot,
        count=pCount,
        levels=", ".join(f"{vCount} {vLevel}" for vLevel, vCount in vLevels),
        perimeter=(
            "Reste dans le périmètre du thème, sans empiéter sur les thèmes "
            f"voisins : {', '.join(vNeighbours)}."
            if vNeighbours
            else "Reste dans le périmètre du thème."
        ),
        manifest=json.dumps(
            {"themes": [{"id": vThemeKey, "file": f"questions/{vThemeKey}.json"}]},
            ensure_ascii=False,
            indent=2,
        ),
        example=json.dumps(vExample, ensure_ascii=False, indent=2),
        level_values=", ".join(f'"{vLevel}"' for vLevel in QUIZ_LEVELS),
        domain_rule=vDomainRule,
    )

    return rPrompt


def is_longest_answer(pQuestion):
    """Indique si la bonne réponse est strictement plus longue que les autres choix."""

    vLengths = [len(vChoice) for vChoice in pQuestion["choices"]]
    vRight = vLengths.pop(pQuestion["answer"])

    rLongest = all(vRight > vLength for vLength in vLengths)

    return rLongest


def format_share(pCount, pTotal):
    """Retourne une part en pourcentage arrondi."""

    rText = f"{round(100 * pCount / pTotal)} %"

    return rText


def assess_questions(pQuestions, pDomain=None):
    """Mesure un lot importé ; retourne son résumé et ses alertes.

    Un écart aux règles de la demande (réponse qui se devine, explications
    trop courtes, pas assez de cas concrets selon le domaine du thème) est
    signalé dès que le lot est assez grand pour le prouver.
    """

    vTotal = len(pQuestions)
    vLongestIds = [
        vQuestion["id"] for vQuestion in pQuestions if is_longest_answer(vQuestion)
    ]
    vLongest = len(vLongestIds)
    vPositionIds = [
        [vQuestion["id"] for vQuestion in pQuestions if vQuestion["answer"] == vIndex]
        for vIndex in range(len(POSITION_LABELS))
    ]
    vPositions = [len(vIds) for vIds in vPositionIds]
    vShortIds = [
        vQuestion["id"]
        for vQuestion in pQuestions
        if len(vQuestion["explanation"].strip()) < MIN_EXPLANATION_LENGTH
    ]
    vShort = len(vShortIds)
    vLevels = [
        sum(vQuestion["level"] == vLevel for vQuestion in pQuestions)
        for vLevel in QUIZ_LEVELS
    ]

    vSummary = (
        f"{vTotal} question(s), bonne réponse la plus longue "
        f"{format_share(vLongest, vTotal)}, positions "
        + " ".join(
            f"{vLabel} {format_share(vCount, vTotal)}"
            for vLabel, vCount in zip(POSITION_LABELS, vPositions)
        )
        + ", niveaux "
        + "/".join(str(vCount) for vCount in vLevels)
        + f", avec code {sum('code' in vQuestion for vQuestion in pQuestions)}"
        f", schémas {sum('visual' in vQuestion for vQuestion in pQuestions)}"
        f", références {sum('references' in vQuestion for vQuestion in pQuestions)}"
    )
    # Chaque alerte garde ses questions : la demande de correction les cite.
    vIssues = []

    if vTotal >= MIN_QUALITY_SAMPLE:
        if vLongest > MAX_LONGEST_SHARE * vTotal:
            vIssues.append(
                (
                    "bonne réponse la plus longue dans "
                    f"{format_share(vLongest, vTotal)} des questions : elle se devine",
                    vLongestIds,
                )
            )

        vIssues += [
            (
                f"bonne réponse en position {vLabel} dans "
                f"{format_share(len(vIds), vTotal)} des questions",
                vIds,
            )
            for vLabel, vIds in zip(POSITION_LABELS, vPositionIds)
            if len(vIds) > MAX_POSITION_SHARE * vTotal
        ]

        if vShort > MAX_SHORT_EXPLANATION_SHARE * vTotal:
            vIssues.append(
                (
                    f"{vShort} explication(s) de moins de {MIN_EXPLANATION_LENGTH} "
                    "caractères",
                    vShortIds,
                )
            )

        vCode = sum("code" in vQuestion for vQuestion in pQuestions)

        if (
            pDomain
            and pDomain[1] in CODE_SUBDOMAINS
            and vCode < MIN_CODE_SHARE * vTotal
        ):
            vIssues.append(
                (
                    f"{vCode} question(s) avec code sur {vTotal} : moins de "
                    f"{round(100 * MIN_CODE_SHARE)} % de cas concrets",
                    [],
                )
            )

    if vIssues:
        logger.warning(
            "Lot de révision à vérifier : %s",
            " ; ".join(vWarning for vWarning, _ in vIssues),
        )

    rQuality = {
        "summary": vSummary,
        "warnings": [vWarning for vWarning, _ in vIssues],
        "issues": vIssues,
    }

    return rQuality


def build_correction_prompt(pReview):
    """Retourne la demande de correction des thèmes signalés à l'import d'un lot."""

    vThemes = "\n\n".join(
        f"Thème « {vTheme['label']} », fichier questions/{vTheme['key']}.json :\n"
        + "\n".join(
            f"- {vWarning}"
            + (f"\n  Questions concernées : {', '.join(vIds)}" if vIds else "")
            for vWarning, vIds in vTheme["issues"]
        )
        for vTheme in pReview
    )

    rPrompt = Template(CORRECTION_FILE.read_text(encoding="utf-8")).substitute(
        themes=vThemes
    )

    return rPrompt
