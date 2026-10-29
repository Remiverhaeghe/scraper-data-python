"""Préparation d'une candidature : correspondance, CV, entretien et lettre

Tout repose sur des règles et sur le profil saisi : aucune donnée ne quitte
l'application et aucun service payant n'est utilisé.
"""

import re
from functools import lru_cache

from job.education import compare_education
from job.enrichment import SKILL_PATTERNS, detect_skills
from job.fingerprint import GENDER_MARKERS
from job.pitch import build_pitch, find_examples, lower_first
from job.presentation import to_list
from job.self_assessment import KNOWN_LEVEL, get_assessed_skills
from job.star_answers import select_star_answers, suggest_star_questions
from job.tricky_questions import build_tricky_questions

# Questions toujours utiles en fin d'entretien
GENERAL_QUESTIONS = (
    "Comment l'équipe est-elle organisée, et avec qui travaillerais-je au quotidien ?",
    "Quelles sont les priorités du poste pour les six premiers mois ?",
    "Comment se déroule l'intégration d'un nouveau collaborateur ?",
)

# Nombre de compétences mises en avant dans la lettre
LETTER_SKILLS = 3

# Poids d'une compétence selon la phrase de l'annonce qui la cite
REQUIRED_WEIGHT = 2.0
NORMAL_WEIGHT = 1.0
PREFERRED_WEIGHT = 0.5
REQUIRED_MARKERS = re.compile(
    r"\b(?:exig[ée]e?s?|indispensables?|obligatoires?|imp[ée]ratifs?|imp[ée]rative"
    r"|ma[îi]trise[rz]?|ma[îi]trisez|required|must)\b",
    re.IGNORECASE,
)
PREFERRED_MARKERS = re.compile(
    r"\bun plus\b|\bapp?r[ée]ci[ée]e?s?\b|\bsouhait[ée]e?s?\b|\bid[ée]alement\b"
    r"|\batouts?\b|\bnice to have\b|\bbonus\b|\bpreferred\b|\bplus\b\s*$",
    re.IGNORECASE,
)
SENTENCE_SEPARATORS = re.compile(r"[.;!?\n•·]+")

# Au-dessous, le score est rapporté à ce poids : une offre qui ne cite qu'une
# compétence, même couverte, reste à un tiers.
MIN_SCORED_WEIGHT = 3.0

# Niveau d'auto-évaluation à partir duquel une compétence compte pleinement, et
# part de maîtrise à partir de laquelle elle est affichée comme couverte
FULL_LEVEL = 8
COVERED_SHARE = 0.5


def get_offer_text(pOffer):
    """Retourne le texte d'une offre où chercher les compétences demandées."""

    rText = " ".join(
        str(pOffer.get(vColumn) or "")
        for vColumn in ("title", "description", "missions", "requirements")
    )

    return rText


def get_offer_skills(pOffer):
    """Retourne les compétences demandées : celles de la source et celles du texte.

    Celles du texte sont lues en base quand elles y sont déjà (job/skill_cache.py),
    sinon cherchées à la volée, plus lentement.
    """

    vDetected = pOffer.get("detected_skills")
    vDetected = (
        to_list(vDetected)
        if isinstance(vDetected, (str, list))
        else detect_skills(get_offer_text(pOffer))
    )

    rSkills = list(dict.fromkeys([*(to_list(pOffer.get("skills")) or []), *vDetected]))

    return rSkills


def same_skill(pFirst, pSecond):
    """Compare deux compétences sans tenir compte de la casse ni des espaces."""

    rSame = pFirst.strip().lower() == pSecond.strip().lower()

    return rSame


def contains_skill(pSkills, pSkill):
    """Indique si une liste contient une compétence, à la casse près."""

    rContains = any(same_skill(vSkill, pSkill) for vSkill in pSkills)

    return rContains


def expand_skills(pSkills):
    """Ajoute aux compétences saisies leur libellé reconnu dans les offres.

    « TIA Portal » ou « habilitation B2V » saisis dans le profil couvrent ainsi
    « Siemens TIA Portal » et « Habilitation électrique » détectés dans une offre.
    """

    rSkills = list(expand_skill_names(tuple(pSkills)))

    return rSkills


# Les mêmes noms reviennent pour chaque offre notée (auto-évaluation) : sans ce
# cache, noter quelques milliers d'offres relançait la détection 500 000 fois.
@lru_cache(maxsize=4096)
def expand_skill_names(pSkills):
    """Retourne les compétences et leurs libellés reconnus, pour un tuple de noms."""

    rSkills = tuple(dict.fromkeys([*pSkills, *detect_skills(" ; ".join(pSkills))]))

    return rSkills


def find_skill_sentence(pSentences, pSkill):
    """Retourne la phrase de l'annonce qui cite la compétence, ou une chaîne vide."""

    vPattern = SKILL_PATTERNS.get(pSkill)

    rSentence = next(
        (
            vSentence
            for vSentence in pSentences
            if (
                vPattern.search(vSentence)
                if vPattern
                else pSkill.lower() in vSentence.lower()
            )
        ),
        "",
    )

    return rSentence


def classify_requirements(pOfferText, pOfferSkills):
    """Retourne le poids de chaque compétence : exigée, appréciée ou normale.

    La phrase qui cite la compétence décide : « exigé », « maîtrise » la rendent
    exigée ; « un plus », « idéalement » la rendent appréciée.
    """

    vSentences = SENTENCE_SEPARATORS.split(pOfferText or "")
    rWeights = {}

    for vSkill in pOfferSkills:
        vSentence = find_skill_sentence(vSentences, vSkill)

        if PREFERRED_MARKERS.search(vSentence):
            rWeights[vSkill] = PREFERRED_WEIGHT
        elif REQUIRED_MARKERS.search(vSentence):
            rWeights[vSkill] = REQUIRED_WEIGHT
        else:
            rWeights[vSkill] = NORMAL_WEIGHT

    return rWeights


@lru_cache(maxsize=64)
def build_level_index(pLevels):
    """Retourne, pour des niveaux (nom, niveau), le rang et le niveau de chaque nom
    exact reconnu et de chaque nom en minuscules, le premier noté l'emportant.

    Construit une fois par profil : noter des milliers d'offres ne relit plus
    chaque niveau pour chaque compétence.
    """

    vExact = {}
    vLower = {}

    for vRank, (vName, vValue) in enumerate(pLevels):
        for vExpanded in expand_skills([vName]):
            vExact.setdefault(vExpanded, (vRank, vValue))

        vLower.setdefault(vName.strip().lower(), (vRank, vValue))

    rIndex = (vExact, vLower)

    return rIndex


@lru_cache(maxsize=64)
def build_skill_set(pSkills):
    """Retourne les compétences en minuscules, pour les chercher sans parcourir la liste."""

    rSkills = frozenset(vSkill.strip().lower() for vSkill in pSkills)

    return rSkills


def get_coverage(pProfile, pProfileSkills, pSkill):
    """Retourne la part de la compétence que le candidat maîtrise, de 0 à 1.

    Notée dans l'auto-évaluation, elle compte à partir de KNOWN_LEVEL, au prorata
    de son niveau et pleinement dès FULL_LEVEL ; plus bas, elle est à renforcer.
    Présente dans le profil sans note, elle compte pleinement.
    """

    vExact, vLower = build_level_index(
        tuple((pProfile.get("skill_levels") or {}).items())
    )
    # Le premier niveau noté qui correspond, par nom reconnu ou par nom saisi
    vFound = min(
        (
            vMatch
            for vMatch in (vExact.get(pSkill), vLower.get(pSkill.strip().lower()))
            if vMatch
        ),
        default=None,
    )
    vLevel = vFound[1] if vFound else None

    if vLevel:
        rCoverage = min(1.0, vLevel / FULL_LEVEL) if vLevel >= KNOWN_LEVEL else 0.0
    else:
        rCoverage = (
            1.0
            if pSkill.strip().lower() in build_skill_set(tuple(pProfileSkills))
            else 0.0
        )

    return rCoverage


def match_profile(pProfile, pOfferSkills, pOfferText=""):
    """Retourne les compétences couvertes, manquantes et le score de correspondance.

    Le score pèse chaque compétence (exigée, appréciée) et sa maîtrise ; il est
    rapporté à au moins MIN_SCORED_WEIGHT, pour qu'une offre qui ne cite qu'une
    compétence ne monte pas à 100 %.
    """

    # Compétences du profil, et celles notées assez haut dans l'auto-évaluation
    vProfileSkills = expand_skills(
        [*pProfile["skills"], *get_assessed_skills(pProfile)]
    )
    vWeights = classify_requirements(pOfferText, pOfferSkills)
    vCoverage = {
        vSkill: get_coverage(pProfile, vProfileSkills, vSkill)
        for vSkill in pOfferSkills
    }
    vCovered = [vSkill for vSkill in pOfferSkills if vCoverage[vSkill] >= COVERED_SHARE]
    vTotal = sum(vWeights.values())

    rMatch = {
        "covered": vCovered,
        "missing": [vSkill for vSkill in pOfferSkills if vSkill not in vCovered],
        "required": [
            vSkill for vSkill, vWeight in vWeights.items() if vWeight == REQUIRED_WEIGHT
        ],
        # Poids et maîtrise de chaque compétence, pour expliquer le score
        "details": [
            {
                "skill": vSkill,
                "weight": vWeights[vSkill],
                "coverage": vCoverage[vSkill],
            }
            for vSkill in pOfferSkills
        ],
        # Sans compétence identifiée dans l'offre, aucun score n'a de sens.
        "score": (
            round(
                100
                * sum(vWeights[vSkill] * vCoverage[vSkill] for vSkill in pOfferSkills)
                / max(vTotal, MIN_SCORED_WEIGHT)
            )
            if pOfferSkills
            else None
        ),
    }

    return rMatch


WEIGHT_LABELS = {
    REQUIRED_WEIGHT: "exigée",
    NORMAL_WEIGHT: "demandée",
    PREFERRED_WEIGHT: "appréciée",
}


def describe_score(pMatch):
    """Explique le score : une ligne par compétence, poids et maîtrise.

    Les compétences exigées d'abord, puis par maîtrise croissante : ce qui pèse
    le plus et manque le plus se lit en premier.
    """

    vDetails = sorted(
        pMatch.get("details", []),
        key=lambda pDetail: (-pDetail["weight"], pDetail["coverage"]),
    )

    rLines = []

    for vDetail in vDetails:
        if vDetail["coverage"] >= 1:
            vMastery = "maîtrisée"
        elif vDetail["coverage"] > 0:
            vMastery = f"partielle ({round(100 * vDetail['coverage'])} %)"
        else:
            vMastery = "manquante"

        rLines.append(
            f"{vDetail['skill']} · {WEIGHT_LABELS.get(vDetail['weight'], '')} · "
            f"{vMastery}"
        )

    vWeight = sum(vDetail["weight"] for vDetail in vDetails)

    # Plancher appliqué : l'offre cite trop peu de compétences pour un score haut.
    if vDetails and vWeight < MIN_SCORED_WEIGHT:
        rLines.append(
            "Peu de compétences citées : le score est rapporté à trois au minimum"
        )

    return rLines


def describe_missing(pMatch):
    """Retourne les compétences manquantes, les exigées signalées, ou « aucune »."""

    rText = ", ".join(
        f"{vSkill} (exigée)" if vSkill in pMatch.get("required", ()) else vSkill
        for vSkill in pMatch["missing"]
    )

    return rText or "aucune"


def build_target_profiles(pProfile):
    """Retourne les profils cibles : un par CV nommé avec ses compétences, sinon
    le profil entier.

    Un parcours double (développement et maintenance, par exemple) se décrit
    par deux CV : chaque offre est notée sur celui qui lui correspond.
    """

    rTargets = [
        (vCv["name"], {**pProfile, "skills": to_list(vCv["skills"])})
        for vCv in pProfile.get("cv_variants") or []
        if vCv.get("name") and to_list(vCv.get("skills"))
    ] or [(None, pProfile)]

    return rTargets


def match_offer(pProfile, pOffer):
    """Compare le profil à une offre, d'après ses compétences et son texte.

    Avec plusieurs profils cibles, le meilleur score l'emporte ; target donne
    le nom du CV retenu, ou None.
    """

    vSkills = get_offer_skills(pOffer)
    vText = get_offer_text(pOffer)

    rMatch = None

    for vName, vTarget in build_target_profiles(pProfile):
        vMatch = {**match_profile(vTarget, vSkills, vText), "target": vName}

        if rMatch is None or (vMatch["score"] or -1) > (rMatch["score"] or -1):
            rMatch = vMatch

    return rMatch


def recommend_cv(pProfile, pOfferSkills):
    """Retourne la variante de CV qui couvre le plus de compétences de l'offre."""

    rCv = None
    vBestCount = -1

    for vCv in pProfile["cv_variants"]:
        vCvSkills = expand_skills(vCv["skills"])
        vCount = sum(contains_skill(vCvSkills, vSkill) for vSkill in pOfferSkills)

        if vCount > vBestCount:
            rCv = {"name": vCv["name"], "matching": vCount}
            vBestCount = vCount

    return rCv


def find_experiences(pProfile, pSkill):
    """Retourne les expériences du profil qui illustrent une compétence."""

    rExperiences = [
        vExperience
        for vExperience in pProfile["experiences"]
        if contains_skill(vExperience["skills"], pSkill)
    ]

    return rExperiences


def build_questions(pOffer):
    """Retourne les questions à poser, selon ce que l'offre ne précise pas."""

    rQuestions = []

    if not (pOffer.get("salary_net_monthly_min") or pOffer.get("salary_label")):
        rQuestions.append(
            "Quelle est la fourchette de rémunération prévue pour le poste ?"
        )

    if pOffer.get("remote") is None:
        rQuestions.append("Quelle est la politique de télétravail de l'équipe ?")

    if not pOffer.get("contract"):
        rQuestions.append("Quel est le type de contrat proposé ?")
    elif pOffer.get("contract") == "CDD":
        rQuestions.append("Une suite en CDI est-elle envisagée à l'issue du contrat ?")

    rQuestions += GENERAL_QUESTIONS

    return rQuestions


def build_answers(pProfile, pMatch, pOffer):
    """Retourne des pistes de réponse aux questions classiques du recruteur."""

    vCompany = pOffer.get("company") or "l'entreprise"
    vSkills = ", ".join(pMatch["covered"][:LETTER_SKILLS])
    vExperience = next(
        (
            vExperience
            for vSkill in pMatch["covered"]
            for vExperience in find_experiences(pProfile, vSkill)
            if vExperience["achievement"]
        ),
        None,
    )
    vSalary = pOffer.get("salary_label")

    vPitch = [pProfile["headline"] or "Votre métier et votre niveau en une phrase"]

    if pProfile["experiences"]:
        vPitch.append(
            "parcours : "
            + ", ".join(vItem["title"] for vItem in pProfile["experiences"][:3])
        )

    if vSkills:
        vPitch.append(f"compétences utiles ici : {vSkills}")

    rAnswers = [
        {
            "question": "Présentez-vous.",
            "hint": " ; ".join(vPitch)
            + ". Deux minutes au plus, en finissant par ce qui vous amène à ce poste.",
        },
        {
            "question": f"Pourquoi {vCompany} ?",
            "hint": f"Citez l'activité de {vCompany} (bouton « Infos entreprise »), "
            "un élément précis de l'offre qui vous attire, puis le lien avec votre "
            "parcours. Évitez les réponses valables pour n'importe quelle entreprise.",
        },
        {
            "question": "Parlez-moi d'une réussite.",
            "hint": (
                f"Méthode STAR (situation, tâche, action, résultat) à partir de : "
                f"{vExperience['title']}, {lower_first(vExperience['achievement'])}."
                if vExperience
                else "Méthode STAR (situation, tâche, action, résultat) : "
                "ajoutez une réalisation à vos expériences dans le Profil."
            ),
        },
        {
            "question": "Quel est votre point faible ?",
            "hint": (
                f"{pMatch['missing'][0]} : dites ce que vous avez déjà commencé "
                "pour progresser (formation, projet personnel) et ce qui vous en "
                "rapproche."
                if pMatch["missing"]
                else "Un vrai point d'amélioration, suivi de ce que vous faites "
                "pour progresser."
            ),
        },
        {
            "question": "Quelles sont vos prétentions salariales ?",
            "hint": (
                f"L'offre annonce {vSalary} : donnez une fourchette cohérente avec "
                "ce montant, en brut annuel."
                if vSalary
                else "L'offre ne donne pas de salaire : préparez une fourchette en "
                "brut annuel à partir d'offres comparables de la liste."
            ),
        },
    ]

    return rAnswers


def build_interview(pProfile, pMatch, pOffer):
    """Prépare l'entretien : expériences à citer, points à préparer, questions."""

    vStrengths = []

    for vSkill in pMatch["covered"]:
        vExperiences = find_experiences(pProfile, vSkill)

        vStrengths.append(
            {
                "skill": vSkill,
                "examples": [
                    f"{vExperience['title']} : {vExperience['achievement']}".rstrip(
                        " :"
                    )
                    for vExperience in vExperiences
                ],
            }
        )

    rInterview = {
        "strengths": vStrengths,
        # Une compétence manquante se prépare plutôt qu'elle ne se cache.
        "gaps": [
            f"{vSkill} : expliquer comment vous comptez vous y former, ou citer une "
            "compétence proche déjà pratiquée."
            for vSkill in pMatch["missing"]
        ],
        "answers": build_answers(pProfile, pMatch, pOffer),
        "questions": build_questions(pOffer),
    }

    return rInterview


def build_letter(pProfile, pMatch, pOffer):
    """Assemble un brouillon de lettre de motivation à relire et personnaliser."""

    vCompany = pOffer.get("company") or "votre entreprise"
    # « Développeur H/F » devient « Développeur » : la mention n'a pas sa place
    # dans une lettre.
    vTitle = " ".join(GENDER_MARKERS.sub(" ", pOffer.get("title") or "").split())
    vTitle = vTitle or "le poste proposé"
    vSkills = pMatch["covered"][:LETTER_SKILLS]

    # Le même exemple que le pitch : un discours cohérent de la lettre à l'entretien.
    vExperience = next(iter(find_examples(pProfile, pMatch["covered"])), None)

    vParagraphs = [
        "Madame, Monsieur,",
        f"Votre offre « {vTitle} » chez {vCompany} a retenu toute mon attention.",
    ]

    if pProfile["headline"]:
        vParagraphs.append(pProfile["headline"])

    if vSkills:
        vParagraphs.append(
            "Je maîtrise notamment " + ", ".join(vSkills) + ", que vous recherchez."
        )

    if vExperience and vExperience["achievement"]:
        vParagraphs.append(
            f"En tant que {lower_first(vExperience['title'])}, j'ai par exemple "
            f"{lower_first(vExperience['achievement'])}.".replace("..", ".")
        )

    vParagraphs += [
        f"Rejoindre {vCompany} me permettrait de mettre ces compétences au service "
        "de vos projets. Je me tiens à votre disposition pour en échanger lors "
        "d'un entretien.",
        "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées.",
    ]

    if pProfile["name"]:
        vParagraphs.append(pProfile["name"])

    rLetter = "\n\n".join(vParagraphs)

    return rLetter


# Questions vécues en entretien rappelées dans chaque préparation
MAX_ASKED_QUESTIONS = 10


def prepare_application(
    pProfile, pOffer, pStarAnswers=None, pAskedQuestions=None, pAgencies=()
):
    """Prépare tous les éléments d'une candidature pour une offre.

    pStarAnswers ajoute à l'entretien les réponses STAR préparées dans le Profil ;
    pAskedQuestions, les questions déjà posées lors d'entretiens précédents ;
    pAgencies, les agences d'intérim qui orientent les questions pièges.
    """

    vOfferSkills = get_offer_skills(pOffer)
    vMatch = match_offer(pProfile, pOffer)

    vInterview = build_interview(pProfile, vMatch, pOffer)
    vInterview["pitch"] = build_pitch(pProfile, vMatch, pOffer)
    vInterview["tricky"] = build_tricky_questions(pOffer, pAgencies)
    vInterview["star"] = select_star_answers(pStarAnswers or {}, pProfile, vOfferSkills)
    vInterview["asked"] = (pAskedQuestions or [])[:MAX_ASKED_QUESTIONS]
    vInterview["likely"] = suggest_star_questions(
        get_offer_text(pOffer), pStarAnswers or {}
    )

    rPreparation = {
        "offer_skills": vOfferSkills,
        "match": vMatch,
        "missing_text": describe_missing(vMatch),
        "score_lines": describe_score(vMatch),
        "cv": recommend_cv(pProfile, vOfferSkills),
        "interview": vInterview,
        "letter": build_letter(pProfile, vMatch, pOffer),
    }

    return rPreparation


def score_offers(pOffers, pProfile):
    """Ajoute à chaque offre son score de correspondance avec le profil, ou None.

    Sans profil renseigné, aucun score n'est calculé. L'écart entre le diplôme
    demandé et celui du profil est ajouté aussi, s'ils sont connus tous les deux.
    """

    vEmpty = (
        not pProfile.get("skills")
        and not get_assessed_skills(pProfile)
        and build_target_profiles(pProfile)[0][0] is None
    )

    for vOffer in pOffers:
        vMatch = None if vEmpty else match_offer(pProfile, vOffer)
        vOffer["match_score"] = vMatch["score"] if vMatch else None
        vOffer["match_target"] = vMatch["target"] if vMatch else None
        vOffer["education_status"] = compare_education(
            vOffer.get("education_level"), pProfile.get("education_level")
        )


# Filtre de la liste des offres : correspondance minimale avec le profil
MATCH_FILTERS = {
    0: "Toute correspondance",
    30: "Correspondance 30 % et +",
    50: "Correspondance 50 % et +",
    70: "Correspondance 70 % et +",
    90: "Correspondance 90 % et +",
}


def filter_by_match(pOffers, pMinScore):
    """Garde les offres au moins aussi proches du profil que pMinScore.

    Sans compétence dans le profil, aucune offre n'a de score : le filtre est
    alors ignoré plutôt que de vider la liste.
    """

    vScored = any(vOffer.get("match_score") is not None for vOffer in pOffers)

    rOffers = (
        [
            vOffer
            for vOffer in pOffers
            if vOffer.get("match_score") is not None
            and vOffer["match_score"] >= pMinScore
        ]
        if pMinScore and vScored
        else pOffers
    )

    return rOffers
